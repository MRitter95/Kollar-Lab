# -*- coding: utf-8 -*-
"""
Created on Sun Nov  8 18:31:45 2020

@author: Kollarlab
"""
import time
import os
from utility.measurement_helpers import estimate_time
import numpy as np
import matplotlib.pyplot as plt

import userfuncs
import utility.plotting_tools as plots

def get_default_settings():
    '''
    get_default_settings _summary_

    :return: _description_
    :rtype: _type_
    '''    
    settings = {}
    
    #Save location
    settings['scanname']    = 'scanname'
    settings['meas_type']   = 'Autler_Townes'

    settings['ext_flux'] = 0
    settings['autler_power'] = -20
    settings['start_autler_freq']  = 3.5e9
    settings['stop_autler_freq']   = 4.5e9
    settings['autler_points'] = 31

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
    settings['ifBW'] = 1e3
    settings['unwrap_phase'] = True

    return settings

def vna_autler_townes(instruments, settings):
    '''
    vna_autler_townes _summary_

    :param instruments: _description_
    :type instruments: _type_
    :param settings: _description_
    :type settings: _type_
    :return: _description_
    :rtype: _type_
    '''    
    #Instruments used
    vna = instruments['VNA']
    SRS = instruments['SRS']
    autlergen = instruments['RFsource']

    vna.reset()

    autlergen.IQ.Mod = 'Off'

    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings'] 

    #Data saving and naming
    #saveDir = userfuncs.saveDir(settings['project_dir'], settings['meas_type'])
    stamp    = userfuncs.timestamp()
    saveDir  = userfuncs.saveDir(settings)
    filename = exp_settings['scanname'] + '_' + stamp

    CAV_Attenuation    = exp_globals['CAV_Attenuation']
    Qbit_Attenuation   = exp_globals['Qbit_Attenuation']
    Autler_Attenuation = exp_globals['Autler_Attenuation']

    exp_settings['CAVpower']     = exp_settings['CAVpower']     + CAV_Attenuation
    exp_settings['RFpower']      = exp_settings['RFpower']      + Qbit_Attenuation
    exp_settings['autler_power'] = exp_settings['autler_power'] + Autler_Attenuation
    
    autlergen.power = exp_settings['autler_power']#########Q 
    autlergen.output = 'On'
    SRS.output = 'On'
    SRS.voltage_ramp(exp_settings['ext_flux'])

    start_autler_freq = exp_settings['start_autler_freq']
    stop_autler_freq  = exp_settings['stop_autler_freq']
    autler_points     = exp_settings['autler_points']
    autler_freqs      = np.round(np.linspace(start_autler_freq, stop_autler_freq, autler_points),-3)

    findices = np.array(list(range(len(autler_freqs))))
    if exp_settings['reverse']:
        findices = np.flipud(findices)
    
    if exp_settings['random']:
        np.random.shuffle(findices)
        
    mags   = np.zeros((len(autler_freqs), exp_settings['freq_points']))
    phases = np.zeros((len(autler_freqs), exp_settings['freq_points']))

    tstart = time.time()
    for freqind in findices:
        autler_freq = autler_freqs[freqind]
        print('Freq: {}, final freq: {}'.format(autler_freq, autler_freqs[-1]))
        
        autlergen.freq = autler_freq

        data = vna.spec_meas(exp_settings)

        vna.autoscale()

        mags[freqind]   = data['mag']
        phases[freqind] = data['phase']

        if freqind==0:
            tstop = time.time()
            estimate_time(tstart, tstop, len(autler_freqs))

        freqs  = data['xaxis']
        labels = ['Freq (GHz)', 'Autler freq (GHz)']
        full_data   = {}
        single_data = {}
        if not exp_settings['random']:
            if exp_settings['reverse']:
                full_data = {}
                full_data['xaxis']  = freqs/1e9
                full_data['mags']   = mags[freqind:]
                full_data['phases'] = phases[freqind:]
            
                single_data = data
                yaxis = autler_freqs[freqind:]/1e9
            else:
                full_data = {}
                full_data['xaxis']  = freqs/1e9
                full_data['mags']   = mags[0:freqind+1]
                full_data['phases'] = phases[0:freqind+1]
            
                single_data = data
                yaxis = autler_freqs[0:freqind+1]/1e9
            
        
            plots.simplescan_plot(full_data, single_data, yaxis, filename, labels, identifier='', fig_num=1)
            
        userfuncs.SaveFull(saveDir, filename, ['full_data', 'single_data', 'autler_freqs', 'labels', 'filename'], 
                            locals(), expsettings=settings, instruments=instruments)
        plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)
    t2 = time.time()
    print('Elapsed time: {}'.format(t2-tstart))
    if exp_settings['random']: 
        full_data = {}
        full_data['xaxis']  = freqs/1e9
        full_data['mags']   = mags
        full_data['phases'] = phases
    
        single_data = data
        yaxis = autler_freqs/1e9
        plots.simplescan_plot(full_data, single_data, yaxis, filename, labels, identifier='', fig_num=1)
        plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)

    data = {'saveDir': saveDir, 'filename': filename, 'fulldata':full_data, 'autler_freqs':autler_freqs}

    return data
