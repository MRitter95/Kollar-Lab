# -*- coding: utf-8 -*-
"""
Created on Fri Feb 26 10:28:57 2021

@author: Kollarlab
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt

import userfuncs
from utility.plotting_tools import simplescan_plot
from utility.measurement_helpers import configure_card, configure_hdawg, estimate_time, read_and_process

import scipy.signal as signal

def get_default_settings():
    settings = {}
    
    settings['scanname'] = 'rabi_chevron'
    settings['meas_type'] = 'rabi_chevron'
    
    #Cavity parameters
    settings['CAVpower']    = -45
    settings['CAV_freq']    = 5e9
    settings['Q_power']     = -20
    
    #Qubit parameters
    settings['start_freq']  = 4*1e9  
    settings['stop_freq']   = 5*1e9 
    settings['freq_points'] = 50

    #Rabi chevron parameters
    settings['start_time']  = 10e-9
    settings['stop_time']   = 500e-9
    settings['time_points'] = 40

    #Card settings
    settings['segments'] = 1
    settings['reads']    = 1
    settings['averages'] = 5e3
    
    return settings

def rabi_chevron(instruments, settings):
    
    ##Instruments used
    qubitgen  = instruments['qubitgen']
    cavitygen = instruments['cavitygen']
    card      = instruments['card']
    hdawg     = instruments['AWG']
    LO        = instruments['LO']

    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings'] 

    stamp    = userfuncs.timestamp()
    saveDir  = userfuncs.saveDir(settings)
    filename = exp_settings['scanname'] + '_' + stamp
    
    ##Cavity settings
    CAV_Attenuation = exp_globals['CAV_Attenuation']
    CAV_power = exp_settings['CAVpower'] + CAV_Attenuation
    CAV_freq  = exp_settings['CAV_freq']
    
    ##Qubit settings
    start_freq  = exp_settings['start_freq']
    stop_freq   = exp_settings['stop_freq']
    freq_points = exp_settings['freq_points']
    freqs  = np.round(np.linspace(start_freq,stop_freq,freq_points),-3)
    
    Qbit_Attenuation = exp_globals['Qbit_Attenuation']
    Qbit_power   = exp_settings['Q_power'] + Qbit_Attenuation
    start_time   = exp_settings['start_time']
    stop_time    = exp_settings['stop_time']
    time_points  = exp_settings['time_points']
    times = np.round(np.linspace(start_time,stop_time,time_points), 9)
    
    ## Generator settings
    cavitygen.Freq   = CAV_freq
    cavitygen.Power  = CAV_power
    cavitygen.IQ.Mod = 'On'

    qubitgen.Freq   = 4e9
    qubitgen.Power  = Qbit_power
    
    qubitgen.IQ.Mod = 'On'

    cavitygen.Output = 'On'
    qubitgen.Output  = 'On'
    
    LO.power  = 12
    LO.freq   = '{} GHz'.format((CAV_freq - exp_globals['IF'])/1e9)
    LO.output = 'On'
    
    ##Card settings
    configure_card(card, settings)

    ##HDAWG settings
    configure_hdawg(hdawg, settings)
    hdawg.Channels[0].configureChannel(amp=0.5,marker_out='Marker', hold='False', delay=30e-9)
    hdawg.Channels[1].configureChannel(amp=0.5,marker_out='Marker', hold='False', delay=30e-9)
    
    progFile = open(r"C:\Users\Kollarlab\Desktop\Kollar-Lab\pulsed_measurements\HDAWG_sequencer_codes\chevron.cpp",'r')
    rawprog  = progFile.read()
    loadprog = rawprog
    progFile.close()
        
    q_pulse = exp_globals['qubit_pulse']
    m_pulse = exp_globals['measurement_pulse']
    loadprog = loadprog.replace('_max_time_', str(m_pulse['meas_pos']))
    loadprog = loadprog.replace('_meas_window_', str(m_pulse['meas_window']))
    loadprog = loadprog.replace('_meas_delay_',str(q_pulse['delay']))
    loadprog = loadprog.replace('_qsigma_',str(q_pulse['sigma']))
    loadprog = loadprog.replace('_num_sigma_',str(q_pulse['num_sigma']))

    ## Starting main measurement loop 
    timedat  = np.zeros((len(times), len(freqs)))
    phasedat = np.zeros((len(times), len(freqs)))
    
    if exp_globals['IF'] != 0:
        #create Chebychev type II digital filter
        filter_N = exp_globals['ddc_config']['order']
        filter_rs = exp_globals['ddc_config']['stop_atten']
        filter_cutoff = np.abs(exp_globals['ddc_config']['cutoff'])
        LPF = signal.cheby2(filter_N, filter_rs, filter_cutoff, btype='low', analog=False, output='sos', fs=card.sampleRate)
        
        xaxis = np.arange(0, card.samples, 1) * 1/card.sampleRate
        digLO_sin = np.sin(2*np.pi*exp_globals['IF']*xaxis)
        digLO_cos = np.cos(2*np.pi*exp_globals['IF']*xaxis)
        
        #store in settings so that the processing functions can get to them
        settings['digLO_sin'] = digLO_sin 
        settings['digLO_cos'] = digLO_cos
        settings['LPF'] = LPF
        
    tstart = time.time()
    first_it = True
    
    for timeind in range(len(times)):
        hold_time = times[timeind]
        finalprog = loadprog.replace('_hold_time_',str(hold_time))
        hdawg.AWGs[0].load_program(finalprog)
        hdawg.AWGs[0].run_loop()
        time.sleep(0.1)
        total_samples = card.samples
#        amps   = np.zeros((len(freqs), card.samples))
#        phases = np.zeros((len(freqs), card.samples))
        Is_full  = np.zeros((len(freqs), total_samples)) #the very rawest data is thrown away for heterodyne! Warning
        Qs_full  = np.zeros((len(freqs), total_samples))
        
        print('Current hold time:{}, max:{}'.format(hold_time, times[-1]))
    
        for find in range(0, len(freqs)):
            freq = freqs[find]
            
            qubitgen.freq = freq
            time.sleep(0.1)
            
#            amp, phase, amp_full, phase_full, xaxis = read_and_process(card, settings)
            I_window, Q_window, I_full, Q_full, xaxis = read_and_process(card, settings, 
                                                                         plot=first_it, 
                                                                         IQstorage = True)
            
            I_final = np.mean(I_window) #compute <I> in the data window
            Q_final = np.mean(Q_window) #compute <Q> in the data window

            if first_it:
                tstop = time.time()
                estimate_time(tstart, tstop, len(freqs)*len(times))
                first_it = False
                           
#            amps[find,:]   = amp_full
#            phases[find,:] = phase_full
#
#            timedat[timeind, find]  = np.mean(amp)
#            phasedat[timeind, find] = np.mean(phase)
            Is_full[find,:]   = I_full
            Qs_full[find,:] = Q_full
            timedat[timeind, find] = np.sqrt(I_final**2 + Q_final**2)
            phasedat[timeind, find] = np.arctan2(Q_final, I_final)*180/np.pi

        full_data = {}
        full_data['xaxis']  = freqs/1e9
        full_data['mags']   = timedat[0:timeind+1]
        full_data['phases'] = phasedat[0:timeind+1]

        single_data = {}
        single_data['xaxis'] = freqs/1e9
        single_data['mag']   = timedat[timeind]
        single_data['phase'] = phasedat[timeind]

        yaxis = times[0:timeind+1]
        labels = ['Freq (GHz)', 'Hold time (us)']
        simplescan_plot(full_data, single_data, yaxis*1e6, filename, labels, identifier='', fig_num=1) 
        plt.savefig(os.path.join(saveDir, filename+'_fullColorPlot.png'), dpi = 150)

#        full_time = {}
#        full_time['xaxis']  = xaxis*1e6
#        full_time['mags']   = amps
#        full_time['phases'] = phases
#
#        single_time = {}
#        single_time['xaxis'] = xaxis*1e6
#        single_time['mag']   = amp
#        single_time['phase'] = phase
        full_time = {}
        full_time['xaxis']  = xaxis*1e6
        full_time['Is']   = Is_full
        full_time['Qs'] = Qs_full

        single_time = {}
        single_time['xaxis'] = xaxis*1e6
        single_time['I']   = I_full
        single_time['Q'] = Q_full

        time_labels = ['Time (us)', 'Freq (GHz)']
        identifier = 'Hold time: {}us'.format(hold_time*1e6)
        simplescan_plot(full_time, single_time, freqs/1e9, 'Raw_time_traces\n'+filename, time_labels, identifier, fig_num=2, IQdata=True)
        plt.savefig(os.path.join(saveDir, filename+'_Raw_time_traces.png'), dpi = 150)
        
        userfuncs.SaveFull(saveDir, filename, ['times','freqs', 'timedat', 'phasedat','xaxis', 'full_data', 'single_data', 'full_time', 'single_time'], 
                            locals(), expsettings=settings, instruments=instruments)
        

    t2 = time.time()
    
    print('elapsed time = ' + str(t2-tstart))

    cavitygen.Output = 'Off'
    qubitgen.Output  = 'Off'
    LO.Output        = 'Off'