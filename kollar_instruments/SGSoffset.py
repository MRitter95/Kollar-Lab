# -*- coding: utf-8 -*-
"""
Created on Thu May 14 11:46:01 2020
Testing offset of SGS unit
@author: Kollarlab
"""

#from kollar_instruments.SGS import RFgen # Ruthie commented out bc it does not exist
from kollar_instruments.HDAWG import HDAWG
from kollar_instruments.Acqiris import Acqiris

import numpy
import time
import pylab
import scipy
import mplcursors


def SGSoffset(card, hdawg):
    ############
    #measurement params
    ###########
    measDur = 10e-6
    freq    = 8e9
    offset  = 0e6
    power   = 2

    ##Card setup
    try:
        card
    except:
        print('Initializing card')
        hardwareAddress = "PXI23::0::0::INSTR"
        card = Acqiris(hardwareAddress)
    card.triggerSlope = 'Rising'
    card.triggerLevel = 0.1
    card.averages = 1 #on-board averages
    card.segments = 1
    card.triggerDelay = 0
    card.activeChannels = [1,2]
    card.verbose = False
    card.sampleRate = 2e9
    card.clockSource = 'External'
    card.channelRange = 0.5
    card.samples = numpy.ceil(measDur*card.sampleRate)
    card.SetParams() #warning. this may round the number of smaples to multiple of 1024

    ## HDAWG setup
    try:
        hdawg
    except:
        print('Initializing HDAWG')
        hdawg = HDAWG('dev8163') #HDAWG device name
        hdawg.AWGs[0].samplerate = '2.4GHz'
        hdawg.channelgrouping = '1x4'
        hdawg.OSCs[1].freq = 10e6
        hdawg.Channels[2].analog_outs = [0.5,0]
        hdawg.Channels[3].analog_outs = [0,1]
        hdawg.Channels[2].configureChannel(amp=1.0)
        hdawg.Channels[3].configureChannel(amp=2.0)

    ## SGS setup
    try:
        logen
        rfgen
    except:
        logen = RFgen('TCPIP0::rssgs100a110738::inst0::INSTR')
        rfgen = RFgen('TCPIP0::rssgs100a110739::inst0::INSTR')
        
    logen.power_Off()
    rfgen.power_Off()

    freq_GHz = freq/1e9
    off_MHz  = offset/1e6

    rfgen.set_Freq(freq_GHz)
    rfgen.set_Amp(power)
    rfgen.mod_Off()
    rfgen.set_External_Reference()
    rfgen.set_RefLO_output(output='LO', freq = 10)
    rfgen.power_On()

    logen.set_Offset(0)
    logen.set_Freq(freq_GHz+0.001)
    logen.set_Offset(off_MHz)
    logen.set_Amp(12)
    logen.mod_Off()
    #logen.set_External_LO()
    logen.power_On() 

    time.sleep(0.5)

    timeaxis = scipy.arange(0, card.samples,1.0)/card.sampleRate

    card.ArmAndWait()
    Idata, Qdata = card.ReadAllData()

    pylab.figure()
    pylab.plot(timeaxis*1e6, Idata[0])
    pylab.plot(timeaxis*1e6, Qdata[0])
    datatips = mplcursors.cursor(multiple = True)
    pylab.show()