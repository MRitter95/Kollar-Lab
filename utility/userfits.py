# -*- coding: utf-8 -*-
"""
Created on Tue Dec  8 15:27:44 2020

@author: Kollarlab
"""
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from lmfit.models import LorentzianModel, ConstantModel, GaussianModel

def T1_model(x, tau, amp, offset):
    '''
    T1_model _summary_

    :param x: _description_
    :type x: _type_
    :param tau: _description_
    :type tau: _type_
    :param amp: _description_
    :type amp: _type_
    :param offset: _description_
    :type offset: _type_
    :return: _description_
    :rtype: _type_
    '''    
    return amp*np.exp(- (x)/tau) + offset

def T2_model(x, tau, amp, offset, freq, phi):
    '''
    T2_model _summary_

    :param x: _description_
    :type x: _type_
    :param tau: _description_
    :type tau: _type_
    :param amp: _description_
    :type amp: _type_
    :param offset: _description_
    :type offset: _type_
    :param freq: _description_
    :type freq: _type_
    :param phi: _description_
    :type phi: _type_
    :return: _description_
    :rtype: _type_
    '''    
    pi = np.pi
    return amp*np.cos(2*pi*freq*x+phi)*np.exp(- (x)/tau) + offset

def fit_T1(taus, amps, fit_guess):
    '''
    fit_T1 _summary_

    :param taus: _description_
    :type taus: _type_
    :param amps: _description_
    :type amps: _type_
    :param fit_guess: _description_
    :type fit_guess: _type_
    :return: _description_
    :rtype: _type_
    '''

    ts = np.linspace(min(taus), max(taus), 10*len(taus))
    fit_curve = np.zeros(len(ts))

    tau = 0
    amp = 0
    offset = 0

    try:
        fit_out, pcov = curve_fit(T1_model, taus, amps, p0 = fit_guess)
        tau, amp, offset, *_ = fit_out
        fit_curve = T1_model(ts, tau, amp, offset)
    except:
        print('Fit did not converge, returning zeros')
        return tau, amp, offset, ts, fit_curve

    return tau, amp, offset, ts, fit_curve

def fit_T2(taus, amps, fit_guess):
    '''
    fit_T2 _summary_

    :param taus: _description_
    :type taus: _type_
    :param amps: _description_
    :type amps: _type_
    :param fit_guess: _description_
    :type fit_guess: _type_
    :return: _description_
    :rtype: _type_
    '''

    ts = np.linspace(min(taus), max(taus), 10*len(taus))
    fit_curve = np.zeros(len(ts))

    tau = 0
    amp = 0
    offset = 0
    freq = 0
    phi = 0

    try:
        bounds = ([0, -np.inf, -np.inf, -np.inf, -np.inf], [1, np.inf, np.inf, np.inf, np.inf])
        fit_out, pcov = curve_fit(T2_model, taus, amps, p0=fit_guess)#, bounds=bounds)
        tau, amp, offset, freq, phi, *_ = fit_out
        fit_curve = T2_model(ts, tau, amp, offset, freq, phi)   
    except:
        print('Fit did not converge, returning zeros')
        return tau, amp, offset, freq, phi, ts, fit_curve 
    
    return tau, amp, offset, freq, phi, ts, fit_curve 

def convert_to_linear(yvals):
    '''
    convert_to_linear _summary_

    :param yvals: _description_
    :type yvals: _type_
    :return: _description_
    :rtype: _type_
    '''    
    linear = 10**(yvals/20)  
    return linear

def fit_gaussian(freqs, mags, plot=False, fig_num=None):
    '''
    fit_gaussian _summary_

    :param freqs: _description_
    :type freqs: _type_
    :param mags: _description_
    :type mags: _type_
    :param plot: _description_, defaults to False
    :type plot: bool, optional
    :param fig_num: _description_, defaults to None
    :type fig_num: _type_, optional
    :return: _description_
    :rtype: _type_
    '''    
    line = convert_to_linear(mags)
    data_test = -(line-max(line))
    
    peak = GaussianModel()
    const = ConstantModel()
    mod = peak + const
    
    center = 0
    sigma = 0
    amp   = 0
    residuals = 0
    try:
        pars = peak.guess(data_test, x=freqs)
        pars += const.make_params()
        
        out = mod.fit(data_test, pars, x=freqs)
        fit_params = out.best_values
        center = fit_params['center']
        sigma  = fit_params['sigma']
        amp    = fit_params['amplitude']/(np.pi*sigma)
        model  = mod.eval(params=out.params, x=freqs)
        amp_dB = 10*np.log10(min(model)/max(model))
        
        residuals = data_test-model
    except:
        print('Fit did not converge, returning zeros')
        return center, sigma
    
    if plot:
        if fig_num is None:
            fig = plt.figure()
        else:
            fig = plt.figure(fig_num)
        plt.clf()
        plt.plot(freqs, data_test)
        plt.plot(freqs, model)
#        plt.show()
        fig.canvas.draw()
        fig.canvas.flush_events()
    
        
    return center, 2*sigma, amp_dB#, residuals

def fit_lorentzian(freqs, mags, plot=False, fig_num=None):
    '''
    fit_lorentzian _summary_

    :param freqs: _description_
    :type freqs: _type_
    :param mags: _description_
    :type mags: _type_
    :param plot: _description_, defaults to False
    :type plot: bool, optional
    :param fig_num: _description_, defaults to None
    :type fig_num: _type_, optional
    :return: _description_
    :rtype: _type_
    '''    
    line = convert_to_linear(mags)
    data_test = -(line-max(line))
    
    peak = LorentzianModel()
    const = ConstantModel()
    mod = peak + const
    
    center = 0
    sigma = 0
    amp   = 0
    residuals = 0
    try:
        pars = peak.guess(data_test, x=freqs)
        pars += const.make_params()
        
        out = mod.fit(data_test, pars, x=freqs)
        fit_params = out.best_values
        center = fit_params['center']
        sigma  = fit_params['sigma']
        amp    = fit_params['amplitude']/(np.pi*sigma)
        model  = mod.eval(params=out.params, x=freqs)
        amp_dB = 10*np.log10(min(model)/max(model))
        residuals = data_test-model
    except:
        print('Fit did not converge, returning zeros')
        return center, sigma
    
    if plot:
        if fig_num is None:
            fig = plt.figure()
        else:
            fig = plt.figure(fig_num)
        plt.clf()
        plt.plot(freqs, data_test)
        plt.plot(freqs, model)
#        plt.show()
        fig.canvas.draw()
        fig.canvas.flush_events()
        
    return center, 2*sigma, amp_dB#, residuals
