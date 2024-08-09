# -*- coding: utf-8 -*-
"""
Created on Wed Nov 18 14:07:57 2020

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
    settings['scanname']    = 'initial_power_scan_q4'
    settings['meas_type']   = 'trans'
    #settings['project_dir'] = r'Z:\Data\HouckQuadTransmon'
    
    #Sweep parameter
    #settings['CAV_Attenuation'] = 30

    settings['start_power']  = -20
    settings['stop_power']   = 10
    settings['power_points'] = 31

    #VNA settings
    settings['channel']  = 1
    settings['avg_time'] = 1
    settings['measurement'] = 'S21'
    settings['start_freq']  = 8.7*1e9  
    settings['stop_freq']   = 8.8*1e9 
    settings['freq_points'] = 1001
    settings['ifBW'] = 1e3
    settings['unwrap_phase'] = False

    return settings

def vna_trans(instruments, settings):
    '''
    vna_trans _summary_

    :param instruments: _description_
    :type instruments: _type_
    :param settings: _description_
    :type settings: _type_
    :return: _description_
    :rtype: _type_
    '''    
    ##Instruments used
    vna = instruments['VNA']

    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings']
    
    vna.reset()  
    
    ##Data saving and naming
    #saveDir = userfuncs.saveDir(settings['project_dir'], settings['meas_type'])
    stamp    = userfuncs.timestamp()
    saveDir  = userfuncs.saveDir(settings)
    filename = exp_settings['scanname'] + '_' + stamp

    CAV_Attenuation = exp_globals['CAV_Attenuation']

    start_power  = exp_settings['start_power'] + CAV_Attenuation
    stop_power   = exp_settings['stop_power'] + CAV_Attenuation
    power_points = exp_settings['power_points']
    powers = np.linspace(start_power, stop_power, power_points)

    mags   = np.zeros((len(powers), exp_settings['freq_points']))
    phases = np.zeros((len(powers), exp_settings['freq_points']))

    tstart = time.time()
    for powerind in range(len(powers)):
        power = powers[powerind]
        print('Power: {}, final power: {}'.format(power-CAV_Attenuation, powers[-1]-CAV_Attenuation))
        exp_settings['RFpower'] = power

        data = vna.trans_meas(exp_settings)

        vna.autoscale()

        mags[powerind]   = data['mag']
        phases[powerind] = data['phase']

        if powerind==0:
            tstop = time.time()
            estimate_time(tstart, tstop, len(powers))
        
        freqs = data['xaxis']   

        full_data = {}
        full_data['xaxis']  = freqs/1e9
        full_data['mags']   = mags[0:powerind+1]
        full_data['phases'] = phases[0:powerind+1]
    
        single_data = data
        single_data['xaxis'] = freqs/1e9
    
        labels = ['Freq (GHz)', 'Power (dBm)']
        yaxis = powers[0:powerind+1]-CAV_Attenuation
        plots.simplescan_plot(full_data, single_data, yaxis, filename, labels, identifier='', fig_num=2)

        plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)
        userfuncs.SaveFull(saveDir, filename, ['full_data', 'single_data', 'powers', 'labels', 'filename'], 
                            locals(), expsettings=settings, instruments=instruments)
        
    t2 = time.time()
    print('Elapsed time: {}'.format(t2-tstart))

    data = {'saveDir': saveDir, 'filename': filename, 'full_data': full_data, 'powers': powers}

    return data