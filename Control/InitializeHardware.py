# -*- coding: utf-8 -*-
"""
Created on Wed May  6 14:39:58 2020

@author: Kollarlab
"""

import pylab
import sys
import numpy
import scipy
import time
from mpldatacursor import datacursor

from Instruments.HDAWG import HDAWG
from Instruments.Acqiris import Acqiris
from Instruments.SGS import SGS100A
from Instruments.Generator import Keysight33500B
from Instruments.DC205 import DC205
from SGShelper import SGS_coupling, HDAWG_clock

#Digitizer
hardwareAddress = "PXI23::0::0::INSTR"
card = Acqiris(hardwareAddress)

#HDAWG
hdawg = HDAWG('dev8163')

#Generators
logen = SGS100A('TCPIP0::rssgs100a110738::inst0::INSTR')
rfgen = SGS100A('TCPIP0::rssgs100a110739::inst0::INSTR')
SGS_coupling(logen,rfgen)

triggergen  = Keysight33500B('USB0::0x0957::0x2507::MY58000681::0::INSTR')

triggergen.Ref.Source = 'Ext'
triggergen.Waveform   = 'SQU'
triggergen.Freq       = '500 Hz'
triggergen.Volts      = '2 V'
triggergen.Output     = 'ON'

SRS = DC205('ASRL3::INSTR')