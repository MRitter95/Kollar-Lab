# -*- coding: utf-8 -*-
"""
Created on Tue Nov 22 17:14:38 2022

@author: Kollarlab
"""


import os
import time
import numpy as np
import matplotlib.pyplot as plt

import userfuncs
from utility.plotting_tools import simplescan_plot
from utility.measurement_helpers import configure_card, configure_hdawg, estimate_time, read_and_process
from utility.scheduler import scheduler

import scipy.signal as signal

def get_default_settings():
    settings = {}
    
    settings['scanname'] = 'pi_calibration'
    settings['meas_type'] = 'pi_calib'
    
    #Measurement params (from qubit calibration)
    settings['CAV_Power']  = -45
    settings['CAV_Freq']   = 5e9
    settings['Q_Power'] = 0
    settings['Q_Freq']  = 4e9
    settings['Hold_time'] = 50e-9
    
    settings['subtract_background'] = True
    settings['back_rate']  = 1 #retake background every n measurements
    #Sweep params
    settings['Drive_Power'] = -20
    
    settings['Num_pi'] = 1

    #Card settings
    settings['segments'] = 1
    settings['reads']    = 1
    settings['averages'] = 5e3
    
    return settings

def pi_rotation(instruments, settings):
    
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
    CAV_power = exp_settings['CAV_Power'] + CAV_Attenuation
    CAV_freq  = exp_settings['CAV_Freq']
    
    ##Qubit settings
   
    Qbit_Attenuation = exp_globals['Qbit_Attenuation']
    qubit_power   = exp_settings['Q_Power'] + Qbit_Attenuation
    
    ## Generator settings
    cavitygen.freq   = CAV_freq
    cavitygen.power  = CAV_power
    cavitygen.enable_pulse()

    qubitgen.freq   = exp_settings['Q_Freq']
    qubitgen.power  = qubit_power
    
    qubitgen.enable_pulse()
    qubitgen.enable_IQ(exp_globals['qubitgen_config']['Ileak'], exp_globals['qubitgen_config']['Qleak'])

    cavitygen.output = 'On'
    qubitgen.output  = 'On'
    
    LO.power  = 12
    LO.freq   = CAV_freq - exp_globals['IF']
    LO.output = 'On'
    
    ##Card settings
    configure_card(card, settings)

    ##HDAWG settings
    configure_hdawg(hdawg, settings)
    
    progFile = open(r"C:\Users\Kollarlab\Desktop\Kollar-Lab\pulsed_measurements\HDAWG_sequencer_codes\hdawg_placeholder.cpp",'r')
    rawprog  = progFile.read()
    loadprog = rawprog
    progFile.close()

    m_pulse = exp_globals['measurement_pulse']
    q_pulse = exp_globals['qubit_pulse']
    
    start_time  = m_pulse['meas_pos']
    window_time = m_pulse['meas_window']
    
    awg_sched = scheduler(total_time=start_time+2*window_time, sample_rate=2.4e9)

    awg_sched.add_analog_channel(1, name='Qubit_I')
    awg_sched.add_analog_channel(2, name='Qubit_Q')
    
    awg_sched.add_digital_channel(1, name='Qubit_enable', polarity='Pos', HW_offset_on=0, HW_offset_off=0)
    awg_sched.add_digital_channel(2, name='Cavity_enable', polarity='Pos', HW_offset_on=0, HW_offset_off=0)
    
    
    qubit_I       = awg_sched.analog_channels['Qubit_I']
    qubit_Q       = awg_sched.analog_channels['Qubit_Q']
    qubit_marker  = awg_sched.digital_channels['Qubit_enable']
    cavity_marker = awg_sched.digital_channels['Cavity_enable']
    
    delay = q_pulse['delay']
    sigma = q_pulse['sigma']
    num_sigma = q_pulse['num_sigma']

    cavity_marker.add_window(start_time, start_time+window_time+1e-6)

    ## Starting main measurement loop 
    
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
    
    hold_time = exp_settings['Hold_time']
    
    p_amp = exp_settings['Pulse_amp']
    
    f_angle = exp_settings['num_rotations'] * 2 * np.pi
    num_angles = int(exp_settings['num_angles'] * exp_settings['num_rotations'])
    
    angles = np.linspace(0, f_angle, num_angles, endpoint = False)
    amp_array = np.zeros(len(angles))
    I_array = np.zeros(amp_array.shape)
    Q_array = np.zeros(amp_array.shape)
    I_g_array = np.zeros(amp_array.shape)
    Q_g_array = np.zeros(amp_array.shape)
    I_e_array = np.zeros(amp_array.shape)
    Q_e_array = np.zeros(amp_array.shape)
    I_s_array = np.zeros(amp_array.shape)
    Q_s_array = np.zeros(amp_array.shape)
    
    imb_scale = exp_settings['offset'] / (exp_settings['offset'] + exp_settings['amp']* np.sin(angles + exp_settings['phi']))
    
    for ii, angle in enumerate(angles):
        
        hdawg.AWGs[0].stop()
        qubit_I.reset()
        qubit_Q.reset()
        qubit_marker.reset()
        
        pulse_length = num_sigma*sigma+hold_time
           
        position = start_time-delay-pulse_length
        
        adj_amp = p_amp * imb_scale[ii]
#        adj_amp = p_amp
#        angle = 0
        
        qubit_I.add_pulse('gaussian_square', position=position, 
                          amplitude=adj_amp*np.cos(angle), length = hold_time, 
                          ramp_sigma=q_pulse['sigma'], num_sigma=q_pulse['num_sigma'])
        
        qubit_Q.add_pulse('gaussian_square', position=position, 
                          amplitude=adj_amp*np.sin(angle), length = hold_time, 
                          ramp_sigma=q_pulse['sigma'], num_sigma=q_pulse['num_sigma'])
        
        qubit_marker.add_window(position-delay, position+pulse_length+delay)
        awg_sched.plot_waveforms()
        
        [ch1, ch2, marker] = awg_sched.compile_schedule('HDAWG', ['Qubit_I', 'Qubit_Q'], ['Qubit_enable', 'Cavity_enable'])
        
        loadprog = loadprog.replace('_samples_', str(awg_sched.samples))
        hdawg.AWGs[0].load_program(loadprog)
        hdawg.AWGs[0].load_waveform('0', ch1, ch2, marker)
        hdawg.AWGs[0].run_loop()
        
        print('Angle: {:.5f} pi'.format(angle/np.pi))
            
        I_window, Q_window, I_full, Q_full, xaxis = read_and_process(card, settings, 
                                                                     plot=first_it, 
                                                                     IQstorage = True)
        # Acquire g and e cavity traces to convert voltage to population 
        if exp_settings['subtract_background']:
            if ii%exp_settings['back_rate']==0:
                #Acquire g trace
                hdawg.AWGs[0].stop()
                qubit_I.reset()
                qubit_Q.reset()
                qubit_marker.reset()
                
                pulse_length = num_sigma*sigma+hold_time
           
                position = start_time-delay-pulse_length
                
                qubit_I.add_pulse('gaussian_square', position=position, 
                          amplitude=0*p_amp, length = hold_time, 
                          ramp_sigma=q_pulse['sigma'], num_sigma=q_pulse['num_sigma'])
                qubit_marker.add_window(position-delay, position+pulse_length+delay)
                
                awg_sched.plot_waveforms()
                
                [ch1, ch2, marker] = awg_sched.compile_schedule('HDAWG', ['Qubit_I', 'Qubit_Q'], ['Qubit_enable', 'Cavity_enable'])
                
                loadprog = loadprog.replace('_samples_', str(awg_sched.samples))
                hdawg.AWGs[0].load_program(loadprog)
                hdawg.AWGs[0].load_waveform('0', ch1, ch2, marker)
                hdawg.AWGs[0].run_loop()
                I_window_g, Q_window_g, I_full_g, Q_full_g, xaxis_g = read_and_process(card, settings, 
                                                                 plot=first_it, 
                                              IQstorage = True)
                #Acquire the e trace
                hdawg.AWGs[0].stop()
                qubit_I.reset()
                qubit_Q.reset()
                qubit_marker.reset()
                
                pulse_length = num_sigma*sigma+hold_time
           
                position = start_time-delay-pulse_length
                
                qubit_I.add_pulse('gaussian_square', position=position, 
                          amplitude=2*p_amp*imb_scale[0], length = hold_time, 
                          ramp_sigma=q_pulse['sigma'], num_sigma=q_pulse['num_sigma'])
                qubit_marker.add_window(position-delay, position+pulse_length+delay)
                
                awg_sched.plot_waveforms()
                
                [ch1, ch2, marker] = awg_sched.compile_schedule('HDAWG', ['Qubit_I', 'Qubit_Q'], ['Qubit_enable', 'Cavity_enable'])
                
                loadprog = loadprog.replace('_samples_', str(awg_sched.samples))
                hdawg.AWGs[0].load_program(loadprog)
                hdawg.AWGs[0].load_waveform('0', ch1, ch2, marker)
                hdawg.AWGs[0].run_loop()
                I_window_e, Q_window_e, I_full_e, Q_full_e, xaxis_e = read_and_process(card, settings, 
                                                                 plot=first_it, 
                                                                 IQstorage = True)

                
                I_ground, Q_ground = [np.mean(I_window_g), np.mean(Q_window_g)] #<I>, <Q> for ground trace
                I_excited, Q_excited = [np.mean(I_window_e), np.mean(Q_window_e)] #<I>, <Q> for ground trace
        
                contrast = np.sqrt((I_excited-I_ground)**2+(Q_excited-Q_ground)**2)
                ge_I = (I_excited-I_ground)/contrast
                ge_Q = (Q_excited-Q_ground)/contrast

        else:
            I_window_g, Q_window_g, I_full_g, Q_full_g = 0,0,0,0
            contrast = 1
            
        if first_it:
            first_it=False
        ##Useful handles for variables
        I_sig, Q_sig   = [np.mean(I_window), np.mean(Q_window)] #<I>, <Q> for signal trace
        I_ground, Q_ground = [np.mean(I_window_g), np.mean(Q_window_g)] #<I>, <Q> for ground trace
        theta_sig  = np.arctan2(Q_sig,I_sig)*180/np.pi #angle relative to x axis in IQ plane
        theta_ground = np.arctan2(Q_ground, I_ground)*180/np.pi #angle relative to x axis in IQ plane 
        
        I_final = (I_sig-I_ground)/contrast #compute <I_net> in the data window
        Q_final = (Q_sig-Q_ground)/contrast #compute <Q_net> in the data window
        I_full_net = (I_full-I_full_g)/contrast #full I data with background subtracted
        Q_full_net = (Q_full-Q_full_g)/contrast #full Q data with background subtracted
        
        #amp = np.sqrt(I_final**2 + Q_final**2)
        #phase = np.arctan2(Q_final, I_final)*180/np.pi
        #amp_full = np.sqrt(I_full_net**2+Q_full_net**2)  
        #phase_full = np.arctan2(Q_full_net, I_full_net)*180/np.pi
        if exp_settings['subtract_background']:
            amp = I_final*ge_I+Q_final*ge_Q
            amp_perp = -I_final*ge_Q+Q_final*ge_I
            I_array[ii] = np.mean(amp)
            Q_array[ii] = np.mean(amp_perp)
        else:
            amp = np.sqrt(I_final**2 + Q_final**2)
            I_array[ii] = np.mean(I_final)
            Q_array[ii] = np.mean(Q_final)
            
        amp_array[ii] = np.mean(amp)
        
        I_g_array[ii] = np.mean(I_ground)
        Q_g_array[ii] = np.mean(Q_ground)
        I_e_array[ii] = np.mean(I_excited)
        Q_e_array[ii] = np.mean(Q_excited)
        I_s_array[ii] = np.mean(I_sig)
        Q_s_array[ii] = np.mean(Q_sig)
        
        userfuncs.SaveFull(saveDir, filename, ['amp_array', 'I_array', 'Q_array', 
                                               'I_g_array', 'I_e_array', 'I_s_array',
                                               'Q_g_array', 'Q_e_array', 'Q_s_array',
                                               'angles'], 
                            locals(), expsettings=settings, instruments=instruments)
        
        fig = plt.figure(41)
        plt.clf()
        plt.plot(I_g_array[:ii], Q_g_array[:ii], label='Ground')
        plt.plot(I_e_array[:ii], Q_e_array[:ii], label='Excited')
        plt.plot(I_s_array[:ii], Q_s_array[:ii], label='Data')
        plt.title('IQ plot of g,e,signal traces')
        plt.xlabel('I')
        plt.ylabel('Q')
        plt.legend()
        fig.canvas.draw()
        fig.canvas.flush_events()
        

    t2 = time.time()
    
    print('elapsed time = ' + str(t2-tstart))
    
    plt.figure(37)
    plt.clf()
    plt.plot(angles/np.pi, amp_array, '-d')
    plt.xlabel("(pi)")
    plt.title(filename)
    plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)
    
    cavitygen.Output = 'Off'
    qubitgen.Output  = 'Off'
    LO.Output        = 'Off'
    
    return angles, amp_array, I_array, Q_array