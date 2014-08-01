% Matlab script for processing the T and H data.
% Data time is in Unix epoch time while matlab datanum returns days

clc;
set(0,'defaultfigurecolor','w','defaultlinelinewidth',1)
fnlist=dir('dht11-*.txt');
fn=fnlist(end).name
doriginal=load(fn);   x=doriginal;
tepoch=x(:,1);  t=tepoch/86400+datenum(1970,1,1)-5/25;
temp=x(:,3);hmd=x(:,4);
hmdrange=[20,100];   tmprange=[10,30];

figure(1);clf
[AX,H1,H2]=plotyy(t,temp,t,hmd);
set(AX(1),'ylim',tmprange,'ytickmode','auto')
tempytick=get(AX(1),'ytick'); 
hmdtickval=linspace(hmdrange(1),hmdrange(2),length(tempytick));
set(AX(2),'ylim',[20,100])
set(AX(2),'ytickmode','manual','ytick',hmdtickval)
set(AX(1),'xlim',[min(t),max(t)]);set(AX(2),'xlim',[min(t),max(t)]);
fmtstr='mmdd-HH';
datetick(AX(1),'x',fmtstr,'keeplimits' );
datetick(AX(2),'x',fmtstr,'keeplimits' );
grid on
ylabel(AX(1),'Temperature (C)');ylabel(AX(2),'Humidity (%)');
title(fn,'interpreter','none')