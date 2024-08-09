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
    '''
    get_default_settings _summary_
    '''    
    fullsettings = {}
    settings = {}
    autoscan_settings = {}
    #Save location
    settings['scanname']    = 'flux_Scan'
    settings['meas_type']   = 'multi_spec_flux_scan'
    
    settings['flux_start'] = np.array([0,0,0])
    settings['flux_stop']  = np.array([0,0,0])
    settings['flux_pts']   = 11
    settings['qubit_num'] = False
    
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

def multi_spec_flux_scan(instruments, settings):
    '''
    multi_spec_flux_scan _summary_

    :param instruments: _description_
    :type instruments: _type_
    :param settings: _description_
    :type settings: _type_
    :raises ValueError: _description_
    :raises ValueError: _description_
    :raises ValueError: _description_
    :return: _description_
    :rtype: _type_
    '''    
    ##Instruments used
    vna = instruments['VNA']
    SRS_list = instruments['DCsupplies']
    
    true_instruments = instruments.copy()
    del true_instruments['DCsupplies']
    
    for sind in range(len(SRS_list)):
        true_instruments['DCsupply'+str(sind+1)] = SRS_list[sind]
    
    vna.reset()

    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings']

    spec_set = exp_settings['spec']
    autoscan_set = exp_settings['autoscan']
    
    background_subtract = autoscan_set['background_subtract']

    ##Data saving and naming
    #saveDir = userfuncs.saveDir(settings['project_dir'], settings['meas_type'])
    stamp     = userfuncs.timestamp()
    saveDir   = userfuncs.saveDir(settings)
    filename  = spec_set['scanname'] + '_' + stamp
    meas_type = spec_set['meas_type']

    CAV_Attenuation  = exp_globals['CAV_Attenuation']
    Qbit_Attenuation = exp_globals['Qbit_Attenuation']
    
    
    spec_set['CAVpower'] = spec_set['CAVpower'] + CAV_Attenuation
    spec_set['RFpower']  = spec_set['RFpower']  + Qbit_Attenuation
    if not spec_set['high_power_spec']:
        print('Using CAVpower from general settings, ignoring autoscan power')
        autoscan_set['RFpower'] = spec_set['CAVpower']
    else:
        autoscan_set['RFpower'] = autoscan_set['RFpower'] + CAV_Attenuation
    
    #set voltage sweep
    flux_start = spec_set['flux_start']
    flux_stop  = spec_set['flux_stop']
    flux_pts   = spec_set['flux_pts']
    flux_holder = []

    if len(flux_start) != len(flux_stop) or len(flux_start) != len(SRS_list):
        raise ValueError('requesting invalid array of flux points')


    for iind in range(len(SRS_list)):
        flux_range = np.linspace(flux_start[iind],flux_stop[iind],flux_pts)
        flux_holder.append(flux_range)
    
    flux_holder = tuple(flux_holder)

    full_fluxes = np.stack(flux_holder,axis=1)


    #Calculate corresponding voltage array
    v2f = exp_globals['v2f']
    f2v = np.linalg.inv(v2f)
    v_offsets = exp_globals['v_offsets']

    diags = np.diagonal(v2f) # Diagonal elements of the volt to flux matrix
    phase_offsets = v_offsets * (diags)

    full_voltages = np.zeros(full_fluxes.shape)

    for i in range(flux_pts):
        desired_phases = full_fluxes[i] + phase_offsets
        full_voltages[i] = f2v@desired_phases



    qubit_num = spec_set['qubit_num']
    
    if qubit_num:
        fluxes = np.transpose(full_fluxes)[qubit_num-1]
    else:
        fluxes = np.linspace(1,len(full_voltages),len(full_voltages))

    if fluxes[0] == fluxes[-1]:
        print('')
        print('Warning! Selected qubit is not being swept, reverting to general numbering system')
        print('')
        spec_set['qubit_num'] = False
        fluxes = np.linspace(1,len(full_voltages),len(full_voltages))    

    max_voltage = 10
    if np.amax(np.abs(full_voltages)) > max_voltage:
        raise ValueError('max voltage too large!')
    else:
        settings['voltages'] = full_voltages
    
    if len(full_voltages[0]) != len(SRS_list):
        raise ValueError('different number of DC supplies and voltages are specified')
    
    trans_mags   = np.zeros((len(full_voltages), autoscan_set['freq_points']))
    trans_phases = np.zeros((len(full_voltages), autoscan_set['freq_points']))
    
    mags   = np.zeros((len(full_voltages), spec_set['freq_points']))
    phases = np.zeros((len(full_voltages), spec_set['freq_points']))
    
    
    
    for i in range(len(SRS_list)):
        if SRS_list[i].Output == 'Off':
            SRS_list[i].voltage_ramp(0)
            SRS_list[i].Output = 'On'
    
    tstart = time.time()
    
    identifier = 'Cav Power : ' + str(spec_set['CAVpower'] - CAV_Attenuation) + ' dB'
    
    if background_subtract:
        vna.reset()
        print('Collecting background ripple, turning cavity power to 0 dBm (on vna)')
        back_settings = copy.deepcopy(autoscan_set)
        back_settings['RFpower'] = 0
        back_data = vna.trans_meas(back_settings)
        
    for vind in range(len(full_voltages)):
        for sind in range(len(SRS_list)):
            SRS_list[sind].voltage_ramp(full_voltages[vind][sind])
            time.sleep(0.1)
            if vind==0:
                print('Voltage {}: {}, final voltage {}: {}'.format(str(sind+1),full_voltages[vind][sind],str(sind+1),full_voltages[-1][sind]))
        print('')
        print('Progress: ' + str(vind+1) + '/' + str(len(full_voltages)))                            
        print('Current Flux {}, Ending Flux {}'.format(str(np.round(fluxes[vind],6)),str(fluxes[-1])))
        print('')

        
        vna.reset()
        vna.output = 'on'
        
        print('trans')
        trans_data  = vna.trans_meas(autoscan_set)
        trans_freqs = trans_data['xaxis']
        trans_mags[vind]   = trans_data['mag']
        trans_phases[vind] = trans_data['phase']
        
        if background_subtract:
            trans_mags[vind] = trans_mags[vind] - back_data['mag']
        else:
            trans_mags[vind] = trans_mags[vind]

        hanger = exp_globals['hanger']
        if hanger:
            spec_set['CAVfreq'] = trans_freqs[np.argmin(trans_mags[vind])] 
        else:
            spec_set['CAVfreq'] = trans_freqs[np.argmax(trans_mags[vind])]

        print('spec, CAV power: {}, cav freq: {}'.format(spec_set['CAVpower'], spec_set['CAVfreq']))

        data = vna.spec_meas(spec_set)
        
        vna.autoscale()
        
        mags[vind]   = data['mag']
        phases[vind] = data['phase']

        freqs = data['xaxis']  
        
        if vind==0:
            tstop=time.time()
            estimate_time(tstart, tstop, len(full_voltages))
            
        transdata = {}
        transdata['xaxis'] = trans_freqs
        transdata['mags'] = trans_mags[0:vind+1,:]
        transdata['phases'] = trans_phases[0:vind+1,:]
        
        specdata = {}
        specdata['xaxis'] = freqs
        specdata['mags'] = mags[0:vind+1,:]
        specdata['phases'] = phases[0:vind+1,:]
        
        singledata = {}
        singledata['xaxis'] = freqs
        singledata['mag'] = data['mag'] 
        singledata['phase'] = data['phase']
        
        trans_labels = ['Freq (GHz)','Flux']
        spec_labels  = ['Freq (GHz)','Flux']
        
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
        
        plots.autoscan_plot(transdata, specplotdata, singledata, fluxes[0:vind+1], filename, trans_labels, spec_labels, identifier, fig_num = 1)

        userfuncs.SaveFull(saveDir, filename, ['transdata', 'specdata', 'singledata', 'full_voltages', 'full_fluxes',
                                       'fluxes', 'filename', 'trans_labels', 'spec_labels','meas_type'], 
                                       locals(), expsettings=settings, instruments=true_instruments)
        plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)
            
    
    t2 = time.time()
    print('Elapsed time: {}'.format(t2-tstart))

    data = {'saveDir': saveDir, 'filename': filename, 'transdata':transdata, 'specdata':specdata,'fluxes':fluxes}

    return data