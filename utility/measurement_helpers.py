# -*- coding: utf-8 -*-
"""
Created on Wed Mar  3 09:20:52 2021

@author: Kollarlab
"""
import numpy as np

def check_inputs(inputs, defaults):
    '''
    Checks that the given input dictionary has the correct settings. It's easy
    to accidentally mistype something or us an old naming convention so this 
    function will throw an error if the keys in the dictionaries don't match
    Input params:
        inputs: input dictionary that is modified by user
        defaults: default dictionary specified by script
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
    Input params:
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
   
def extract_data(raw_data, xaxis, settings):
    '''
    Extracts the data from a trace. Finds the indices of start/ stop for both
    data and background (assumes that they are the same length, which should
    be enforced by the card samples in the actual exp script) and splices the 
    correct ranges from the raw data. Returns a time axis for the data window 
    and subtracts mean of background if specified
    Key input params:
    ALL VALUES SHOULD BE IN TIME UNITS (base seconds)
        init_buffer: buffer specified to card before the measurement tone
        emp_delay: combination of line delay and other delays that correctly
                   shifts the digitizer to match the HDAWG time axis
        meas_window: width of the measurement pulse
        post_buffer: time to wait after the pulse before measuring background
    '''
    measurement_pulse = settings['exp_globals']['measurement_pulse']
    init_buffer = measurement_pulse['init_buffer']
    emp_delay   = measurement_pulse['emp_delay']
    meas_window = measurement_pulse['meas_window']
    post_buffer = measurement_pulse['post_buffer']
    
    timestep   = xaxis[1] - xaxis[0]
    data_start = int((init_buffer + emp_delay)/timestep)
    back_start = int((init_buffer + emp_delay + meas_window + pulse_buffer)/timestep)
    window_width = int(meas_window/timestep)
    
    #print(timestep)
    #print(data_start)
    #print(back_start)
    #print(window_width)
    
    data_x = xaxis[data_start:data_start+window_width]
    
    data    = raw_data[data_start:data_start+window_width]
    background = raw_data[back_start:back_start+window_width]
    back_val = np.mean(background)
    
    if settings['subtract_background']:
        return data - back_val, data_x, raw_data - back_val, xaxis
    else:
        return data, data_x, raw_data, xaxis

def configure_card(card, settings):
    '''
    Helper function to configure the card from a set of settings. This will
    force a standard definition of what the digitizer timing should be. Computes
    the total acquisition time and converts it to samples (also configures the 
    rest of the digitizer but this is the main part that requires logic)
    Inputs:
        settings dictionary with the following keys (should be initialized from
        the get_default_settings method)
        meas_window: width of measurment tone
        meas_pos: position of measurement tone relative to the rise edge of the 
            trigger
        emp_delay: line delay and other delays accumulated between the 
            AWG and the digitizer
        init_buffer: buffer to collect data before the pulse
        post_buffer: buffer after measurment tone to wait out the ringing before
            background subtraction
        averages: number of averages for the card to perform in HW
        segments: number of segments (will be averaged together), useful when
            number of averages gets very high ~>50e3
        sampleRate: sampling rate of digitizer (make this lower for longer acquisitions)
        activeChannels: active channels on digitizer (both by default)
        timeout: timeout (in s) for VISA communication (make this longer for 
                         longer acquisitions)
        channelRange: full scale (peak to peak) of each channel, 0.5 or 2.5 V
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
    card.averages       = exp_settings['averages']
    card.segments       = exp_settings['segments']
    card.triggerDelay   = trigger_delay
    card.samples        = int(meas_samples)
    card.SetParams()    