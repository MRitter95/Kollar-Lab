# -*- coding: utf-8 -*-
"""
Created on Sun Nov  8 18:31:45 2020

@author: Kollarlab
"""
import time
import copy
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
    fullsettings = {}
    settings = {}
    autoscan_settings = {}
    
    #Save location
    settings['scanname']    = 'scanname'
    settings['meas_type']   = 'Autler_Townes_Autoscan'

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
    
    
    fullsettings['AT'] = settings
    fullsettings['autoscan'] = autoscan_settings
    fullsettings['meas_type'] = 'Autler_Townes_Autoscan' #this needs to be at this level for SaveDir to find it
    
    return fullsettings


def vna_autler_townes_autoscan(instruments, settings):
    '''
    vna_autler_townes_autoscan _summary_

    :param instruments: _description_
    :type instruments: _type_
    :param settings: _description_
    :type settings: _type_
    '''    
    #Instruments used
    vna = instruments['VNA']
    SRS = instruments['SRS']
    autlergen = instruments['RFsource']

    vna.reset()
#    vna.output = 'on'

    autlergen.IQ.Mod = 'Off'

    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings'] 
    
    AT_set = exp_settings['AT']
    autoscan_set = exp_settings['autoscan']
#    exp_settings['meas_type'] = AT_set['meas_type'] #this is iportant for getting the save directory working
    
    background_subtract = autoscan_set['background_subtract']

    #Data saving and naming
    #saveDir = userfuncs.saveDir(settings['project_dir'], settings['meas_type'])
    stamp    = userfuncs.timestamp()
    saveDir  = userfuncs.saveDir(settings)
    filename = AT_set['scanname'] + '_' + stamp

    CAV_Attenuation    = exp_globals['CAV_Attenuation']
    Qbit_Attenuation   = exp_globals['Qbit_Attenuation']
    Autler_Attenuation = exp_globals['Autler_Attenuation']

    AT_set['CAVpower']     = AT_set['CAVpower']     + CAV_Attenuation
    AT_set['RFpower']      = AT_set['RFpower']      + Qbit_Attenuation
    AT_set['autler_power'] = AT_set['autler_power'] + Autler_Attenuation
    
    autlergen.power = AT_set['autler_power']#########Q 
    autlergen.output = 'On'
    SRS.output = 'On'
    SRS.voltage_ramp(AT_set['ext_flux'])

    start_autler_freq = AT_set['start_autler_freq']
    stop_autler_freq  = AT_set['stop_autler_freq']
    autler_points     = AT_set['autler_points']
    autler_freqs      = np.round(np.linspace(start_autler_freq, stop_autler_freq, autler_points),-3)

    findices = np.array(list(range(len(autler_freqs))))
    if AT_set['reverse']:
        findices = np.flipud(findices)
    
    if AT_set['random']:
        np.random.shuffle(findices)
        
    
    trans_mags   = np.zeros((autler_points, autoscan_set['freq_points']))
    trans_phases = np.zeros((autler_points, autoscan_set['freq_points']))  
    
    mags   = np.zeros((len(autler_freqs), AT_set['freq_points']))
    phases = np.zeros((len(autler_freqs), AT_set['freq_points']))

    tstart = time.time()
    
    identifier = 'Cav Power : ' + str(AT_set['CAVpower'] - CAV_Attenuation) + ' dB'
    
    if background_subtract:
        vna.reset()
        print('Collecting background ripple, turning cavity power to 0 dBm (on vna)')
        back_settings = copy.deepcopy(autoscan_set)
        back_settings['RFpower'] = 0
        back_data = vna.trans_meas(back_settings)
    
    for freqind in findices:
        autler_freq = autler_freqs[freqind]
        print('Freq: {}, final freq: {}'.format(autler_freq, autler_freqs[-1]))
        
        autlergen.freq = autler_freq
        vna.reset()
        vna.output = 'on'
        
        autlergen.output = 'Off'
        
        print('trans')
        trans_data  = vna.trans_meas(autoscan_set)
        trans_freqs = trans_data['xaxis']
        trans_mags[freqind]   = trans_data['mag']
        trans_phases[freqind] = trans_data['phase']
        
        if background_subtract:
            trans_mags[freqind] = trans_mags[freqind] - back_data['mag']
        else:
            trans_mags[freqind] = trans_mags[freqind]

        hanger = exp_globals['hanger']
        if hanger:
            AT_set['CAVfreq'] = trans_freqs[np.argmin(trans_mags[freqind])] 
        else:
            AT_set['CAVfreq'] = trans_freqs[np.argmax(trans_mags[freqind])]

        print('AT, CAV power: {}, cav freq: {}'.format(AT_set['CAVpower'], AT_set['CAVfreq']))

        autlergen.output = 'On'
        data = vna.spec_meas(AT_set)

        vna.autoscale()

        mags[freqind]   = data['mag']
        phases[freqind] = data['phase']

        if freqind==0:
            tstop = time.time()
            estimate_time(tstart, tstop, len(autler_freqs))
        
        transdata = {}
        transdata['xaxis'] = trans_freqs/1e9
        transdata['mags'] = trans_mags[0:freqind+1,:]
        transdata['phases'] = trans_phases[0:freqind+1,:]

        freqs  = data['xaxis']
        labels = ['Freq (GHz)', 'Autler freq (GHz)']
        trans_labels = ['Freq (GHz)','Voltage (V)']
        full_data   = {}
        single_data = {}
        if not AT_set['random']:
            if AT_set['reverse']:
                full_data = {}
                full_data['xaxis']  = freqs/1e9
                full_data['mags']   = mags[freqind:]
                full_data['phases'] = phases[freqind:]
            
                single_data = data
                yaxis = autler_freqs[freqind:]
            else:
                full_data = {}
                full_data['xaxis']  = freqs/1e9
                full_data['mags']   = mags[0:freqind+1]
                full_data['phases'] = phases[0:freqind+1]
            
                single_data = data
                yaxis = autler_freqs[0:freqind+1]/1e9
            
        
            plots.autoscan_plot(transdata, full_data, single_data, freqs[0:freqind+1], filename, trans_labels, labels, identifier, fig_num = 1)
            # plots.simplescan_plot(full_data, single_data, yaxis, filename, labels, identifier='', fig_num=1)
            
        userfuncs.SaveFull(saveDir, filename, ['full_data', 'single_data', 'autler_freqs', 'labels', 'filename'], 
                            locals(), expsettings=settings, instruments=instruments)
        plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)
    t2 = time.time()
    print('Elapsed time: {}'.format(t2-tstart))
    if AT_set['random']: 
        full_data = {}
        full_data['xaxis']  = freqs/1e9
        full_data['mags']   = mags
        full_data['phases'] = phases
    
        single_data = data
        yaxis = autler_freqs/1e9
        plots.autoscan_plot(transdata, full_data, single_data, freqs[0:freqind+1], filename, trans_labels, labels, identifier, fig_num = 1)
        # plots.simplescan_plot(full_data, single_data, yaxis, filename, labels, identifier='', fig_num=1)
        plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)

    
    data = {'saveDir': saveDir, 'filename': filename, 'fulldata':full_data, 'autler_freqs':autler_freqs}

    return data
