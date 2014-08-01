import smbus
from time import *
import pydht
import time
import subprocess 
import os
class i2c_device:
    def __init__(self, addr, port=1):
        self.addr = addr
        self.bus = smbus.SMBus(port)

    # Write a single command
    def write_cmd(self, cmd):
        self.bus.write_byte(self.addr, cmd)
        sleep(0.0001)

    # Write a command and argument
    def write_cmd_arg(self, cmd, data):
        self.bus.write_byte_data(self.addr, cmd, data)
        sleep(0.0001)

    # Write a block of data
    def write_block_data(self, cmd, data):
        self.bus.write_block_data(self.addr, cmd, data)
        sleep(0.0001)

    # Read a single byte
    def read(self):
        return self.bus.read_byte(self.addr)

    # Read 
    def read_data(self, cmd):
        return self.bus.read_byte_data(self.addr, cmd)

    # Read a block of data
    def read_block_data(self, cmd):
        return self.bus.read_block_data(self.addr, cmd)

# LCD Address
ADDRESS = 0x3f

# commands
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_CURSORSHIFT = 0x10
LCD_FUNCTIONSET = 0x20
LCD_SETCGRAMADDR = 0x40
LCD_SETDDRAMADDR = 0x80

# flags for display entry mode
LCD_ENTRYRIGHT = 0x00
LCD_ENTRYLEFT = 0x02
LCD_ENTRYSHIFTINCREMENT = 0x01
LCD_ENTRYSHIFTDECREMENT = 0x00

# flags for display on/off control
LCD_DISPLAYON = 0x04
LCD_DISPLAYOFF = 0x00
LCD_CURSORON = 0x02
LCD_CURSOROFF = 0x00
LCD_BLINKON = 0x01
LCD_BLINKOFF = 0x00

# flags for display/cursor shift
LCD_DISPLAYMOVE = 0x08
LCD_CURSORMOVE = 0x00
LCD_MOVERIGHT = 0x04
LCD_MOVELEFT = 0x00

# flags for function set
LCD_8BITMODE = 0x10
LCD_4BITMODE = 0x00
LCD_2LINE = 0x08
LCD_1LINE = 0x00
LCD_5x10DOTS = 0x04
LCD_5x8DOTS = 0x00

# flags for backlight control
LCD_BACKLIGHT = 0x08
LCD_NOBACKLIGHT = 0x00

En = 0b00000100  # Enable bit
Rw = 0b00000010  # Read/Write bit
Rs = 0b00000001  # Register select bit


class lcd:
    # initializes objects and lcd
    LCD_BacklightOpt=LCD_NOBACKLIGHT
    LCD_BacklightOpt=LCD_BACKLIGHT
    LCD_TurnOn,LCD_TurnOff= LCD_BACKLIGHT,LCD_NOBACKLIGHT
    def __init__(self):
        self.lcd_device = i2c_device(ADDRESS)

        self.lcd_write(0x03)
        self.lcd_write(0x03)
        self.lcd_write(0x03)
        self.lcd_write(0x02)

        self.lcd_write(LCD_FUNCTIONSET | LCD_2LINE | LCD_5x8DOTS | LCD_4BITMODE)
        self.lcd_write(LCD_DISPLAYCONTROL | LCD_DISPLAYON)
        self.lcd_write(LCD_CLEARDISPLAY)
        self.lcd_write(LCD_ENTRYMODESET | LCD_ENTRYLEFT)
        sleep(0.2)
        self.backlight=lcd.LCD_BacklightOpt
        # clocks EN to latch command

    def lcd_backlighton(self,N=-1):
        try: 
            N=int(N)
            if not N in [1,0,-1]:
                raise Exception("Wrong backlight option")
        except Exception:  N=lcd.LCD_TurnOff
        if N==1: self.LCD_BacklightOpt=lcd.LCD_TurnOn
        elif N==0: self.LCD_BacklightOpt=lcd.LCD_TurnOff
        elif self.LCD_BacklightOpt==lcd.LCD_TurnOff: self.LCD_BacklightOpt=lcd.LCD_TurnOn
        else: self.LCD_BacklightOpt=lcd.LCD_TurnOff
    
    def lcd_strobe(self, data):
        self.lcd_device.write_cmd(data | En | self.LCD_BacklightOpt)
        sleep(.0005)
        self.lcd_device.write_cmd(((data & ~En) | self.LCD_BacklightOpt))
        sleep(.0001)

    def lcd_write_four_bits(self, data):
        self.lcd_device.write_cmd(data | self.LCD_BacklightOpt) 
        self.lcd_strobe(data)

    # write a command to lcd
    def lcd_write(self, cmd, mode=0):
        self.lcd_write_four_bits(mode | (cmd & 0xF0))
        self.lcd_write_four_bits(mode | ((cmd << 4) & 0xF0))

    # put string function
    def lcd_display_string(self, string, line):
        if line == 1:
            self.lcd_write(0x80)
        if line == 2:
            self.lcd_write(0xC0)
        if line == 3:
            self.lcd_write(0x94)
        if line == 4:
            self.lcd_write(0xD4)
        for char in string:
            self.lcd_write(ord(char), Rs)

    # clear lcd and set to home
    def lcd_clear(self):
        self.lcd_write(LCD_CLEARDISPLAY)
        self.lcd_write(LCD_RETURNHOME)

def get_dht11():
    t0=-time.time()
    r=pydht.get(board_mode="BOARD",pin=7)
    return int(r['temperature']),int(r['humidity'])

def init_mylcd():
    mylcd = lcd()
    mylcd.lcd_display_string("Debug Messages Here".center(20), 2)
    mylcd.lcd_display_string("Version 0.5".center(20), 3)   
    return mylcd

    
def update(mylcd):    
    mytemp,myhmd=get_dht11()
    mytimestr=time.strftime("%m-%d  %H:%M  %a")
    mylcd.lcd_display_string(mytimestr.center(20), 1)
    mylcd.lcd_display_string(("T= %d C   H= %d %%"%(mytemp,myhmd)).center(20), 4)
    return mytemp,myhmd

def writetolog(writelist,fh=None):
    if fh is None: return
    for idx,item in enumerate(writelist):
        if idx==0: fh.write("%.2f ,"%(item))
        elif  1<=idx<=2: fh.write(" %s ,"%(item))
        else: fh.write(" %d ,"%((item)))
    fh.write("\n")
    fh.flush()
   
    
def main():
    updateintervalsec=30
    zlogname=r"tlog/tlog_%s.txt"%time.strftime("%y%m%d_%H%M%S")
    fh=None
    fh=open(zlogname,'w')
    # subprocess.call("sudo chown pi ./tlog/*")
    mylcd=init_mylcd()
    num_error=0
    for ct in xrange(int(24*60*60 / updateintervalsec)):
        t0=time.time()
        mylcd.lcd_backlighton(0)
        try:
            mytemp,myhmd=update(mylcd)
        except Exception:
            num_error=num_error+1
            mytemp,myhmd=-1,-1
            continue
        if (-1 <= mytemp <= 50) and (-1 <= myhmd <= 100):
            writelist=[t0, time.strftime("%y%m%d",time.localtime(t0)),\
                time.strftime("%H%M%S",time.localtime(t0)),mytemp,myhmd]
            writetolog(writelist,fh)
            twait=updateintervalsec-(time.time()-t0)
            mylcd.lcd_display_string(("%5d/%d    %7.3f"%(ct+1,num_error,twait)).center(20), 3)
            twait=updateintervalsec-(time.time()-t0)
            if twait>0: time.sleep(twait)
    if fh is not None: fh.close()
    

def get_log_file_name(tlast,tnew,outdir=r".",fname_prefix=r"dht11-"):
    t_lastdate_num=int(time.strftime("%Y%m%d",time.localtime(tlast)))
    t_newdate_num=int(time.strftime("%Y%m%d",time.localtime(tnew)))
    # if not os.path.exists(outdir): os.mkdir(outdir)
    fnout=os.path.join(os.getcwdu(),outdir,fname_prefix+time.strftime("%y-%m-%d")+".txt")
    # print fnout, t_newdate_num,t_lastdate_num
    if (t_newdate_num>t_lastdate_num) and not (os.path.exists(fnout)): open(fnout,'w').close()
    return fnout      


def main2():
    outdir=r"pipylog_dht11"
    if not os.path.exists(outdir):os.mkdir(outdir)
    updateintervalsec,running_time_hour=30,24
    t_new_loop,num_error=0,0
    mylcd=init_mylcd()
    mylcd.lcd_backlighton(0)
    for loop_counter in xrange(running_time_hour*60*60/updateintervalsec):
        t_last_loop=t_new_loop
        t_new_loop=time.time()
        try:
            mytemp,myhmd=update(mylcd)
        except Exception,e:
            num_error+=1
            time.sleep(0.5)
            continue
        if (-1<= mytemp <=50) and (-1<=myhmd<=100):
            fnout=get_log_file_name(t_last_loop,t_new_loop,outdir)
            with open(fnout,'a') as fhout:
                fhout.write("%.2f , %s , %3d , %3d\n"%(t_new_loop,\
                            strftime("%H%M%S",time.localtime(t_new_loop)), mytemp,myhmd))
        t_end_loop=time.time()
        twait=updateintervalsec-(t_end_loop-t_new_loop)
        mylcd.lcd_display_string(("%5d/%d    %7.3f"%(loop_counter+1,num_error,twait)).center(20), 3)
        if twait>0:time.sleep(twait)
        
if __name__=="__main__": main2()
