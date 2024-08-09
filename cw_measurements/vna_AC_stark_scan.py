# -*- coding: utf-8 -*-
"""
Created on Thu Dec 17 12:02:58 2020

@author: Kollarlab
"""
import copy 
import time
import os
from utility.measurement_helpers import estimate_time
import numpy as np
import matplotlib.pyplot as plt

import userfuncs
import utility.plotting_tools as plots

def get_default_settings():
    """
    get_default_settings _summary_
    """   
    fullsettings = {}
    settings = {}
    autoscan_settings = {}
    #Save location
    settings['scanname']    = 'AC_Stark_Scan'
    settings['meas_type']   = 'spec_stark_scan'
    #settings['project_dir'] = r'Z:\Data'
    
    
    settings['RFport'] = 3
    settings['Mport'] = 2
    settings['CAVport'] = 1
    
    settings['channel'] = 1
    settings['avg_time'] = 10
    settings['measurement'] = 'S21'
    settings['start_freq'] = 6.5e9
    settings['stop_freq'] = 9.5e9
    settings['freq_points'] = 3001
    settings['CAVpower'] = -55
    settings['RFpower'] = -15
    settings['ifBW'] = .2e3
    
    settings['cav_start_power']  = -60
    settings['cav_stop_power']  = -55
    settings['cav_power_points'] = 3
    
    settings['high_power_spec'] = False
    settings['unwrap_phase'] = True
    
#    settings['CAV_Attenuation'] = 30
#    settings['Qbit_Attenuation'] = 10
    
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

def vna_spec_stark_scan(instruments, settings):
    """
    vna_spec_stark_scan _summary_

    :param instruments: _description_
    :type instruments: _type_
    :param settings: _description_
    :type settings: _type_
    :return: _description_
    :rtype: _type_
    """    
    vna = instruments['VNA']

    vna.reset()

    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings']

    spec_set = exp_settings['spec']
    autoscan_set = exp_settings['autoscan']
    
    background_subtract = autoscan_set['background_subtract']

    ##Data saving and naming
    #saveDir = userfuncs.saveDir(settings['project_dir'], settings['meas_type'])
    stamp    = userfuncs.timestamp()
    saveDir  = userfuncs.saveDir(settings)
    filename = spec_set['scanname'] + '_' + stamp

    CAV_Attenuation  = exp_globals['CAV_Attenuation']
    Qbit_Attenuation = exp_globals['Qbit_Attenuation']
    
    
    # spec_set['CAVpower'] = spec_set['CAVpower'] + CAV_Attenuation
    spec_set['RFpower']  = spec_set['RFpower']  + Qbit_Attenuation
    
    if not spec_set['high_power_spec']:
        print('Using CAVpower from general settings, ignoring autoscan power')
        autoscan_set['RFpower'] = spec_set['CAVpower']
    else:
        autoscan_set['RFpower'] = autoscan_set['RFpower'] + CAV_Attenuation
    
    #set cavity power sweep
    start_power  = spec_set['cav_start_power'] + CAV_Attenuation
    stop_power   = spec_set['cav_stop_power'] + CAV_Attenuation
    power_points = spec_set['cav_power_points']
    
    powers = np.linspace(start_power,stop_power,power_points)
    
    trans_mags   = np.zeros((power_points, autoscan_set['freq_points']))
    trans_phases = np.zeros((power_points, autoscan_set['freq_points']))
    
    mags   = np.zeros((power_points, spec_set['freq_points']))
    phases = np.zeros((power_points, spec_set['freq_points']))
    
    
    tstart = time.time()
    
    identifier = 'Spec Power : ' + str(spec_set['RFpower'] - Qbit_Attenuation) + ' dB'
    
    if background_subtract:
        vna.reset()  
        print('Collecting background ripple, turning cavity power to 0 dBm (on vna)')
        back_settings = copy.deepcopy(autoscan_set)
        back_settings['RFpower'] = 0
        back_data = vna.trans_meas(back_settings)
        
    for pind in range(power_points):
        CAV_power = powers[pind]
        print('Start Power: {}, Stop Power: {}'.format(CAV_power-CAV_Attenuation, powers[-1]-CAV_Attenuation))
        autoscan_set['RFpower'] = powers[pind]
        
        time.sleep(0.1)
        
        vna.reset()  
        vna.output = 'on'
        
        print('trans')
        trans_data  = vna.trans_meas(autoscan_set)
        trans_freqs = trans_data['xaxis']
        trans_mags[pind]   = trans_data['mag']
        trans_phases[pind] = trans_data['phase']
        
        if background_subtract:
            trans_mags[pind] = trans_mags[pind] - back_data['mag']
        else:
            trans_mags[pind] = trans_mags[pind]

        hanger = exp_globals['hanger']
        if hanger:
            spec_set['CAVfreq'] = trans_freqs[np.argmin(trans_mags[pind])] 
        else:
            spec_set['CAVfreq'] = trans_freqs[np.argmax(trans_mags[pind])]
        
        spec_set['CAVpower'] = powers[pind]
        
        print('spec, CAV power: {}, cav freq: {}'.format(spec_set['CAVpower']-CAV_Attenuation, spec_set['CAVfreq']))

        data = vna.spec_meas(spec_set)
        
        vna.autoscale()
        
        mags[pind]   = data['mag']
        phases[pind] = data['phase']

        freqs = data['xaxis']  
        
        if pind==0:
            tstop=time.time()
            estimate_time(tstart, tstop, len(powers))
            
        transdata = {}
        transdata['xaxis'] = trans_freqs/1e9
        transdata['mags'] = trans_mags[0:pind+1,:]
        transdata['phases'] = trans_phases[0:pind+1,:]
        
        specdata = {}
        specdata['xaxis'] = freqs/1e9
        specdata['mags'] = mags[0:pind+1,:]
        specdata['phases'] = phases[0:pind+1,:]
        
        singledata = {}
        singledata['xaxis'] = freqs/1e9
        singledata['mag'] = data['mag'] 
        singledata['phase'] = data['phase']
        
        trans_labels = ['Freq (GHz)','Powers (dBm)']
        spec_labels  = ['Freq (GHz)','Powers (dBm)']
        
        #modify the spec data to subtract the offset in amp and phase
        #and then plot the modified version
        specplotdata = {}
        specplotdata['xaxis']  = specdata['xaxis']
        specplotdata['mags']   = specdata['mags']
        specplotdata['phases'] = specdata['phases']
        
        mat = np.copy(specplotdata['mags'])
        for ind in range(0, mat.shape[0]):
            mat[ind,:]  = mat[ind,:] - np.mean(mat[ind,:])
        specplotdata['mags'] = mat
        
        mat = np.copy(specplotdata['phases'])
        for ind in range(0, mat.shape[0]):
            mat[ind,:]  = mat[ind,:] - np.mean(mat[ind,:])
        specplotdata['phases'] = mat
        
        plots.autoscan_plot(transdata, specplotdata, singledata, powers[0:pind+1]-CAV_Attenuation, filename, trans_labels, spec_labels, identifier, fig_num = 1)
            
        userfuncs.SaveFull(saveDir, filename, ['transdata', 'specdata', 'singledata', 'powers', 
                                       'filename', 'trans_labels', 'spec_labels'], 
                                       locals(), expsettings=settings, instruments=instruments)
        plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)
            
    
    t2 = time.time()
    print('Elapsed time: {}'.format(t2-tstart))
    
    data = {'saveDir': saveDir, 'filename': filename, 'transdata':transdata, 'specdata':specdata, 'powers':powers}

    return data

    