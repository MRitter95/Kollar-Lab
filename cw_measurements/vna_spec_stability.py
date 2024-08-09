# -*- coding: utf-8 -*-
"""
Created on Wed Jul 14 17:37:06 2021

@author: Kollarlab
"""

import time
import os
from utility.measurement_helpers import estimate_time
import numpy as np
import matplotlib.pyplot as plt

import userfuncs
import utility.plotting_tools as plots
from utility.userfits import fit_lorentzian

def get_default_settings():
    '''
    get_default_settings _summary_

    :return: _description_
    :rtype: _type_
    '''    
    fullsettings = {}
    settings = {}
    autoscan_settings = {}
    #Save location
    settings['scanname']    = 'initial_power_scan_q4'
    settings['meas_type']   = 'stability'
    #settings['project_dir'] = r'Z:\Data'

    #Sweep parameters
    #settings['CAV_Attenuation'] = 30
    #settings['Qbit_Attenuation'] = 10

    settings['num_points'] = 10

    #VNA settings
    settings['channel'] = 1
    settings['avg_time'] = 30
    settings['measurement'] = 'S21'
    settings['start_freq'] = 3.5e9
    settings['stop_freq'] = 4.5e9
    settings['freq_points'] = 501
    settings['RFpower'] = -25
    settings['RFport'] = 3
    settings['Mport'] = 2
    settings['CAVport'] = 1
    settings['CAVpower'] = -55
    settings['CAVfreq'] = 8.12555e9
    settings['ifBW'] = 2e2
    settings['mode'] = 'MOV'
    
    settings['unwrap_phase'] = True
    
    autoscan_settings['channel'] = 1
    autoscan_settings['measurement'] = 'S21'
    autoscan_settings['freq_points'] = 501
    autoscan_settings['ifBW'] = settings['ifBW']
    autoscan_settings['avg_time'] = 15
    autoscan_settings['start_freq'] = 7.6e9
    autoscan_settings['stop_freq'] = 7.7e9
    autoscan_settings['RFpower'] = settings['CAVpower']
    autoscan_settings['background_subtract'] = False
    autoscan_settings['unwrap_phase'] = False
    
    fullsettings['spec'] = settings
    fullsettings['autoscan'] = autoscan_settings
    
    return fullsettings

def vna_spec_stability(instruments, settings):
    '''
    vna_spec_stability _summary_

    :param instruments: _description_
    :type instruments: _type_
    :param settings: _description_
    :type settings: _type_
    '''    
    #Instruments used
    vna = instruments['VNA']
    
    vna.reset()

    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings']
    
    spec_set = exp_settings['spec']
    autoscan_set = exp_settings['autoscan']
    
    #Data saving and naming
    #saveDir = userfuncs.saveDir(settings['project_dir'], settings['meas_type'])
    stamp    = userfuncs.timestamp()
    saveDir  = userfuncs.saveDir(settings)
    filename = spec_set['scanname'] + '_' + stamp

    CAV_Attenuation  = exp_globals['CAV_Attenuation']
    Qbit_Attenuation = exp_globals['Qbit_Attenuation']

    spec_set['CAVpower'] = spec_set['CAVpower'] + CAV_Attenuation
    spec_set['RFpower']  = spec_set['RFpower'] + Qbit_Attenuation
    
    autoscan_set['RFpower'] = spec_set['CAVpower']
    
    timing = np.linspace(0, spec_set['num_points']*(spec_set['avg_time']+autoscan_set['avg_time']), spec_set['num_points'])

    mags   = np.zeros((spec_set['num_points'], spec_set['freq_points']))
    phases = np.zeros((spec_set['num_points'], spec_set['freq_points']))
    
    centers = np.zeros(spec_set['num_points'])
    widths  = np.zeros(spec_set['num_points'])
    amps    = np.zeros(spec_set['num_points'])
    
    tstart = time.time()
    for tind in range(len(timing)):
        print('Measurement {} out of {}'.format(tind, spec_set['num_points']))
        
        vna.reset()
        vna.output = 'on'
        
#        print('trans')
#        trans_data   = vna.trans_meas(autoscan_set)
#        trans_freqs  = trans_data['xaxis']
#        trans_mags   = trans_data['mag']
#        trans_phases = trans_data['phase']
#
#        hanger = exp_globals['hanger']
#        if hanger:
#            spec_set['CAVfreq'] = trans_freqs[np.argmin(trans_mags)] 
#        else:
#            spec_set['CAVfreq'] = trans_freqs[np.argmax(trans_mags)]
#
#        print('spec, CAV power: {}, cav freq: {}'.format(spec_set['CAVpower'], spec_set['CAVfreq']))
        
        data = vna.spec_meas(spec_set)

        vna.autoscale()

        mags[tind]   = data['mag']
        phases[tind] = data['phase']

        if tind==0:
            tstop = time.time()
            estimate_time(tstart, tstop, len(timing))

        freqs = data['xaxis']
    
        full_data = {}
        full_data['xaxis'] = freqs/1e9
        full_data['mags'] = mags[0:tind+1]
        full_data['phases'] = phases[0:tind+1]
    
        single_data = data
        single_data['xaxis'] = freqs/1e9
        yaxis = timing[0:tind+1]
        labels = ['Freq (GHz)', 'Time elapsed (s)']
    
        plots.simplescan_plot(full_data, single_data, yaxis, filename, labels, identifier='', fig_num=1)
        plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)
        center, width, amp = fit_lorentzian(freqs, data['mag'], plot=True, fig_num=4)
        
        fig = plt.figure(1)
        fig.canvas.draw()
        fig.canvas.flush_events()
        
        
        centers[tind] = center
        widths[tind]  = width
        amps[tind]    = amp
        
        fig = plt.figure(2, figsize=(13,8))
        plt.clf()
        plt.subplot(311)
        plt.title('Center vs time (GHz)')
        plt.plot(timing[0:tind+1], centers[0:tind+1]/1e9)
        plt.subplot(312)
        plt.title('FWHM vs time (MHz)')
        plt.plot(timing[0:tind+1], widths[0:tind+1]/1e6)
        plt.subplot(313)
        plt.title('Contrast (dB)')
        plt.plot(timing[0:tind+1], amps[0:tind+1])
        
        plt.suptitle('Filename:{}'.format(filename))
        
        fig.canvas.draw()
        fig.canvas.flush_events()
        plt.savefig(os.path.join(saveDir, filename+'fits.png'), dpi = 150)
        
        userfuncs.SaveFull(saveDir, filename, 
                           ['full_data', 'single_data', 'timing', 'labels', 'filename', 
                            'amps', 'centers', 'widths'], 
                           locals(), expsettings=settings, instruments=instruments)
        
    t2 = time.time()
    print('Elapsed time: {}'.format(t2-tstart))

    data = {'saveDir': saveDir, 'filename': filename, 'full_data': full_data, 'timing': timing}

    return data

    