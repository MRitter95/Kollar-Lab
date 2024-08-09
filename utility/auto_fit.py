# -*- coding: utf-8 -*-
"""
Created on Thu Apr 27 16:32:24 2023

@author: Kollarlab
"""
from pulsed_measurements.T2_echo_phase_rotation import meas_T2_phase_rotation
from pulsed_measurements.T2_echo_phase_rotation import GetDefaultSettings as T2_Defaults 

from pulsed_measurements.T1 import meas_T1
from pulsed_measurements.T1 import get_default_settings as T1_Defaults

import numpy as np
import matplotlib.pyplot as plt
from utility.FitT import fit_T1, fit_T2

def T1_meas(calib_params, time_max, num_points, instruments, exp_globals, averages=5e3):
    '''
    T1_meas _summary_

    :param calib_params: _description_
    :type calib_params: _type_
    :param time_max: _description_
    :type time_max: _type_
    :param num_points: _description_
    :type num_points: _type_
    :param instruments: _description_
    :type instruments: _type_
    :param exp_globals: _description_
    :type exp_globals: _type_
    :param averages: _description_, defaults to 5e3
    :type averages: _type_, optional
    :return: _description_
    :rtype: _type_
    '''    

    exp_settings = T1_Defaults()
    
    exp_settings['scanname'] = 'T1'
    exp_settings['Q_Freq']    = calib_params['Q_Freq']
    exp_settings['Q_Power']   = calib_params['Q_Power']
    exp_settings['CAV_Power'] = calib_params['CAV_Power']
    exp_settings['CAV_Freq']  = calib_params['CAV_Freq']
    
    #Card settings
    exp_settings['segments']      = 1
    exp_settings['reads']         = 1
    exp_settings['averages']      = averages
    
    exp_settings['T1_guess']   = 5e-6
    exp_settings['Tau_min']    = 0e-6
    exp_settings['Tau_max']    = time_max
    exp_settings['Tau_points'] = num_points
    exp_settings['spacing'] = 'lin'
    exp_settings['subtract_background'] = True
    exp_settings['num_save'] = 10
    
    exp_settings['fit_data'] = False
    exp_settings['verbose'] = False
    fullsettings = {}
    fullsettings['exp_globals'] = exp_globals
    fullsettings['exp_settings'] = exp_settings
    
    fittedT1, taus, amp_int = meas_T1(instruments, fullsettings)
    
    datafit = fit_T1(taus, amp_int)
    
    fig = plt.figure(113,figsize = [10,6])
    plt.clf()
    plt.plot(taus, amp_int)
    plt.plot(datafit['ts'], datafit['fit_curve'])
    plt.title('T1:{:.3}us'.format(datafit['tau']*1e6))
    fig.canvas.draw()
    fig.canvas.flush_events()
    return datafit['tau']
    
def T2_meas(freq, calib_params, time_max, num_points, instruments, exp_globals, averages=5e3):
    '''
    T2_meas _summary_

    :param freq: _description_
    :type freq: _type_
    :param calib_params: _description_
    :type calib_params: _type_
    :param time_max: _description_
    :type time_max: _type_
    :param num_points: _description_
    :type num_points: _type_
    :param instruments: _description_
    :type instruments: _type_
    :param exp_globals: _description_
    :type exp_globals: _type_
    :param averages: _description_, defaults to 5e3
    :type averages: _type_, optional
    '''    
    
    exp_settings = T2_Defaults()
    
    exp_settings['scanname'] = 'T2'
    
    exp_settings['Q_Freq']    = freq
    exp_settings['Q_Power']   = calib_params['Q_Power']
    exp_settings['CAV_Power'] = calib_params['CAV_Power']
    exp_settings['CAV_Freq']  = calib_params['CAV_Freq']
    
    #Card settings
    exp_settings['segments']         = 1
    exp_settings['reads']            = 1
    exp_settings['averages']         = 5e3
    
    exp_settings['subtract_background'] = True
    
    exp_settings['T2_mode'] = 'detuning'
    exp_settings['T2_guess'] = 2e-6
    exp_settings['basis'] = 'X' 
    exp_settings['detuning'] = 0e6
    exp_settings['Tau_min'] = 100e-9
    exp_settings['Tau_max'] = time_max
    exp_settings['Tau_points'] = num_points
    exp_settings['pulse_count'] = 0
    exp_settings['phase_rotation_f'] = 5e6
    exp_settings['num_save'] = 10
    
    exp_settings['fit_data'] = False
    exp_settings['verbose'] = False
    settings = {}
    settings['exp_globals'] = exp_globals
    settings['exp_settings'] = exp_settings
    
    T2, detuning, taus, amp_int, loop_times, pulse_deets = meas_T2_phase_rotation(instruments, settings)
    
    datafit = fit_T2(taus, amp_int)
    
    fig = plt.figure(112,figsize = [10,6])
    plt.clf()
    plt.plot(taus, amp_int)
    plt.plot(datafit['ts'], datafit['fit_curve'])
    plt.title('T2:{:.3}us, freq:{:.3}MHz'.format(datafit['tau']*1e6, datafit['freq']/1e6))
    fig.canvas.draw()
    fig.canvas.flush_events()
    return(datafit['freq'], datafit['tau']) 

def find_Q_freq(qubit_guess, calib_params, instruments, exp_globals, 
                t_window=1e-6, num_points=21, freq_shift=2e6, averages=5e3):
     
    '''
     _summary_

    :return: _description_
    :rtype: _type_
    '''     
    delta1, T2_fit1 = T2_meas(qubit_guess, calib_params, t_window, num_points, instruments, exp_globals, averages)
    probef2 = qubit_guess + freq_shift
    delta2, T2_fit2 = T2_meas(probef2, calib_params, t_window, num_points, instruments, exp_globals, averages)
    
    respchange = delta2-delta1
    
    
    if respchange > 0:
        qubit_frequency1 = qubit_guess - delta1
        qubit_frequency2 = probef2 - delta2
        
    if respchange < 0:
        qubit_frequency1 = qubit_guess + delta1
        qubit_frequency2 = probef2 + delta2
            
    qffinal = np.average([qubit_frequency1, qubit_frequency2])
    
    return int(qffinal/1e3)*1e3 

def find_T1(T1_guess, calib_params, instruments, exp_globals, averages=5e3):
    '''
    find_T1 _summary_

    :param T1_guess: _description_
    :type T1_guess: _type_
    :param calib_params: _description_
    :type calib_params: _type_
    :param instruments: _description_
    :type instruments: _type_
    :param exp_globals: _description_
    :type exp_globals: _type_
    :param averages: _description_, defaults to 5e3
    :type averages: _type_, optional
    :return: _description_
    :rtype: _type_
    '''    

    T1_fit = T1_guess
    acceptable_T1 = T1_fit
    T1_range = int(T1_fit*1e6) * 5e-6
    pointnum = 21
    
    print('###################################')
    print('STARTING PARAMETERS:')
    print('T1 guess: {:.3}'.format(T1_fit))
    print('Target Time Range: {:.3}'.format(T1_range))
    print('Time range must be within {:.3} units of 5*T1 to be considered successful.'.format(acceptable_T1))
    print('###################################')
    print('')
    
    T1_timefit = T1_meas(calib_params, T1_range, pointnum, instruments, exp_globals, averages)
    T1_range_n = 5*int(T1_timefit*1e6)*1e-6
        
    while acceptable_T1 < np.abs(T1_range_n-T1_range):
        
        T1_range = T1_range_n
        
        print('---------------------------------')
        print('Attempting time range: {:.3} units'.format(T1_range))
        
        T1_timefit = T1_meas(calib_params, T1_range, pointnum, instruments, exp_globals, averages)
        
        print('New T1 value: {:.3}'.format(T1_timefit))
        print('Ideal time range: {:.3}'.format(T1_timefit*5))
        print('error: {:.3}%'.format( (T1_range - T1_timefit*5)/(T1_timefit*5) * 100 ))
        
        T1_range_n = int(T1_timefit*1e6) * 5e-6
        acceptable_T1 = T1_timefit
        
    print('T1 FOUND!')
    return T1_timefit

def find_T2(T2_guess, calib_params, instruments, exp_globals, averages=5e3):
    '''
    find_T2 _summary_

    :param T2_guess: _description_
    :type T2_guess: _type_
    :param calib_params: _description_
    :type calib_params: _type_
    :param instruments: _description_
    :type instruments: _type_
    :param exp_globals: _description_
    :type exp_globals: _type_
    :param averages: _description_, defaults to 5e3
    :type averages: _type_, optional
    :return: _description_
    :rtype: _type_
    '''    

    T2_fit = T2_guess
    acceptable_T2 = T2_fit
    T2_range = int(T2_fit*1e6) * 5e-6
    pointnum = 51
    nyquist_f = 0.5*pointnum/T2_range
    probe_freq = calib_params['Q_Freq'] + nyquist_f/5
    
    
    print('###################################')
    print('STARTING PARAMETERS:')
    print('Calculated T2: {:.3}'.format(T2_fit))
    print('Target Time Range: {:.3}'.format(T2_range))
    print('Time range must be within {:.3} units of 5*T2 to be considered successful.'.format(acceptable_T2))
    print('###################################')
    print('')
    
    delta_timefit, T2_timefit = T2_meas(probe_freq, calib_params, 
                                                T2_range, pointnum, instruments, exp_globals)
    T2_range_n = 5*int(T2_timefit*1e6)*1e-6
    
    max_count = 5
    while acceptable_T2 < np.abs(T2_range_n-T2_range):
        if max_count<=0:
            print('Max evals exceeded, breaking')
            break
        
        T2_range = T2_range_n
        nyquist_f = 0.5*pointnum/T2_range
        probe_freq = calib_params['Q_Freq'] + nyquist_f/5
        
        print('---------------------------------')
        print('Attempting time range: {:.3} units'.format(T2_range))
        
        delta_timefit, T2_timefit = T2_meas(probe_freq, calib_params, 
                                                T2_range, pointnum, instruments, exp_globals)
        
        print('New T2 value: {:.3}'.format(T2_timefit))
        print('Ideal time range: {:.3}'.format(T2_timefit*5))
        print('error: {:.3}%'.format( (T2_range - T2_timefit*5)/(T2_timefit*5) * 100 ))
        
        T2_range_n = int(T2_timefit*1e6) * 5e-6
        acceptable_T2 = T2_timefit
        max_count-=1
        
    print('T2 FOUND!')
    return T2_timefit

def find_T2_old(T2_guess, calib_params, instruments, exp_globals, averages=5e3):
    '''
    find_T2_old _summary_

    :param T2_guess: _description_
    :type T2_guess: _type_
    :param calib_params: _description_
    :type calib_params: _type_
    :param instruments: _description_
    :type instruments: _type_
    :param exp_globals: _description_
    :type exp_globals: _type_
    :param averages: _description_, defaults to 5e3
    :type averages: _type_, optional
    :return: _description_
    :rtype: _type_
    '''    
    tstart = 5e-6
    tactual_T2 = tstart
    T2_fit = T2_guess#np.min(np.abs([T2_fit1, T2_fit2]))
    ttarget_T2 = T2_fit * 5
    ttrouble_T2 = tstart
    acceptable_T2 = 0.3*T2_fit/2 # The leniency with which the dynamic time window will adjust
    manualcutoff = 1000 # a manual cutoff, in case T2 solves to be a massive number.
    pointnum = 51
    
    print('###################################')
    print('STARTING PARAMETERS:')
    print('Calculated T2: {:.3}'.format(T2_fit))
    print('Target Time Range: {:.3}'.format(ttarget_T2))
    print('Time range must be within {:.3} units of 5*T2 to be considered successful.'.format(acceptable_T2))
    print('###################################')
    print('')
    
    
    while acceptable_T2/2 < np.abs(ttarget_T2 - tactual_T2):
        
        tactual_T2 = ttarget_T2 #Set the ideal time range as the one to use.
        probe_dynamic = calib_params['Q_Freq'] + 10/tactual_T2
        
        print('Attempting time range of {:.3} units'.format(tactual_T2))
        
        if 0 > tactual_T2 or tactual_T2 > manualcutoff  : #If the time range to test is negative or too large, try to extend the starting time range and test again.
            probe_dynamic = calib_params['Q_Freq'] + 10/ttrouble_T2
            ttrouble_T2 = ttrouble_T2*2
            
            print('Calculated range is outside limits.')
            print('Attempting time range of {:.3} units'.format(ttrouble_T2))
            
            delta_timefit, T2_timefit = T2_meas(probe_dynamic, calib_params, 
                                                ttrouble_T2, pointnum, instruments, exp_globals)
        
        else:
            
            print('Time fit determined! Adjusting to fit...')
            
            ttrouble = tactual_T2
            
            delta_timefit, T2_timefit = T2_meas(probe_dynamic, calib_params, 
                                                tactual_T2, pointnum, instruments, exp_globals)
            
        print('New T2 value: {}'.format(T2_timefit))
        print('ping!')
        print('------------------------------------')
        print('')
        
        ttarget_T2 = T2_timefit * 5
        acceptable_T2 = 0.3*tactual_T2
    
    return T2_timefit