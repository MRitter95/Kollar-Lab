# -*- coding: utf-8 -*-
"""
Created on Tue May 17 18:14:04 2022

@author: Kollarlab
"""
import numpy as np
import scipy.signal

def heterodyne_DDC(I, Q, settings):
    '''
    heterodyne_DDC _summary_

    :param I: _description_
    :type I: _type_
    :param Q: _description_
    :type Q: _type_
    :param settings: _description_
    :type settings: _type_
    :return: _description_
    :rtype: _type_
    '''    
    [I1, Q1, xaxis] = demod(I, settings)
    [I2, Q2, xaxis] = demod(Q, settings)
    It = I1+Q2
    Qt = Q1-I2
    return [It,Qt, xaxis]

def demod(signal, settings):
    '''
    demod _summary_

    :param signal: _description_
    :type signal: _type_
    :param settings: _description_
    :type settings: _type_
    :return: _description_
    :rtype: _type_
    '''    
    IF = settings['IF']
    sample_rate = settings['sample_rate']
    
    xaxis   = np.linspace(0, len(signal), len(signal))/sample_rate
    DDC_sin = np.sin(2*np.pi*IF*xaxis)
    DDC_cos = np.cos(2*np.pi*IF*xaxis)
    demodI, time = filter_sig(signal*DDC_cos, settings)
    demodQ, time = filter_sig(signal*DDC_sin, settings)
    return [demodI, demodQ, time]

def filter_sig(signal, settings):
    '''
    filter_sig _summary_

    :param signal: _description_
    :type signal: _type_
    :param settings: _description_
    :type settings: _type_
    :return: _description_
    :rtype: _type_
    '''

    method = settings['method']
    IF     = settings['cutoff']
    
    sample_rate  = settings['sample_rate']
    filter_order = settings['order']
    filter_atten = settings['stop_atten']
    
    if method=='period':
        samples_per_period = int(sample_rate/IF)
        return period(signal, samples_per_period, sample_rate)
    if method=='low_pass':
        return low_pass(signal, filter_order, filter_atten, IF, sample_rate)
        
def period(signal, period, sample_rate):
    '''
    period _summary_

    :param signal: _description_
    :type signal: _type_
    :param period: _description_
    :type period: _type_
    :param sample_rate: _description_
    :type sample_rate: _type_
    :return: _description_
    :rtype: _type_
    '''

    full_periods = int(np.floor(len(signal)/period))
    split = np.array(np.split(signal[0:int(full_periods*period)], full_periods))
    clean = np.mean(split, axis=1)
    xaxis = np.linspace(0, len(signal), full_periods)/sample_rate
    if int(full_periods*period)<len(signal):
        remainder = signal[int(full_periods*period)+1:]
        scaled_remainder = np.mean(remainder)*(len(remainder)/period)**2
        xaxis = np.linspace(0, len(signal), full_periods+1)/sample_rate
        return [np.append(clean, scaled_remainder), xaxis]
    return [clean, xaxis]
       
def low_pass(signal, filter_N, filter_rs, filter_cutoff, sample_rate):
    '''
    low_pass _summary_

    :param signal: _description_
    :type signal: _type_
    :param filter_N: _description_
    :type filter_N: _type_
    :param filter_rs: _description_
    :type filter_rs: _type_
    :param filter_cutoff: _description_
    :type filter_cutoff: _type_
    :param sample_rate: _description_
    :type sample_rate: _type_
    :return: _description_
    :rtype: _type_
    '''

    LPF = scipy.signal.cheby2(filter_N, filter_rs, filter_cutoff, btype='low', analog=False, output='sos', fs=sample_rate)
    filtered_sig = scipy.signal.sosfilt(LPF, signal)
    xaxis = np.linspace(0, len(signal), len(signal))/sample_rate
    return [filtered_sig, xaxis]