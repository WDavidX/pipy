% Matlab script for processing the T and H data.
% Data time is in Unix epoch time while matlab datanum returns days
clc;clear all
set(0,'defaultfigurecolor','w','defaultlinelinewidth',1);lwtmp=2;lwhmd=1;
logdir='pipylog_dht22v2'; display(logdir)
fnlist=dir(strcat(logdir,'\dht22-*.txt'));
fn=fnlist(end).name
doriginal=load(strcat(logdir,'/',fn));   x=doriginal;
tepoch=x(:,1);  t=tepoch/86400+datenum(1970,1,1)-5/24;
temp=x(:,3);hmd=x(:,4);
hmdrange=[20,68];   tmprange=[5,35];
figh=figure(1);clf
set(figh,'units','normalized','outerposition',[0 0 1 1])
[AX,H1,H2]=plotyy(t,temp,t,hmd);
set(H1,'linewidth',lwtmp); set(H2,'linewidth',lwhmd);
set(AX(1),'ylim',tmprange,'ytickmode','auto')
tempytick=get(AX(1),'ytick'); 
hmdtickval=linspace(hmdrange(1),hmdrange(2),length(tempytick));
set(AX(2),'ylim',hmdrange)
set(AX(2),'ytickmode','manual','ytick',hmdtickval)
set(AX(1),'xlim',[min(t),max(t)]);set(AX(2),'xlim',[min(t),max(t)]);
fmtstr='mmdd-HH';
datetick(AX(1),'x',fmtstr,'keeplimits' );
datetick(AX(2),'x',fmtstr,'keeplimits' );
tmpcolor=[1 0 0]; set(AX(1),'ycolor',tmpcolor);set(H1,'color',tmpcolor)
hmdcolor=[0 0 1]; set(AX(2),'ycolor',hmdcolor);set(H2,'color',hmdcolor)
grid on
ylabel(AX(1),'Temperature (C)');ylabel(AX(2),'Humidity (%)');
title(fn,'interpreter','none')