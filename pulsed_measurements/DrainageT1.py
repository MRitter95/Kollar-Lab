# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 11:10:09 2020

@author: Kollarlab
"""

import time
import numpy 
import os
import matplotlib.pyplot as plt

import userfuncs
#from VNAplottingTools import base_power_plot, base_raw_time_plot_spec, pulsed_debug, base_power_plot_imshow

pi = numpy.pi

def remove_IQ_ellipse(Is, Qs, axes, center, phi):
   
    Isprime = numpy.cos(phi)*(Is-center[0]) + numpy.sin(phi)*(Qs-center[1]) + center[0]
    Qsprime = -numpy.sin(phi)*(Is-center[0]) + numpy.cos(phi)*(Qs-center[1]) 
    Qsprime = Qsprime*axes[0]/axes[1] + center[1]
    return Isprime, Qsprime

def GetDefaultSettings():
    settings = {}
    
    settings['scanname'] = 'F4_B137_T1search_del'
    settings['project_dir']  = r'C:\Users\Kollarlab\Desktop\Data\PhosporusDopedSilicon'
    
    #Cavity parameters
    settings['CAVpower']        = -30
    settings['CAV_freq']        = 3.88148e9
    
    #Qubit parameters
    #q_freq = 4.20554796e9
    settings['probe_freq']      = 3.85e9
    settings['probe_power']     = 0
    
    #data acquisition settings
    settings['segments']         = 200
    settings['reads']            = 50
    settings['averages']         = 10
    
    #Card settings
    settings['activeChannels']   = [1,2]
    settings['channelRange']     = 0.5
    settings['sampleRate']       = 2e9/8
    settings['meas_window']      = 100e-6
    settings['empirical_delay']  = 1e-6
    settings['timeout']          = 30
    
    settings['drive_time']       = 2
    settings['meas_type'] = 'DrainageT1'
    
    settings['meas_pos'] = 15.0e-6
    settings['trigger_freq'] = 2e3 

def T1_Drainage(instruments, settings):
    center = [0.027, -0.034]
    phi = 0.044*2*pi/180
    axes = [0.024, 0.018]

    ##Instruments used
    cavitygen = instruments['cavitygen']
    qubitgen  = instruments['qubitgen']
    card      = instruments['card']
    hdawg     = instruments['AWG']
    LO        = instruments['LO']
    
    ##Data saving and naming
    saveDir = userfuncs.saveDir(settings['project_dir'], settings['meas_type'])
    stamp = userfuncs.timestamp()
    filename = settings['scanname'] + '_' + stamp
    
    
    ## Generator settings
    qubitgen.Freq   = settings['probe_freq']
    qubitgen.Power  = settings['probe_power'] 
    qubitgen.IQ.Mod = 'Off'
    
    
    cavitygen.Freq   = settings['CAV_freq'] 
    cavitygen.Power  = settings['CAVpower'] 
    cavitygen.IQ.Mod = 'On'
    
    cavitygen.Output = 'On'
    qubitgen.Output = 'On'
    
    LO.inst.write('ROSC EXT')
    LO.inst.write('SENS:SWE:TYPE CW')
    LO.inst.write('SOUR:POW 12')
    LO.freq = settings['CAV_freq'] 
    LO.output = 'On' 
    
    ##Card settings
    meas_samples = settings['sampleRate']*settings['meas_window']
    
    card.averages       = settings['averages']
    card.segments       = settings['segments']
    card.sampleRate     = settings['sampleRate']
    card.activeChannels = settings['activeChannels']
    card.triggerDelay   = settings['meas_pos'] + settings['empirical_delay']
    card.timeout        = settings['timeout']
    card.samples        = int(meas_samples*1.2)
    card.channelRange   = settings['channelRange']
    card.SetParams()
    
    ##HDAWG settings
    hdawg.AWGs[0].samplerate = '2.4GHz'
    hdawg.channelgrouping = '1x4'
    hdawg.Channels[0].configureChannel(amp=1.0,marker_out='Marker', hold='True')
    hdawg.Channels[1].configureChannel(amp=1.0,marker_out='Marker', hold='True')
    hdawg.AWGs[0].Triggers[0].configureTrigger(slope='rising',channel='Trigger in 1')
    
    progFile = open(r"C:\Users\Kollarlab\Desktop\Kollar-Lab\Control\HDAWG_sequencer_codes\pulsedtrans.cpp",'r')
    rawprog  = progFile.read()
    loadprog = rawprog
    progFile.close()
    
    loadprog = loadprog.replace('_max_time_', str(settings['meas_pos']))
    loadprog = loadprog.replace('_meas_window_', str(settings['meas_window']))
    
    hdawg.AWGs[0].load_program(loadprog)
    hdawg.AWGs[0].run_loop()
    time.sleep(0.1)
    
    data_window = int(settings['meas_window']*card.sampleRate)
    
    xaxis = (numpy.array(range(card.samples))/card.sampleRate)
    xaxis_us = xaxis*1e6
    
    LO.inst.write('SENS:SWE:TYPE CW')
    LO.inst.write('SOUR:POW 12')
    
    
    #for the final processed data
    powerdat = numpy.zeros(settings['segments'])
    phasedat = numpy.zeros(settings['segments'])
    
    Imat = numpy.zeros((settings['segments'], len(xaxis)))
    Qmat = numpy.zeros((settings['segments'], len(xaxis)))
    
    ampMat = numpy.zeros((settings['segments'], len(xaxis)))
    phaseMat = numpy.zeros((settings['segments'], len(xaxis)))
    
    
    #raw data from a single read
    I_oneRead = numpy.zeros((settings['segments'], len(xaxis)))
    Q_oneRead = numpy.zeros((settings['segments'], len(xaxis)))
    
    amps_oneRead = numpy.zeros((settings['segments'], len(xaxis)))
    phases_oneRead = numpy.zeros((settings['segments'], len(xaxis)))
    
    for rind in range(0, settings['reads']):
        print('   ')
        print('current read : ' + str(rind))
        
        if rind == 0:
            tstart = time.time()
        
        #start by turning on the probe for a while
        qubitgen.Output = 'On'
        time.sleep(settings['drive_time'] )
        qubitgen.Output = 'Off'
        
        t1 = time.time()
        
        card.ArmAndWait()
                
        rawI,rawQ = card.ReadAllData() #these are now matrices
        
        if rind == 0:
            tstop = time.time()
            singlePointTime = tstop-tstart
            
            estimatedTime = singlePointTime*settings['reads']
            print('    ')
            print('estimated time for this scan : ' + str(numpy.round(estimatedTime/60, 1)) + ' minutes')
            print('estimated time for this scan : ' + str(numpy.round(estimatedTime/60/60, 2)) + ' hours')
            print('    ')
        
        # mixer correction
        for sind in range(0, settings['segments']):
            Ip, Qp = remove_IQ_ellipse(rawI[sind], rawQ[sind], axes, center, phi)
            
            DC_I = numpy.mean(Ip[-50:])
            DC_Q = numpy.mean(Qp[-50:])
            Idat = Ip-DC_I
            Qdat = Qp-DC_Q
            
            I_oneRead[sind,:] = Idat
            Q_oneRead[sind,:] = Qdat
            
            amp = numpy.sqrt(Idat**2+Qdat**2)
            phase = numpy.arctan2(Qdat, Idat)*180/numpy.pi
    
            amps_oneRead[sind,:] = amp
            phases_oneRead[sind,:] = phase
        
    
        #we have processed a single read. Now to store
        Imat= Imat + I_oneRead
        Qmat = Qmat + Q_oneRead
        
        ampMat = ampMat + amps_oneRead
        phaseMat = phaseMat + phases_oneRead
    
    
    #now we are done with all the reads
        
    #compute our final data
    ampMat = ampMat / settings['reads']  
    phaseMat = phaseMat / settings['reads']  
    Imat = Imat / settings['reads']  
    Qmat = Qmat / settings['reads']    
    
    ind1 = 0
    ind2 = data_window
    powerdat = numpy.mean(ampMat[:,ind1:int(ind2)], axis=1) 
    phasedat = numpy.mean(phaseMat[:,ind1:int(ind2)], axis=1)
    
    data_xaxis = numpy.arange(0,settings['segments'],1) * settings['averages'] * 1/settings['trigger_freq'] #x axis in trigger periods
    
    fig = plt.figure(1, figsize=(13,8))
    plt.clf()
    ax = plt.subplot(1,2,1)
    base_power_plot_imshow(fig, ax, xaxis_us, data_xaxis, ampMat, ['Time(us)', 'Time (trigger)', 'Amp'],0)
    ax = plt.subplot(1,2,2)
    base_power_plot_imshow(fig, ax, xaxis_us, data_xaxis, phaseMat, ['Time(us)', 'Time (trigger)', 'Phase'],0)
    plt.suptitle(filename)
    
    plt.savefig(os.path.join(saveDir, filename+'_RawData.png'), dpi = 150)
    #final data figure
    
    fig2  = plt.figure(2)
    plt.clf()
    ax = plt.subplot(1,2,1)
    plt.plot(data_xaxis, powerdat)
    plt.xlabel('time (s)')
    plt.ylabel('amplitude (lin)')
    
    ax = plt.subplot(1,2,2)
    plt.plot(data_xaxis, phasedat)
    plt.xlabel('time (s)')
    plt.ylabel('phase (degrees)')
    
    plt.suptitle(filename)
    plt.show()
    
    userfuncs.SaveFull(saveDir, filename, ['powerdat', 'phasedat',
                                           'Imat', 'Qmat',
                                           'axes', 'center', 'phi',
                                           'data_xaxis'], locals(), expsettings=settings)
    plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)
    
