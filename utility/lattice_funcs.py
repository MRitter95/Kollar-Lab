# -*- coding: utf-8 -*-
"""
Created on Mon Mar 25 15:48:20 2024

@author: kollarlab
"""

import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import userfuncs
from utility.userfits_v2 import fit_model
from utility.plotting_tools import general_colormap_subplot
import os


################################################################################
def full_data_fit(spec_file,hanger = False):
    '''
    full_data_fit _summary_

    :param spec_file: _description_
    :type spec_file: _type_
    :param hanger: _description_, defaults to False
    :type hanger: bool, optional
    :return: _description_
    :rtype: _type_
    '''    
    #spec_file: str, filename of relevant data
    #hanger: bool, whether the device is a hanger
    #Loads spec flux data, finds max/min for trans and spec values to extract cavity/qubit frequencies at each voltage point.
    full_data = userfuncs.LoadFull(spec_file)

    if 'powers' in full_data[0]:
        xaxis = full_data[0]['powers']
    elif 'voltages' in full_data[0]:
        xaxis = full_data[0]['voltages']
    elif 'fluxes' in full_data[0]:
        xaxis = full_data[0]['fluxes']


    trans_freqs_GHz = full_data[0]['transdata']['xaxis']
    trans_mags = full_data[0]['transdata']['phases']
    
    cfreqs = []
    
    for f in range(0,len(xaxis)):
        if hanger:
            fholder = trans_freqs_GHz[np.argmin(trans_mags[f])]
        else:
            fholder = trans_freqs_GHz[np.argmax(trans_mags[f])]
        cfreqs.append(fholder)
    
    spec_freqs_GHz = full_data[0]['specdata']['xaxis']
    spec_mags = full_data[0]['specdata']['phases']
    
    qfreqs = []
    
    for f in range(0,len(xaxis)):
        if hanger:
            qholder = spec_freqs_GHz[np.argmax(spec_mags[f])]
        else:
            qholder = spec_freqs_GHz[np.argmin(spec_mags[f])]
        qfreqs.append(qholder)
    
    
    return xaxis, cfreqs, qfreqs



def full_data_fit_mags(spec_file,hanger = False):
    '''
    full_data_fit_mags _summary_

    :param spec_file: _description_
    :type spec_file: _type_
    :param hanger: _description_, defaults to False
    :type hanger: bool, optional
    :return: _description_
    :rtype: _type_
    '''    
    #spec_file: str, filename of relevant data
    #hanger: bool, whether the device is a hanger
    #Loads spec flux data, finds max/min for trans and spec values to extract cavity/qubit frequencies at each voltage point.
    full_data = userfuncs.LoadFull(spec_file)
    
    if 'powers' in full_data[0]:
        xaxis = full_data[0]['powers']
    elif 'voltages' in full_data[0]:
        xaxis = full_data[0]['voltages']
    elif 'fluxes' in full_data[0]:
        xaxis = full_data[0]['fluxes']
    

    trans_freqs_GHz = full_data[0]['transdata']['xaxis']
    trans_mags = full_data[0]['transdata']['phases']
    
    cfreqs = []
    
    for f in range(0,len(xaxis)):
        if hanger:
            fholder = trans_freqs_GHz[np.argmin(trans_mags[f])]
        else:
            fholder = trans_freqs_GHz[np.argmax(trans_mags[f])]
        cfreqs.append(fholder)
    
    spec_freqs_GHz = full_data[0]['specdata']['xaxis']
    spec_mags = full_data[0]['specdata']['mags']
    
    qfreqs = []
    
    for f in range(0,len(xaxis)):
        if hanger:
            qholder = spec_freqs_GHz[np.argmax(spec_mags[f])]
        else:
            qholder = spec_freqs_GHz[np.argmin(spec_mags[f])]
        qfreqs.append(qholder)
    
    
    return xaxis, cfreqs, qfreqs



def trans_data_fit(spec_file,hanger = False):
    '''
    trans_data_fit _summary_

    :param spec_file: _description_
    :type spec_file: _type_
    :param hanger: _description_, defaults to True
    :type hanger: bool, optional
    :return: _description_
    :rtype: _type_
    '''    
    #spec_file: str, filename of relevant data
    #hanger: bool, whether the device is a hanger
    #Loads trans flux data, finds max/min for trans values to extract cavity frequencies at each voltage point.
    full_data = userfuncs.LoadFull(spec_file)

    if 'powers' in full_data[0]:
        xaxis = full_data[0]['powers']
    elif 'voltages' in full_data[0]:
        xaxis = full_data[0]['voltages']
    elif 'fluxes' in full_data[0]:
        xaxis = full_data[0]['fluxes']
    
    trans_freqs_GHz = full_data[0]['full_data']['xaxis']
    trans_mags = full_data[0]['full_data']['phases']
    
    cfreqs = []
    
    for f in range(0,len(xaxis)):
        if hanger:
            fholder = trans_freqs_GHz[np.argmin(trans_mags[f])]
        else:
            fholder = trans_freqs_GHz[np.argmax(trans_mags[f])]
        cfreqs.append(fholder)
    
    return xaxis, cfreqs

################################################################################

def lin_fun(x,m,b):
    '''
    lin_fun _summary_

    :param x: _description_
    :type x: _type_
    :param m: _description_
    :type m: _type_
    :param b: _description_
    :type b: _type_
    :return: _description_
    :rtype: _type_
    '''    
    #x, m, b: float
    #You get it
    return m*x + b

def kerr_fit(data_trans, data_transoe, data_spec, RF_atten, index=False):
    '''
    kerr_fit _summary_

    :param data_trans: _description_
    :type data_trans: _type_
    :param data_transoe: _description_
    :type data_transoe: _type_
    :param data_spec: _description_
    :type data_spec: _type_
    :param RF_atten: _description_
    :type RF_atten: _type_
    :param index: _description_, defaults to False
    :type index: bool, optional
    :return: _description_
    :rtype: _type_
    '''    
    if index:
        data_trans_mags = data_trans['full_data']['mags'][index]
        data_trans_phases = data_trans['full_data']['phases'][index]
        data_transoe_phases = data_transoe['full_data']['phases'][index]
    else:
        data_trans_mags = data_trans['full_data']['mags'][0]
        data_trans_phases = data_trans['full_data']['phases'][0]
        data_transoe_phases = data_transoe['full_data']['phases'][0]
    
    
    zero_point_ind = np.argmax(data_trans_mags)

    data_spec_phase = data_spec['full_data']['phases']
    data_spec_phase_min = np.zeros(len(data_spec_phase))
    for i in range(len(data_spec_phase)):
        data_spec_phase_min[i] = np.min(data_spec_phase[i])

    lin_ax = 10**((data_spec['powers']-RF_atten)/10)
    
    normalize = data_transoe_phases[zero_point_ind] - data_trans_phases[zero_point_ind]
    normalized_phases = data_transoe_phases - normalize
    normalized_phases = np.unwrap(normalized_phases,period=360)
    
    if normalized_phases[zero_point_ind]>180:
        normalized_phases = normalized_phases - 360
    elif normalized_phases[zero_point_ind]<-180:
        normalized_phases = normalized_phases + 360
    
    monitor_tone = np.zeros(len(data_spec_phase))
    for i in range(len(data_spec_phase_min)):
        a = np.argmin(np.abs(normalized_phases - data_spec_phase_min[i]))
        monitor_tone[i] = data_transoe['full_data']['xaxis'][zero_point_ind] - data_transoe['full_data']['xaxis'][a] 
    
    popt, pcov = curve_fit(lin_fun, lin_ax, monitor_tone, method='lm', maxfev=10000)
    # txtstr = 'fit : ' + str(int(popt[0])) + '[KHz/mW]'
    
    
    output_dict = {'power_mW': lin_ax, 'phase_shift' : data_spec_phase_min, 
                   'freq_shift' : monitor_tone,'slope_GHz_mW' : popt[0], 'full_fit':popt}
    return output_dict

def full_flux_vector(flux_start,flux_stop,flux_pts):
    '''
    full_flux_vector _summary_

    :param flux_start: _description_
    :type flux_start: _type_
    :param flux_stop: _description_
    :type flux_stop: _type_
    :param flux_pts: _description_
    :type flux_pts: _type_
    :raises ValueError: _description_
    :return: _description_
    :rtype: _type_
    '''    
    #flux_start: array of length n
    #flux_start: array of length n
    #flux_pts: integer
    #Function for generating a series of flux vectors to feed to a flux scan
    flux_holder = []
    if len(flux_start) != len(flux_stop):
        raise ValueError('requesting invalid array of flux points')
    for i in range(len(flux_start)):
        flux_range = np.linspace(flux_start[i],flux_stop[i],flux_pts)
        flux_holder.append(flux_range)

    flux_holder = tuple(flux_holder)
    full_fluxes = np.stack(flux_holder,axis=1)

    return full_fluxes    

def flux2v_generator(v2f,v_offsets,full_fluxes):
    '''
    flux2v_generator _summary_

    :param v2f: _description_
    :type v2f: _type_
    :param v_offsets: _description_
    :type v_offsets: _type_
    :param full_fluxes: _description_
    :type full_fluxes: _type_
    :return: _description_
    :rtype: _type_
    '''    
    #Function for calculating the corresponding voltage vectors for an 
    #array of flux vectors
    f2v = np.linalg.inv(v2f)
    diags = np.diagonal(v2f)
    phase_offsets = v_offsets * (diags)
    
    full_voltages = np.zeros(full_fluxes.shape)
    
    for i in range(len(full_fluxes)):
        desired_phases = full_fluxes[i] + phase_offsets
        full_voltages[i] = f2v@desired_phases
    return full_voltages




def phase_fun(volts,v2f,v_offsets):
    '''
    phase_fun _summary_

    :param volts: _description_
    :type volts: _type_
    :param v2f: _description_
    :type v2f: _type_
    :param v_offsets: _description_
    :type v_offsets: _type_
    :return: _description_
    :rtype: _type_
    '''

    #volts: (n,) array of voltages
    #v2f: (n,n) array, the volt to flux matrix
    #v_offsets: (n,) array, collection of voltage offsets
    #Transforms SRS voltages into the actual phase response of the qubits
    diags = np.diagonal(v2f) # Diagonal elements of the volt to flux matrix
    phase_offsets = v_offsets * (diags)
    phases = v2f@volts - phase_offsets
    return phases


def phase_finder(volt,v2f,v_offsets,SRS_ind):
    '''
    phase_finder _summary_

    :param volt: _description_
    :type volt: _type_
    :param v2f: _description_
    :type v2f: _type_
    :param v_offsets: _description_
    :type v_offsets: _type_
    :param SRS_ind: _description_
    :type SRS_ind: _type_
    :return: _description_
    :rtype: _type_
    '''    
    #volt: float, voltage point from a 1D SRS sweep you'd like to know the qubit's phase for
    #v2f: (n,n) array, the volt to flux matrix
    #v_offsets: (n,) array, collection of voltage offsets
    #SRS_ind: int, labels the qubit being driven
    #Finds the phase for a qubit when one SRS is at a voltage point.
    diags = np.diagonal(v2f)
    return diags[SRS_ind-1] * (volt - v_offsets[SRS_ind-1])

def volt_finder(phase,v2f,v_offsets,SRS_ind):
    '''
    volt_finder _summary_

    :param phase: _description_
    :type phase: _type_
    :param v2f: _description_
    :type v2f: _type_
    :param v_offsets: _description_
    :type v_offsets: _type_
    :param SRS_ind: _description_
    :type SRS_ind: _type_
    :return: _description_
    :rtype: _type_
    '''    
    #phase: float, qubit phase you'd like to target
    #v2f: (n,n) array, the volt to flux matrix
    #v_offsets: (n,) array, collection of voltage offsets
    #SRS_ind: int, labels the qubit being driven
    #Finds the phase for a qubit when one SRS is at a voltage point.
    diags = np.diagonal(v2f)
    return (1/diags[SRS_ind-1])*phase + v_offsets[SRS_ind-1]

# For qubit frequency calibration script
def calibration_slope(file_path, qubit_num):
    '''
    calibration_slope _summary_

    :param file_path: _description_
    :type file_path: _type_
    :param qubit_num: _description_
    :type qubit_num: _type_
    :return: _description_
    :rtype: _type_
    '''    
    full_data = userfuncs.LoadFull(file_path+'.pkl')
    freq_list = []
    flux_list = []
    flux_num = len(full_data[0]['full_fluxes'])
    for i in range(flux_num):
        result = fit_model(full_data[0]['specdata']['xaxis'], full_data[0]['specdata']['mags'][i], 'lorenz')
        freq_list.append(result['center'])
        flux_list.append(full_data[0]['full_fluxes'][i][qubit_num-1])
    popt, pcov = curve_fit(linear_func, freq_list, flux_list, method='lm')
    slope = popt[0]
    return freq_list, flux_list, slope

def linear_func(x, a, b):
    '''
    linear_func _summary_

    :param x: _description_
    :type x: _type_
    :param a: _description_
    :type a: _type_
    :param b: _description_
    :type b: _type_
    :return: _description_
    :rtype: _type_
    '''    
    return a*x + b

def calibration_flux(file_path, ref_freq_list, slope, qubit_num):
    '''
    calibration_flux _summary_

    :param file_path: _description_
    :type file_path: _type_
    :param ref_freq_list: _description_
    :type ref_freq_list: _type_
    :param slope: _description_
    :type slope: _type_
    :param qubit_num: _description_
    :type qubit_num: _type_
    :return: _description_
    :rtype: _type_
    '''    
    full_data = userfuncs.LoadFull(file_path+'.pkl')
    del_f = []
    del_phi = []
    flux_list = full_data[0]['fluxes']
    flux_pts = len(flux_list)
    for i in range(flux_pts):
        #result = fit_model(full_data[0]['specdata']['xaxis'], full_data[0]['specdata']['mags'][i], 'lorenz')
        #del_f.append(ref_freq_list[i] - result['center'])
        resultarg = np.argmin(full_data[0]['specdata']['mags'][i])
        del_f.append(ref_freq_list[i] - full_data[0]['specdata']['xaxis'][resultarg])
        del_phi.append(slope*(del_f[i]))
    avg_del_phi = sum(del_phi)/flux_pts
    avg_del_f = sum(del_f)/flux_pts
    new_flux_start = full_data[0]['full_fluxes'][0][qubit_num-1]+avg_del_phi
    new_flux_stop = full_data[0]['full_fluxes'][flux_pts-1][qubit_num-1]+avg_del_phi
    print(qubit_num-1)
    cali_flux_start = np.copy(full_data[0]['full_fluxes'][0])
    cali_flux_start[qubit_num-1] = new_flux_start
    cali_flux_stop = np.copy(full_data[0]['full_fluxes'][flux_pts-1])
    cali_flux_stop[qubit_num-1] = new_flux_stop
    return cali_flux_start, cali_flux_stop, avg_del_f, avg_del_phi 

def calibration_plot(transdata, specdata, yaxis, scanname, trans_labels, spec_labels, fig_num = ''):
    if fig_num == '':
        fig = plt.figure(figsize=(13,8))
    else:
        fig = plt.figure(fig_num, figsize=(13,8))
    plt.clf()
    
    ax = plt.subplot(2,2,1)
    general_colormap_subplot(ax,transdata['xaxis'], yaxis, transdata['mags'], trans_labels, 'Trans mag')
    
    ax = plt.subplot(2,2,2)
    general_colormap_subplot(ax,transdata['xaxis'], yaxis, transdata['phases'], trans_labels, 'Trans phase')
    
    ax = plt.subplot(2,2,3)
    general_colormap_subplot(ax,specdata['xaxis'], yaxis, specdata['mags'], spec_labels, 'Spec mag')
    
    ax = plt.subplot(2,2,4)
    general_colormap_subplot(ax,specdata['xaxis'], yaxis, specdata['phases'], spec_labels, 'Spec phase')
    
    plt.suptitle('Filename: {}'.format(scanname))
    
    fig.canvas.draw()
    fig.canvas.flush_events()
    return