# -*- coding: utf-8 -*-
"""
Created on Wed Apr 21 12:15:03 2021

@author: Kollarlab
"""

import time
import os
import numpy as np
import matplotlib.pyplot as plt

import userfuncs
from utility.plotting_tools import base_power_plot_imshow
from utility.userfits import fit_T2

def GetDefaultSettings():
    settings = {}
    
    settings['scanname'] = 'T2_echo'
    settings['project_dir'] = r'Z:\Data\defaultdir'
    settings['meas_type'] = 'Tmeas'

    
    settings['Q_Freq'] = 4e9
    settings['Q_Power'] = -20
    settings['CAV_Freq'] = 6e9
    settings['CAV_Power'] = -60
    
    Meas_pos = 80e-6
    #Card settings
    settings['segments']         = 1
    settings['reads']            = 1
    settings['averages']         = 25e3
    settings['activeChannels']   = [1,2]
    settings['sampleRate']       = 2e9/8
    settings['trigger_buffer']   = Meas_pos
    settings['meas_window']      = 20e-6
    
    settings['Tau_min'] = 200e-9
    settings['Tau_max'] = 30e-6
    settings['Tau_points'] = 5
    settings['pulse_count'] = 1
    
    #Pulse settings
    settings['Measurement_pos'] = Meas_pos
    settings['wait_time'] = 200e-9
    settings['pulse_width'] = 80e-9
    
    return settings

def meas_T2_echo(instruments, settings):
    ##Instruments used
    qubitgen  = instruments['qubitgen']
    cavitygen = instruments['cavitygen']
    card      = instruments['card']
    hdawg     = instruments['AWG']
    LO        = instruments['LO']
    
    Q_Freq    = settings['Q_Freq'] + settings['detuning']
    Q_Power   = settings['Q_Power']
    CAV_Freq  = settings['CAV_Freq']
    CAV_Power = settings['CAV_Power']
    
    CAV_Attenuation  = settings['CAV_Attenuation']
    Qbit_Attenuation = settings['Qbit_Attenuation']
    detuning = settings['detuning']
    
    stamp = userfuncs.timestamp()
    filename = settings['scanname'] + '_' + stamp
    saveDir = userfuncs.saveDir(settings['project_dir'], settings['meas_type'])
    
    ## Generator settings
    LO.Ref.Source = 'EXT'
    LO.Power = 12
    LO.Freq = CAV_Freq - 1e6
    LO.Output = 'On'

    LO.output = 'On' 
    
    cavitygen.Freq   = CAV_Freq
    cavitygen.Power  = CAV_Power + CAV_Attenuation
    cavitygen.IQ.Mod = 'On'
    
    qubitgen.Freq   = Q_Freq
    qubitgen.Power  = Q_Power + Qbit_Attenuation
    qubitgen.IQ.Mod = 'On'
    
    cavitygen.Output = 'On'
    qubitgen.Output = 'On'
    
    ## Card Settings
    meas_samples = settings['sampleRate']*settings['meas_window']
    
    card.averages       = settings['averages']
    card.segments       = settings['segments']
    card.sampleRate     = settings['sampleRate']
    card.activeChannels = settings['activeChannels']
    card.triggerDelay   = settings['trigger_buffer']
    card.timeout        = 30
    card.samples        = int(meas_samples*2.5)
    card.channelRange   = 2.5
    card.SetParams()
    
    data_window = int(meas_samples)
    start_points = int(1.2e-6*card.sampleRate)
    
    xaxis = (np.array(range(card.samples))/card.sampleRate)
    xaxis_us = xaxis*1e6 + settings['trigger_buffer']
    
    ## HDAWG
    hdawg.AWGs[0].samplerate = '2.4GHz'
    hdawg.channelgrouping = '1x4'
    hdawg.Channels[0].configureChannel(amp=1.0,marker_out='Marker', hold='False')
    hdawg.Channels[1].configureChannel(amp=1.0,marker_out='Marker', hold='False')
    hdawg.AWGs[0].Triggers[0].configureTrigger(slope='rising',channel='Trigger in 1')
    
    progFile = open(r"C:\Users\Kollarlab\Desktop\Kollar-Lab\pulsed_measurements\HDAWG_sequencer_codes\T2_echo.cpp",'r')
    rawprog  = progFile.read()
    loadprog = rawprog
    progFile.close()
    
    loadprog = loadprog.replace('_max_time_', str(settings['Measurement_pos']))
    loadprog = loadprog.replace('_meas_window_', str(settings['meas_window']))
    loadprog = loadprog.replace('_wait_time_', str(settings['wait_time']))
    loadprog = loadprog.replace('_qwidth_', str(settings['pulse_width']))
    loadprog = loadprog.replace('_pi_count_', str(settings['pulse_count']))
    
    taus = np.linspace(settings['Tau_min'],settings['Tau_max'] , settings['Tau_points'] )
    
    plt.figure(1)
    plt.clf()
    amp_int = np.zeros(len(taus))
    amps    = np.zeros((len(taus),card.samples))
    
    tstart = time.time()
    
    for tind in range(len(taus)):
            
        tau = taus[tind]
        print('Tau: {}'.format(tau))
        finalprog = loadprog
        finalprog = finalprog.replace('_tau_',str(tau))
        hdawg.AWGs[0].load_program(finalprog)
        hdawg.AWGs[0].run_loop()
        time.sleep(0.1)
        
        card.ArmAndWait()
        I,Q = card.ReadAllData()
        
        DC_I = np.mean(I[0][-data_window:])
        DC_Q = np.mean(Q[0][-data_window:])
        
        Idat = I[0]-DC_I
        Qdat = Q[0]-DC_Q
        
        amp = np.sqrt(Idat**2+Qdat**2)
        
        amps[tind] = amp
        amp_int[tind] = np.mean(amp[start_points:start_points+data_window])
        if tind == 0:
            tstop = time.time()
            singlePointTime = tstop-tstart
            
            estimatedTime = singlePointTime*len(taus)
            print('    ')
            print('estimated time for this scan : ' + str(np.round(estimatedTime/60, 1)) + ' minutes')
            print('estimated time for this scan : ' + str(np.round(estimatedTime/60/60, 2)) + ' hours')
            print('    ')
    
    userfuncs.SaveFull(saveDir, filename, ['taus','xaxis_us', 'amps', 'amp_int'], locals(), expsettings=settings)
    
    t2 = time.time()
    
    print('Elapsed time: {}'.format(t2-tstart))
    
    fig = plt.figure(1,figsize=(13,8))
    plt.clf()
        
    ax = plt.subplot(1,1,1)
    base_power_plot_imshow(fig, ax, xaxis_us, taus*1e6, amps, ['Time (us)', 'Tau (us)', 'Amp'], attenuation=0)
    
    plt.suptitle(filename)
    plt.savefig(os.path.join(saveDir, filename+'_fulldata.png'), dpi = 150)
    
    fig = plt.figure(2,figsize=(13,8))
    plt.clf()
    tau0 = 5e-9
    offset0 = np.mean(amp_int[-10])
    amp0 = np.mean(max(amp_int)-offset0)
    freq0 = detuning
    phi0 = 0
    
    fit_guess = [tau0, amp0, offset0, freq0, phi0]
    try:
        T2, detuning = fit_T2(taus, amp_int, fit_guess)
    except:
        print('T2 fit did not converge')
        T2 = 0
        detuning = 0
    
    plt.suptitle(filename)
    plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)
    
    
    return T2, detuning