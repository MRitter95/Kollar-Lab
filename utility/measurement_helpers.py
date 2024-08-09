# -*- coding: utf-8 -*-
"""
Created on Wed Mar  3 09:20:52 2021


8-25-21 AK trying to unwarpp the phase of pulse homodyne data. Messing 
with the extract data function.

@author: Kollarlab
"""
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta, datetime

import scipy.signal as signal

def check_inputs(inputs, defaults):
    '''
    Checks that the given input dictionary has the correct settings. It's easy
    to accidentally mistype something or us an old naming convention so this 
    function will throw an error if the keys in the dictionaries don't match
    
    Parameters
    __________
            inputs: 
                input dictionary that is modified by user
            defaults: 
                default dictionary specified by script

    '''
    diff1 = set(inputs) - set(defaults)
    diff2 = set(defaults) - set(inputs)
    if len(diff1) !=0 or len(diff2) !=0:
        print('Differing keys:')
        if len(diff1)!=0:
            print(diff1)
        else:
            print(diff2)
        raise ValueError('Incorrect number of inputs, please check the default settings for variable names')

def remove_IQ_ellipse(Is, Qs, mixer_config):
    '''
    Removes IQ imbalances from the mixer. This is critical for signals with 
    small SNR since the differences between high and low can be wiped out by
    the ellipse eccentricity. Expects axes center phi in the convention defined
    by the 'fitEllipse' function in the ellipse_fitting file
    
        Parameters:
            Is, Qs: raw I, Q signals 

            mixer config: dictionary with axes, center and phase rotation params
            of the ellipse as found in the fitEllipse function. This is initialized
            in the exp_globals function

    '''
    center = mixer_config['center']
    axes   = mixer_config['axes']
    phi    = mixer_config['phi']

    Isprime = np.cos(phi)*(Is-center[0]) + np.sin(phi)*(Qs-center[1]) + center[0]
    Qsprime = -np.sin(phi)*(Is-center[0]) + np.cos(phi)*(Qs-center[1]) 
    Qsprime = Qsprime*axes[0]/axes[1] + center[1]
    return Isprime, Qsprime

def remove_slow_drift(I, Q, t):
    '''
    remove_slow_drift _summary_

    :param I: _description_
    :type I: _type_
    :param Q: _description_
    :type Q: _type_
    :param t: _description_
    :type t: _type_
    :return: _description_
    :rtype: _type_
    '''    
    angle = -0.00035*t*np.pi/180
    rot_mat = np.array([[np.cos(angle), -np.sin(angle)], 
                         [np.sin(angle), np.cos(angle)]])
    return rot_mat@np.array([I,Q])

def generate_filter(card, settings):
    '''
    generate_filter _summary_

    :param card: _description_
    :type card: _type_
    :param settings: _description_
    :type settings: _type_
    '''    
    exp_globals = settings['exp_globals']
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

def extract_data(raw_data, xaxis, settings):
    '''
    Extracts the data from a trace. Finds the indices of start/ stop for both
    data and background (assumes that they are the same length, which should
    be enforced by the card samples in the actual exp script) and splices the 
    correct ranges from the raw data. Returns a time axis for the data window 
    and subtracts mean of background if specified.

    ALL VALUES SHOULD BE IN TIME UNITS (base seconds)


    Parameters
    ________________
        

        init_buffer: 
            buffer specified to card before the measurement tone
        emp_delay: 
            combination of line delay and other delays that correctly shifts the digitizer to match the HDAWG time axis
        meas_window: 
            width of the measurement pulse
        post_buffer: 
            time to wait after the pulse before measuring background

    '''
    measurement_pulse = settings['exp_globals']['measurement_pulse']
    init_buffer = measurement_pulse['init_buffer']
    emp_delay   = measurement_pulse['emp_delay']
    meas_window = measurement_pulse['meas_window']
    post_buffer = measurement_pulse['post_buffer']
    
    timestep   = xaxis[1] - xaxis[0]
    data_start = int((init_buffer + emp_delay)/timestep)
    back_start = int((init_buffer + emp_delay + meas_window + post_buffer)/timestep)
    window_width = int(meas_window/timestep)
    
    data_x = xaxis[data_start:data_start+window_width]
    
    data    = raw_data[data_start:data_start+window_width]
    background = raw_data[back_start:back_start+window_width]
    back_val = np.mean(background)
    
    if settings['exp_settings']['subtract_background']:
        return data - back_val, data_x, raw_data - back_val, xaxis
    else:
        return data, data_x, raw_data, xaxis
        
        
def extract_data_heterodyne(raw_data, xaxis, settings):
    '''
    Extracts the data from a trace. Finds the indices of start/ stop for both
    data and background (assumes that they are the same length, which should
    be enforced by the card samples in the actual exp script) and splices the 
    correct ranges from the raw data. Returns a time axis for the data window 
    and subtracts mean of background if specified.

    ALL VALUES SHOULD BE IN TIME UNITS (base seconds)

    This has been modified from extract_data so that it will work with heterodyne and digital down conversion
    
    Parameters
    _________________

        init_buffer: 
            buffer specified to card before the measurement tone
        emp_delay: 
            combination of line delay and other delays that correctly shifts the digitizer to match the HDAWG time axis
        meas_window: 
            width of the measurement pulse
        post_buffer: 
            time to wait after the pulse before measuring background
        
        
    '''
    measurement_pulse = settings['exp_globals']['measurement_pulse']
    init_buffer = measurement_pulse['init_buffer']
    emp_delay   = measurement_pulse['emp_delay']
    meas_window = measurement_pulse['meas_window']
    post_buffer = measurement_pulse['post_buffer']
    
    timestep   = xaxis[1] - xaxis[0]
    data_start = int((init_buffer + emp_delay)/timestep)
    back_start = int((init_buffer + emp_delay + meas_window + post_buffer)/timestep)
    window_width = int(meas_window/timestep)
    
    data_x = xaxis[data_start:data_start+window_width]
    background = raw_data[back_start:back_start+window_width]
    back_val = np.mean(background)

    if settings['exp_settings']['subtract_background']:
        raw_data = raw_data-back_val

    #now I am ready to filter the data.
    LPF = settings['LPF']
    digLO_sin = settings['digLO_sin']
    digLO_cos = settings['digLO_cos']
    
    filtered_sin_full = signal.sosfilt(LPF, raw_data*digLO_sin)
    filtered_cos_full = signal.sosfilt(LPF, raw_data*digLO_cos)
    
    filtered_sin = filtered_sin_full[data_start:data_start+window_width]
    filtered_cos = filtered_cos_full[data_start:data_start+window_width]
    
    return filtered_cos, filtered_sin, data_x, filtered_cos_full, filtered_sin_full, xaxis
        
def estimate_time(t1, t2, steps):
    '''
    estimate_time _summary_

    :param t1: _description_
    :type t1: _type_
    :param t2: _description_
    :type t2: _type_
    :param steps: _description_
    :type steps: _type_
    '''    
    one_step = t2-t1
    total_time = one_step*steps
    
    final_time = datetime.now() + timedelta(seconds=(total_time-one_step))
    mins = np.round(total_time/60,1)
    hours = np.round(total_time/3600, 2)
    
    print('    ')
    print('estimated time for this scan : {} mins or {} hours'.format(mins, hours))
    print('expected finish time: {}'.format(final_time.ctime()))
    print('    ')

def heterodyne_martin(Ipp, Qpp, xaxis, settings):
    '''
    heterodyne_martin _summary_

    :param Ipp: _description_
    :type Ipp: _type_
    :param Qpp: _description_
    :type Qpp: _type_
    :param xaxis: _description_
    :type xaxis: _type_
    :param settings: _description_
    :type settings: _type_
    :return: _description_
    :rtype: _type_
    '''    
    I_cos, I_sin, Itime, I_cos_full, I_sin_full, time_full = extract_data_heterodyne(Ipp, xaxis, settings)
    Q_cos, Q_sin, Qtime, Q_cos_full, Q_sin_full, time_full = extract_data_heterodyne(Qpp, xaxis, settings)
    Qprime_sin = Q_cos
    Qprime_cos = -Q_sin
    
    Qprime_sin_full = Q_cos_full
    Qprime_cos_full = -Q_sin_full
    
    
    Q_window  = (I_sin +  Qprime_sin)/2
    I_window = (I_cos + Qprime_cos)/2
    
    Q_full  = (I_sin_full +  Qprime_sin_full)/2
    I_full = (I_cos_full + Qprime_cos_full)/2
    
    return I_window, Q_window, Itime, I_full, Q_full, time_full

def read_and_process_two_pulses(card, settings, plot):
    '''
    read_and_process_two_pulses _summary_

    :param card: _description_
    :type card: _type_
    :param settings: _description_
    :type settings: _type_
    :param plot: _description_
    :type plot: _type_
    :return: _description_
    :rtype: _type_
    '''    
    card.ArmAndWait()
    I, Q = card.ReadAllData()
    Ipeven = np.mean(I[::2], 0)
    Qpeven = np.mean(Q[::2], 0)
    Ipodd = np.mean(I[1::2], 0)
    Qpodd = np.mean(Q[1::2], 0)
    
    mixer_config = settings['exp_globals']['mixer_config']
    Ippeven, Qppeven = remove_IQ_ellipse(Ipeven, Qpeven, mixer_config)
    Ippodd, Qppodd = remove_IQ_ellipse(Ipodd, Qpodd, mixer_config)
    xaxis = np.linspace(0, card.samples, card.samples, endpoint=False)/card.sampleRate
    
    I1_window, Q1_window, time_window, I1_full, Q1_full, time_full = heterodyne_martin(Ippeven, Qppeven, xaxis, settings)
    I2_window, Q2_window, time_window, I2_full, Q2_full, time_full = heterodyne_martin(Ippeven, Qppeven, xaxis, settings)
    Inet = I1_window-I2_window
    Qnet = Q1_window-Q2_window
    Inet_full = I1_full-I2_full
    Qnet_full = Q1_full-Q2_full
    return Inet, Qnet, Inet_full, Qnet_full, xaxis

def read_and_process_dual_readout(card, settings, plot):
    '''
    

    Parameters
    ----------
    card : TYPE
        DESCRIPTION.
    settings : TYPE
        DESCRIPTION.
    plot : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    '''
    card.ArmAndWait()
    I, Q = card.ReadAllData()
    boost = np.mean(I, 0)
    readout = np.mean(Q, 0)

    xaxis = np.linspace(0, card.samples, card.samples, endpoint=False)/card.sampleRate
            
    boost_I, boost_Q, Itime, I_cos_full, I_sin_full, time_full = extract_data_heterodyne(boost, xaxis, settings)
    readout_I, readout_Q, Qtime, Q_cos_full, Q_sin_full, time_full = extract_data_heterodyne(readout, xaxis, settings)
    
    
    if plot:
        fig0 = plt.figure(97)
        plt.clf()
        ax = plt.subplot(1,1,1)
        plt.plot(xaxis*1e6, boost, label = 'raw boost')
        plt.plot(xaxis*1e6, readout, label = 'raw readout')
        plt.xlabel('Time (us)')
        plt.ylabel('Voltage')
        plt.title('Card Voltages')
        ax.legend(loc = 'upper right')
      
        fig0.canvas.draw()
        fig0.canvas.flush_events()
    
    return boost_I, boost_Q, readout_I, readout_Q, xaxis        


def read_and_process_single_channel(card, settings, plot):
    '''
    The original version of this function wanted to convert to 
    amplitude(t) and phase(t). This has been found to be problematic.
    To get the old version of operation, set
    IQstorage = False
    
    IQstorage = True will instead return I(t) and Q(t) for 
    later processing.
    '''
    card.ArmAndWait()
    I, Q = card.ReadAllData()
    Ip = np.mean(I, 0)

    xaxis = np.linspace(0, card.samples, card.samples, endpoint=False)/card.sampleRate
            
    I_cos, I_sin, Itime, I_cos_full, I_sin_full, time_full = extract_data_heterodyne(Ip, xaxis, settings)
    
    I_full = I_cos_full
    Q_full = I_sin_full
    I_window = I_cos
    Q_window = I_sin
    
    if plot:
        fig0 = plt.figure(97)
        plt.clf()
        ax = plt.subplot(1,1,1)
        plt.plot(xaxis*1e6, Ip, label = 'raw V1')
        plt.xlabel('Time (us)')
        plt.ylabel('Voltage')
        plt.title('Card Voltages')
        ax.legend(loc = 'upper right')
      
        fig0.canvas.draw()
        fig0.canvas.flush_events()
        
        amp = np.sqrt(Q_window**2+I_window**2) #this is just the I signal
        amp_full = np.sqrt(I_full**2+Q_full**2)
        plot_data_extraction(amp, Itime, amp_full, time_full, I_full, Q_full)
    
    return I_window, Q_window, I_full, Q_full, xaxis


def read_and_process(card, settings, plot, IQstorage = True):
    '''The original version of this function wanted to convert to 
    amplitude(t) and phase(t). This has been found to be problematic.
    To get the old version of operation, set
    IQstorage = False
    
    IQstorage = True will instead return I(t) and Q(t) for 
    later processing.
    '''
    card.ArmAndWait()
    I, Q = card.ReadAllData()
    Ip = np.mean(I, 0)
    Qp = np.mean(Q, 0)
    mixer_config = settings['exp_globals']['mixer_config']
    Ipp, Qpp = remove_IQ_ellipse(Ip, Qp, mixer_config)
#    Ipp, Qpp = remove_slow_drift(Ipp, Qpp, time_el)
    xaxis = np.linspace(0, card.samples, card.samples, endpoint=False)/card.sampleRate

#    Idata, Itime, Ifull, time_full = extract_data(Ipp, xaxis, settings)
#    Qdata, Qtime, Qfull, time_full = extract_data(Qpp, xaxis, settings)
    
    if not IQstorage:
        Idata, Itime, Ifull, time_full = extract_data(Ipp, xaxis, settings)
        Qdata, Qtime, Qfull, time_full = extract_data(Qpp, xaxis, settings)
        
        amp_full = np.sqrt(Ifull**2+Qfull**2)
        if settings['exp_globals']['IF'] == 0:
            phase_full = np.arctan2(Qfull, Ifull)*180/np.pi
        else:
            raw_angle = np.arctan2(Qfull, Ifull)*180/np.pi
            phase_full = np.mod(raw_angle + 360*settings['exp_globals']['IF']*xaxis, 360)
            
    #        plt.figure(101)
    #        plt.clf()
    #        ax = plt.subplot(1,2,1)
    #        plt.plot(xaxis, raw_angle)
    #        plt.title('raw phase angle')
    #        ax = plt.subplot(1,2,2)
    #        plt.plot(xaxis, phase_full)
    #        plt.show()
    #        plt.title('(hopefully) corrected phase angle')
    
        amp = np.sqrt(Idata**2+Qdata**2)
        
        if settings['exp_globals']['IF'] == 0:
            phase = np.arctan2(Qdata, Idata)*180/np.pi
        else:
            raw_angle = np.arctan2(Qdata, Idata)*180/np.pi
            phase = np.mod(raw_angle + 360*settings['exp_globals']['IF']*Itime, 360)
    
        if plot:
            plot_data_extraction(amp, Itime, amp_full, time_full, Ifull, Qfull)
    
        return amp, phase, amp_full, phase_full, xaxis
    else:
        #do not convert to amp(t) and phase(t)
#        if plot:
#            amp = np.sqrt(Idata**2+Qdata**2) #this is just a guide to theeye for locating the pulse
#            amp_full = np.sqrt(Ifull**2+Qfull**2)
#            plot_data_extraction(amp, Itime, amp_full, time_full, Ifull, Qfull)
        
        if settings['exp_globals']['IF'] == 0:
#            Idata, Itime, Ifull, time_full = extract_data(Ipp, xaxis, settings)
#            Qdata, Qtime, Qfull, time_full = extract_data(Qpp, xaxis, settings)
#            if plot:
#                amp = np.sqrt(Idata**2+Qdata**2) #this is just a guide to theeye for locating the pulse
#                amp_full = np.sqrt(Ifull**2+Qfull**2)
#                plot_data_extraction(amp, Itime, amp_full, time_full, Ifull, Qfull)
            
            #matching newer names
            I_window, Itime, I_full, time_full = extract_data(Ipp, xaxis, settings)
            Q_window, Qtime, Q_full, time_full = extract_data(Qpp, xaxis, settings)
            if plot:
                amp = np.sqrt(I_window**2+Q_window**2) #this is just a guide to theeye for locating the pulse
                amp_full = np.sqrt(I_full**2+Q_full**2)
                plot_data_extraction(amp, Itime, amp_full, time_full, I_full, Q_full)
        else:
            #Quick fix to the problem of full cancellation in the DDC data. Turns out the channels got swapped 
            #during a reshuffle and combining the channels incorrectly leads to near perfect cancellation (offset by
            #the mixer impairements). For now I just swapped the definition of I and Q to match the combination phase
            I_cos, I_sin, Itime, I_cos_full, I_sin_full, time_full = extract_data_heterodyne(Ipp, xaxis, settings)
            Q_cos, Q_sin, Qtime, Q_cos_full, Q_sin_full, time_full = extract_data_heterodyne(Qpp, xaxis, settings)
            
            
                
            #rotate the mixer Q signal back into I so they can be averaged properly
            theta = -np.pi/2
            Qprime_sin = Q_sin*np.cos(theta) + -Q_cos *np.sin(theta) 
            Qprime_cos = Q_sin*np.sin(theta) + Q_cos*np.cos(theta)
            
            Qprime_sin_full = Q_sin_full*np.cos(theta) + -Q_cos_full *np.sin(theta) 
            Qprime_cos_full = Q_sin_full*np.sin(theta) + Q_cos_full*np.cos(theta)
            
            
            Q_window  = (I_sin +  Qprime_sin)/2
            I_window = (I_cos + Qprime_cos)/2
            
            Q_full  = (I_sin_full +  Qprime_sin_full)/2
            I_full = (I_cos_full + Qprime_cos_full)/2
            
            if plot:
                fig0 = plt.figure(97)
                plt.clf()
                ax = plt.subplot(1,2,1)
                plt.plot(xaxis*1e6, Ip, label = 'raw V1')
                plt.plot(xaxis*1e6, Qp, label = 'raw V2')
                plt.xlabel('Time (us)')
                plt.ylabel('Voltage')
                plt.title('Card Voltages')
                ax.legend(loc = 'upper right')
                
                ax = plt.subplot(1,2,2)
                plt.plot(xaxis*1e6, np.sqrt(Ip**2 + Qp**2), label = 'crude amplitude')
                plt.plot(xaxis*1e6, np.sqrt(Ipp**2 + Qpp**2), label = 'mixer corrected')
                plt.xlabel('Time (us)')
                plt.ylabel('Voltage')
                plt.title('Rough Pulse Amplitude')
                ax.legend(loc = 'upper right')
                plt.show()
                fig0.canvas.draw()
                fig0.canvas.flush_events()
                
                amp = np.sqrt(Q_window**2+I_window**2) #this is just the I signal
                amp_full = np.sqrt(I_full**2+Q_full**2)
                plot_data_extraction(amp, Itime, amp_full, time_full, I_full, Q_full)
        
        return I_window, Q_window, I_full, Q_full, xaxis
            
        

def plot_data_extraction(amp_extract, time_extract, amp_full, time_full, I, Q):
    '''
    plot_data_extraction _summary_

    :param amp_extract: _description_
    :type amp_extract: _type_
    :param time_extract: _description_
    :type time_extract: _type_
    :param amp_full: _description_
    :type amp_full: _type_
    :param time_full: _description_
    :type time_full: _type_
    :param I: _description_
    :type I: _type_
    :param Q: _description_
    :type Q: _type_
    '''    
    fig = plt.figure(99)
    plt.clf()
    plt.plot(time_full*1e6, amp_full, 'r')
    plt.plot(time_extract*1e6, amp_extract,'b')
    plt.xlabel('Time (us)')
    plt.title('Data window check')
    plt.show()
    fig.canvas.draw()
    fig.canvas.flush_events()

    fig2 = plt.figure(98)
    plt.clf()
    plt.subplot(1,3,1)
    plt.plot(time_full*1e6, I, 'b')
    plt.xlabel('Time (us)')
    plt.title('I')    

    plt.subplot(1,3,2)
    plt.plot(time_full*1e6, Q, 'r')
    plt.xlabel('Time (us)')
    plt.title('Q')    

    plt.subplot(1,3,3)
    plt.plot(time_full*1e6, I, 'b')
    plt.plot(time_full*1e6, Q, 'r')
    plt.xlabel('Time (us)')
    plt.title('I and Q')    

    plt.suptitle('Single read I and Q')
    plt.show()
    fig2.canvas.draw()
    fig2.canvas.flush_events()

def configure_hdawg(hdawg, settings):
    '''
    configure_hdawg _summary_

    :param hdawg: _description_
    :type hdawg: _type_
    :param settings: _description_
    :type settings: _type_
    '''

    hdawg_config = settings['hdawg_config']
    amp = hdawg_config['amplitude']
    trigger_slope = hdawg_config['trigger_slope']
    hdawg.AWGs[0].samplerate = hdawg_config['samplerate']
    hdawg.channelgrouping = hdawg_config['channelgrouping']
    hdawg.Channels[0].configureChannel(amp=amp,marker_out='Marker', hold='False')
    hdawg.Channels[1].configureChannel(amp=amp,marker_out='Marker', hold='False')
    hdawg.Channels[2].configureChannel(amp=amp,marker_out='Marker', hold='False')
    hdawg.Channels[3].configureChannel(amp=amp,marker_out='Marker', hold='False')
    hdawg.AWGs[0].Triggers[0].configureTrigger(slope=trigger_slope,channel='Trigger in 1')
    
def configure_card(card, settings):
    '''
    Helper function to configure the card from a set of settings. This will
    force a standard definition of what the digitizer timing should be. Computes
    the total acquisition time and converts it to samples (also configures the 
    rest of the digitizer but this is the main part that requires logic)

    Inputs
    _______

        settings dictionary with the following keys (should be initialized from
        the get_default_settings method)

        meas_window: 
            width of measurment tone
        meas_pos: 
            position of measurement tone relative to the rise edge of the trigger
        emp_delay: 
            line delay and other delays accumulated between the AWG and the digitizer
        init_buffer: 
            buffer to collect data before the pulse
        post_buffer: 
            buffer after measurment tone to wait out the ringing before background subtraction
        averages: 
            number of averages for the card to perform in HW
        segments: 
            number of segments (will be averaged together), useful when number of averages gets very high ~>50e3
        sampleRate: 
            sampling rate of digitizer (make this lower for longer acquisitions)
        activeChannels: 
            active channels on digitizer (both by default)
        timeout: 
            timeout (in s) for VISA communication (make this longer for longer acquisitions)
        channelRange: 
            full scale (peak to peak) of each channel, 0.5 or 2.5 V

    '''
    exp_globals = settings['exp_globals']
    exp_settings = settings['exp_settings']

    measurement_pulse = exp_globals['measurement_pulse']
    card_config = exp_globals['card_config']

    #Compute total acquisition time
    meas_pos    = measurement_pulse['meas_pos']
    meas_window = measurement_pulse['meas_window']
    emp_delay   = measurement_pulse['emp_delay']
    init_buffer = measurement_pulse['init_buffer']
    post_buffer = measurement_pulse['post_buffer']

    card_time = 2*meas_window + emp_delay + init_buffer + post_buffer
    meas_samples = card_config['sampleRate']*card_time

    #Compute trigger delay, has to be multiple of 32ns for Acquiris
    trigger_delay = np.floor((meas_pos - init_buffer)/32e-9)*32e-9
    
    card.channelRange   = card_config['channelRange']
    card.timeout        = card_config['timeout']
    card.sampleRate     = card_config['sampleRate']
    card.activeChannels = card_config['activeChannels']
    card.triggerSlope   = card_config['triggerSlope']
    card.averages       = exp_settings['averages']
    card.segments       = exp_settings['segments']
    card.triggerDelay   = trigger_delay
    card.samples        = int(meas_samples)
    card.SetParams()    