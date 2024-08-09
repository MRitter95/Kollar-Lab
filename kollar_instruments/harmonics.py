# -*- coding: utf-8 -*-
"""
Created on Wed May 26 10:38:41 2021

@author: Kollarlab
"""

from time import sleep, time
import matplotlib as plt

from kollar_instruments.VNA import VNA
vna = VNA('TCPIP0::192.168.1.7::inst0::INSTR', reset = False)

vna.configure_frequency(1, start=3.5e+9, stop=5e+9) 
vna.inst.write('SOUR1:FREQ1:CONV:ARB:IFR 1, 1, 0, SWEep')
sleep(5)
first = vna.get_channel_data(1)
plt.plot(first['xaxis'], first['Trc4'])


vna.configure_frequency(1, start=7e+9, stop=10e+9) 
vna.inst.write('SOUR1:FREQ1:CONV:ARB:IFR 1, 2, 0, SWEep')
sleep(5)
second = vna.get_channel_data(1)
plt.plot(second['xaxis'], second['Trc4'])


vna.configure_frequency(1, start=11.5e+9, stop=15e+9) 
vna.inst.write('SOUR1:FREQ1:CONV:ARB:IFR 1, 3, 0, SWEep')
sleep(5)
third = vna.get_channel_data(1)
plt.plot(third['xaxis'], third['Trc4'])

userfuncs.SaveFull(saveDir, scanname, [], locals())
plt.savefig(os.path.join(saveDir, scanname+'.png'), dpi = 150)