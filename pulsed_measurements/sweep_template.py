# -*- coding: utf-8 -*-
"""
Created on Wed Mar  3 13:29:04 2021

@author: Kollarlab
"""

'''
For loop template
'''
import os
import time
import numpy as np
import matplotlib.pyplot as plt
import userfuncs 
from utility.measurement_helpers import remove_IQ_ellipse, extract_data
from utility.plotting_tools import simplescan_plot
   
def base_task(card, xaxis, settings):
    card.ArmAndWait()
    
    I, Q = card.ReadAllData()
    
    Itemp = np.mean(I, 0)
    Qtemp = np.mean(Q, 0)
    
    if settings['remove_IQ_ellipse']:
        axes = settings['ellipse_axes']
        center = settings['ellipse_center']
        phi = settings['ellipse_phi']
        Itemp, Qtemp = remove_IQ_ellipse(Itemp, Qtemp, axes, center, phi)
    
    I_amp, I_time, I_raw, I_raw_time = extract_data(Itemp, xaxis, settings)
    Q_amp, Q_time, Q_raw, Q_raw_time = extract_data(Qtemp, xaxis, settings)
    
    amp_vec = np.sqrt(I_amp**2+Q_amp**2)
    phase_vec = np.arctan2(Q_amp, I_amp)*180/np.pi
    
    raw_amp_vec = np.sqrt(I_raw**2+Q_raw**2)
    raw_phase_vec = np.arctan2(Q_raw, I_raw)*180/np.pi
    
    return amp_vec, phase_vec, raw_amp_vec, raw_phase_vec
    
def sweep_2D(instruments, settings, saveDir, filename, sweep1, sweep2, commandlist, plotlabels):
        
    ##Instruments used
    qubitgen  = instruments['qubitgen']
    cavitygen = instruments['cavitygen']
    card      = instruments['card']
    hdawg     = instruments['AWG']
    LO        = instruments['LO']
    
    xaxis = (np.array(range(card.samples))/card.sampleRate)
    xaxis_us = xaxis*1e6
    
    mag_data   = np.zeros((len(sweep1), len(sweep2)))
    phase_data = np.zeros((len(sweep1), len(sweep2)))
    
    raw_mag_data   = np.zeros((len(sweep1), len(sweep2), card.samples))
    raw_phase_data = np.zeros((len(sweep1), len(sweep2), card.samples))
    
    commands1 = commandlist['outer_loop']
    commands2 = commandlist['inner_loop']
    
    tstart = time.time()
    for sind, val in enumerate(sweep1):
        exec(commands1.format(val))
        for pind, pval in enumerate(sweep2):
            exec(commands2.format(pval))
            amp_vec, phase_vec, raw_mag, raw_phase = base_task(card, settings)
            
            if sind == 0 and pind == 0:
                tstop = time.time()
                singlePointTime = tstop-tstart
                
                estimatedTime = singlePointTime*len(sweep1)*len(sweep2)
                print('    ')
                print('estimated time for this scan : ' + str(np.round(estimatedTime/60, 1)) + ' minutes')
                print('estimated time for this scan : ' + str(np.round(estimatedTime/60/60, 2)) + ' hours')
                print('    ')
                
            mag_data[sind, pind]   = np.mean(amp_vec)
            phase_data[sind, pind] = np.mean(phase_vec)
            raw_mag_data[sind, pind]   = raw_mag
            raw_phase_data[sind, pind] = raw_phase
            
        full_data = {}
        full_data['xaxis'] = sweep2
        full_data['mags'] = mag_data[0:sind+1]
        full_data['phases'] = phase_data[0:sind+1]

        single_data = {}
        single_data['xaxis'] = sweep2
        single_data['mag'] = mag_data[sind]
        single_data['phase'] = phase_data[sind]

        yaxis = sweep1
        labels = plotlabels['final']
        simplescan_plot(full_data, single_data, yaxis, filename, labels, identifier='', fig_num=1) 
        plt.savefig(os.path.join(saveDir, filename+'_fullColorPlot.png'), dpi = 150)
        
        full_time = {}
        full_time['xaxis'] = xaxis_us
        full_time['mags'] = raw_mag_data
        full_time['phases'] = raw_phase_data

        single_time = {}
        single_time['xaxis'] = xaxis_us
        single_time['mag'] = raw_mag
        single_time['phase'] = raw_phase

        time_labels = plotlabels['raw_data']
      
        simplescan_plot(full_time, single_time, sweep1, 'Raw_time_traces', time_labels, identifier='', fig_num=2)
        plt.savefig(os.path.join(saveDir, filename+'_Raw_time_traces.png'), dpi = 150)
        
        userfuncs.SaveFull(saveDir, filename, ['sweep1', 'sweep2', 'full_data', 'full_time', 'single_data', 'single_time', 
                                               'raw_mag_data', 'raw_phase_data'], locals(), expsettings=settings)