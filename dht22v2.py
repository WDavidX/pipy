#!/usr/bin/env python

# 2014-07-11 DHT22.py

import time
import atexit
import pigpio
import smbus
import subprocess
import os
import signal
import RPi.GPIO as GPIO
import psutil
import urllib2
import json
import socket

class i2c_device:
    def __init__(self, addr, port=1):
        self.addr = addr
        self.bus = smbus.SMBus(port)

    # Write a single command
    def write_cmd(self, cmd):
        self.bus.write_byte(self.addr, cmd)
        time.sleep(0.0001)

    # Write a command and argument
    def write_cmd_arg(self, cmd, data):
        self.bus.write_byte_data(self.addr, cmd, data)
        time.sleep(0.0001)

    # Write a block of data
    def write_block_data(self, cmd, data):
        self.bus.write_block_data(self.addr, cmd, data)
        time.sleep(0.0001)

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
    """
    Class to control LCD display
    """
    LCD_BacklightOpt = LCD_NOBACKLIGHT
    LCD_BacklightOpt = LCD_BACKLIGHT
    LCD_TurnOn, LCD_TurnOff = LCD_BACKLIGHT, LCD_NOBACKLIGHT

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
        time.sleep(0.2)
        self.backlight = lcd.LCD_BacklightOpt
        # clocks EN to latch command

    def lcd_backlighton(self, N=-1):
        try:
            N = int(N)
            if not N in [1, 0, -1]:
                raise Exception("Wrong backlight option")
        except Exception:
            N = lcd.LCD_TurnOff
        if N == 1:
            self.LCD_BacklightOpt = lcd.LCD_TurnOn
        elif N == 0:
            self.LCD_BacklightOpt = lcd.LCD_TurnOff
        elif self.LCD_BacklightOpt == lcd.LCD_TurnOff:
            self.LCD_BacklightOpt = lcd.LCD_TurnOn
        else:
            self.LCD_BacklightOpt = lcd.LCD_TurnOff

    def lcd_strobe(self, data):
        self.lcd_device.write_cmd(data | En | self.LCD_BacklightOpt)
        time.sleep(.0005)
        self.lcd_device.write_cmd(((data & ~En) | self.LCD_BacklightOpt))
        time.sleep(.0001)

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


class sensor:
    """
    A class to read relative humidity and temperature from the
    DHT22 sensor.  The sensor is also known as the AM2302.
    The sensor can be powered from the Pi 3V3 or the Pi 5V rail.
    Powering from the 3V3 rail is simpler and safer.  You may need
    to power from 5V if the sensor is connected via a long cable.
    For 3V3 operation connect pin 1 to 3V3 and pin 4 to ground.
    Connect pin 2 to a gpio.
    For 5V operation connect pin 1 to 5V and pin 4 to ground.
    The following pin 2 connection works for me.  Use at YOUR OWN RISK.

    5V--5K_resistor--+--10K_resistor--Ground
                     |
    DHT22 pin 2 -----+
                     |
    gpio ------------+
    """

    def __init__(self, pi, gpio, LED=None, power=None):
        """
        Instantiate with the Pi and gpio to which the DHT22 output
        pin is connected.

        Optionally a LED may be specified.  This will be blinked for
        each successful reading.

        Optionally a gpio used to power the sensor may be specified.
        This gpio will be set high to power the sensor.  If the sensor
        locks it will be power cycled to restart the readings.

        Taking readings more often than about once every two seconds will
        eventually cause the DHT22 to hang.  A 3 second interval seems OK.
        """

        self.pi = pi
        self.gpio = gpio
        self.LED = LED
        self.power = power

        if power is not None:
            pi.write(power, 1)  # Switch sensor on.
            time.sleep(2)

        self.powered = True

        self.cb = None

        atexit.register(self.cancel)

        self.bad_CS = 0  # Bad checksum count.
        self.bad_SM = 0  # Short message count.
        self.bad_MM = 0  # Missing message count.
        self.bad_SR = 0  # Sensor reset count.
        self.bad_Trigger = False  # flag true if the last trigger was good

        # Power cycle if timeout > MAX_TIMEOUTS.
        self.no_response = 0
        self.MAX_NO_RESPONSE = 2

        self.rhum = -999
        self.temp = -999

        self.tov = None

        self.high_tick = 0
        self.bit = 40

        pi.set_pull_up_down(gpio, pigpio.PUD_OFF)

        pi.set_watchdog(gpio, 0)  # Kill any watchdogs.

        self.cb = pi.callback(gpio, pigpio.EITHER_EDGE, self._cb)

    def _cb(self, gpio, level, tick):
        """
        Accumulate the 40 data bits.  Format into 5 bytes, humidity high,
        humidity low, temperature high, temperature low, checksum.
        """
        diff = pigpio.tickDiff(self.high_tick, tick)
        self.bad_Trigger = False
        if level == 0:

            # Edge length determines if bit is 1 or 0.

            if diff >= 50:
                val = 1
                if diff >= 200:  # Bad bit?
                    self.CS = 256  # Force bad checksum.
            else:
                val = 0

            if self.bit >= 40:  # Message complete.
                self.bit = 40

            elif self.bit >= 32:  # In checksum byte.
                self.CS = (self.CS << 1) + val

                if self.bit == 39:

                    # 40th bit received.

                    self.pi.set_watchdog(self.gpio, 0)
                    self.no_response = 0
                    total = self.hH + self.hL + self.tH + self.tL
                    if (total & 255) == self.CS:  # Is checksum ok?
                        self.rhum = ((self.hH << 8) + self.hL) * 0.1
                        if self.tH & 128:  # Negative temperature.
                            mult = -0.1
                            self.tH = self.tH & 127
                        else:
                            mult = 0.1

                        self.temp = ((self.tH << 8) + self.tL) * mult
                        self.tov = time.time()

                        if self.LED is not None:
                            self.pi.write(self.LED, 0)

                    else:
                        self.bad_Trigger = True
                        self.bad_CS += 1


            elif self.bit >= 24:  # in temp low byte
                self.tL = (self.tL << 1) + val

            elif self.bit >= 16:  # in temp high byte
                self.tH = (self.tH << 1) + val

            elif self.bit >= 8:  # in humidity low byte
                self.hL = (self.hL << 1) + val

            elif self.bit >= 0:  # in humidity high byte
                self.hH = (self.hH << 1) + val

            else:  # header bits
                pass

            self.bit += 1

        elif level == 1:
            self.high_tick = tick
            if diff > 250000:
                self.bit = -2
                self.hH = 0
                self.hL = 0
                self.tH = 0
                self.tL = 0
                self.CS = 0

        else:  # level == pigpio.TIMEOUT:
            self.pi.set_watchdog(self.gpio, 0)
            if self.bit < 8:  # Too few data bits received.
                self.bad_MM += 1  # Bump missing message count.
                self.no_response += 1
                if self.no_response > self.MAX_NO_RESPONSE:
                    self.no_response = 0
                    self.bad_SR += 1  # Bump sensor reset count.
                    if self.power is not None:
                        self.powered = False
                        self.pi.write(self.power, 0)
                        time.sleep(2)
                        self.pi.write(self.power, 1)
                        time.sleep(2)
                        self.powered = True
            elif self.bit < 39:  # Short message receieved.
                self.bad_SM += 1  # Bump short message count.
                self.no_response = 0

            else:  # Full message received.

                self.no_response = 0

    def sensor_info(self):
        return self.temp, self.rhum, self.bad_Trigger, self.bad_SM

    def is_last_tigger(self):
        return self.bad_Trigger

    def temperature(self):
        """Return current temperature."""
        return self.temp

    def humidity(self):
        """Return current relative humidity."""
        return self.rhum

    def staleness(self):
        """Return time since measurement made."""
        if self.tov is not None:
            return time.time() - self.tov
        else:
            return -999

    def bad_checksum(self):
        """Return count of messages received with bad checksums."""
        return self.bad_CS

    def short_message(self):
        """Return count of short messages."""
        return self.bad_SM

    def missing_message(self):
        """Return count of missing messages."""
        return self.bad_MM

    def sensor_resets(self):
        """Return count of power cycles because of sensor hangs."""
        return self.bad_SR

    def trigger(self):
        """Trigger a new relative humidity and temperature reading."""
        if self.powered:
            if self.LED is not None:
                self.pi.write(self.LED, 1)

            self.pi.write(self.gpio, pigpio.LOW)
            time.sleep(0.017)  # 17 ms
            self.pi.set_mode(self.gpio, pigpio.INPUT)
            self.pi.set_watchdog(self.gpio, 200)

    def cancel(self):
        """Cancel the DHT22 sensor."""
        self.pi.set_watchdog(self.gpio, 0)
        if self.cb != None:
            self.cb.cancel()
            self.cb = None


def orignal_sample():
    pass
    # Intervals of about 2 seconds or less will eventually hang the DHT22.
    INTERVAL = 3
    pi = pigpio.pi()
    s = sensor(pi, 4, LED=None, power=None)
    r = 0
    next_reading = time.time()
    while True:
        r += 1
        s.trigger()
        time.sleep(0.2)
        print("r={} H={} T={} stale={:3.2f} bad_checksum={} SMS={} Missing={} resets={}".format(
            r, s.humidity(), s.temperature(), s.staleness(),
            s.bad_checksum(), s.short_message(), s.missing_message(),
            s.sensor_resets()))
        next_reading += INTERVAL
        time.sleep(next_reading - time.time())  # Overall INTERVAL second polling.
    s.cancel()
    pi.stop()


def init_mylcd():
    mylcd = lcd()
    mylcd.lcd_display_string("Emma Be Happy".center(20), 2)
    mylcd.lcd_display_string("DHT22 Version 1.0".center(20), 3)
    return mylcd


def backlight_control(fname="backlighton.txt"):
    if os.path.exists(fname):
        return 1
    else:
        return 0


def get_log_file_name(tlast, tnew, outdir=r".", fname_prefix=r"dht22-"):
    t_lastdate_num = int(time.strftime("%Y%m%d", time.localtime(tlast)))
    t_newdate_num = int(time.strftime("%Y%m%d", time.localtime(tnew)))
    # if not os.path.exists(outdir): os.mkdir(outdir)
    fnout = os.path.join(os.getcwdu(), outdir, fname_prefix + time.strftime("%y-%m-%d") + ".txt")
    # print fnout, t_newdate_num,t_lastdate_num
    if (t_newdate_num > t_lastdate_num) and not (os.path.exists(fnout)): open(fnout, 'w').close()
    os.system("""sudo chown pi %s"""%fnout)
    return fnout


def update_lcd(mylcd, t, h):
    mytimestr = time.strftime("%m-%d %H:%M  %a")
    mylcd.lcd_display_string(mytimestr.center(20), 1)
    mylcd.lcd_display_string(("%.1fF %.1fC %.1f%%" % (t * 9 / 5.0 + 32, t, h)).center(20), 4)


def get_weather_api():
    minneapolis_url = r'http://api.openweathermap.org/data/2.5/weather?id=5037649&units=metric'
    try:
        response = urllib2.urlopen(minneapolis_url,timeout=5)
    except urllib2.URLError, e:
        print "urlopen error at %s, %s"%(time.strftime("%m-%d %H:%M:%S"),e)
        return ""
    except socket.timeout,e:
        print "urlopen error at %s, %s"%(time.strftime("%m-%d %H:%M:%S"),e)
        return ""
    data = json.load(response)
    outstr=" %s %.1fC%.0f" % (time.strftime("%H:%M", time.localtime(data['sys']['sunset'])), data['main']['temp'], data['main']['humidity'])
    return  outstr

    
def main1():
    # Some init values
    outdir = r"pipylog_" + os.path.splitext(__file__)[0]
    if not os.path.exists(outdir): os.mkdir(outdir)
    updateIntervalSec, runningTimeHour = 60, 24
    retryInvervalSec = 3
    totalLoopNum, errorLoopNum = 0, 0
    main_t0 = time.time()

    # init instances
    pi = pigpio.pi()
    s = sensor(pi, 4, LED=None, power=None)
    mylcd = init_mylcd()
    mylcd.lcd_backlighton(backlight_control())
    dht_running = True
    initDone = False

    # Sensor first few trials
    init_t0 = -time.time()
    init_loop = 0
    while not initDone:
        loop_t0 = time.time()
        s.trigger()
        t, h, badtrigger, badsm = s.sensor_info()
        if (h != -999):
            initDone = True
        else:  # time.sleep(loop_t0+3-time.time())
            init_loop += 1
            time.sleep(loop_t0 + retryInvervalSec - time.time())
    print "Init sensor %d loops in in %.1f seconds" % (init_loop, time.time() + init_t0)
    print "Output directory %s" % (os.path.abspath(outdir))

    while (dht_running):
        try:
            loop_t_last = loop_t0
            loop_t0 = time.time()
            s.trigger()
            totalLoopNum += 1
            t, h, badtrigger, badsm = s.sensor_info()
            # print totalLoopNum,t,h,badtrigger, badsm

            if badtrigger:
                errorLoopNum += 1
                t_badtrigger_waitsec = max(0, loop_t0 + retryInvervalSec - time.time())
                if t_badtrigger_waitsec > 0: time.sleep(t_badtrigger_waitsec)
                continue

            twaitsec = max(0, loop_t0 + updateIntervalSec - time.time())
            mylcd.lcd_backlighton(backlight_control())
            update_lcd(mylcd, t, h)
            fnout = get_log_file_name(loop_t_last, loop_t0, outdir)
            with open(fnout, 'a') as fhout:
                fhout.write(
                    "%.2f , %s , %4.1f , %4.1f\n" % (loop_t0, time.strftime("%H%M%S", time.localtime(loop_t0)), t, h))
            # mylcd.lcd_display_string(("%5d/%d    %7.3f" % (totalLoopNum, errorLoopNum, twaitsec)).center(20), 3)
            weather_str= get_weather_api()
            mylcd.lcd_display_string(("%d/%d%s" % (totalLoopNum, errorLoopNum, weather_str)).center(20), 3)
            if twaitsec > 0: time.sleep(twaitsec)
        except KeyboardInterrupt:
            dht_running = False
        except Exception, e:
            # dht_running=False
            time.sleep(0.1)
            continue
    print "\n" * 2
    print "%s terminated" % (os.path.abspath(__file__))
    print "Up time: %.1f sec,  %d loops from %s " % (
    time.time() -main_t0, totalLoopNum, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(main_t0)))
    print "Log file at %s" % ( fnout)
    if errorLoopNum > 0: print "Error loops %d/%d" % (errorLoopNum, totalLoopNum)

def start_daemon():
    p1 = subprocess.Popen(["ps","axo","pid,ppid,pgrp,tty,tpgid,sess,comm"], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["awk", "$2==1"], stdin=p1.stdout, stdout=subprocess.PIPE)
    p3 = subprocess.Popen(["awk", "$1==$3"], stdin=p2.stdout, stdout=subprocess.PIPE)
    pdata,perr=p3.communicate()
    pigpiod_found=False
    for idx,item in enumerate(pdata.split("\n")):
        pname=(item.strip()).split(' ')[-1]
        if pname == "pigpiod":
            pigpiod_found=True
            line=item.strip()
            break
    if pigpiod_found: print line
    else: os.system("sudo pigpiod")
     
if __name__ == "__main__":
    pass
    # orignal_sample()
    start_daemon()
    main1()
    #print get_weather_api()
    
