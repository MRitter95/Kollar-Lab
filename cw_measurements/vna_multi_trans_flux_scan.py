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
    '''
    settings = {}
    
    #Save location
    settings['scanname']    = 'flux_Scan'
    settings['meas_type']   = 'multi_trans_flux_scan'
    #settings['project_dir'] = r'Z:\Data'
    
    #Sweep parameter
#    settings['CAV_Attenuation'] = 30
    settings['flux_start'] = np.array([0,0,0])
    settings['flux_stop']  = np.array([0,0,0])
    settings['flux_pts']   = 11
    settings['qubit_num'] = False

    settings['start_power'] = -50
    settings['stop_power'] = -48
    settings['power_points'] = 1
    
    settings['avg_times'] = np.array([0.8])
    
    #VNA settings
    settings['channel']  = 1
    settings['avg_time'] = 1
    settings['measurement'] = 'S21'
    settings['start_freq']  = 7.576e9-40e6 
    settings['stop_freq']   = 7.576e9+40e6 
    settings['freq_points'] = 501
    settings['ifBW'] = 4e3
    settings['unwrap_phase'] = False

    return settings

def multi_trans_flux_scan(instruments, settings):
    '''
    multi_trans_flux_scan _summary_

    :param instruments: _description_
    :type instruments: _type_
    :param settings: _description_
    :type settings: _type_
    '''    
    ##Instruments used
    vna = instruments['VNA']
    SRS_list = instruments['DCsupplies']

    true_instruments = instruments.copy()
    del true_instruments['DCsupplies']

    for sind in range(len(SRS_list)):
        true_instruments['DCsupply'+str(sind+1)] = SRS_list[sind]

#    vna.reset() #####!!! warning put me back
    print('WARNING" Auto reset has been overridden')

    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings']

    ##Data saving and naming
    #saveDir = userfuncs.saveDir(settings['project_dir'], settings['meas_type'])
    stamp     = userfuncs.timestamp()
    saveDir   = userfuncs.saveDir(settings)
    meas_type = exp_settings['meas_type']
    filename_template = exp_settings['scanname'] + '_power{}dBm_' + stamp

    CAV_Attenuation = exp_globals['CAV_Attenuation']
    
    #Make array of fluxes



    flux_start = exp_settings['flux_start']
    flux_stop  = exp_settings['flux_stop']
    flux_pts   = exp_settings['flux_pts']
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

   


    #full_voltages = np.round(exp_settings['voltages'],5)

    qubit_num = exp_settings['qubit_num']


    if qubit_num:
        fluxes = np.transpose(full_fluxes)[qubit_num-1]
    else:
        fluxes = np.linspace(1,len(full_voltages),len(full_voltages))

    if fluxes[0] == fluxes[-1]:
        print('')
        print('Warning! Selected qubit is not being swept, reverting to general numbering system')
        print('')
        exp_settings['qubit_num'] = False
        fluxes = np.linspace(1,len(full_voltages),len(full_voltages))


    max_voltage = 10
    if np.amax(np.abs(full_voltages)) > max_voltage:
        raise ValueError('max voltage too large!')
    else:
        exp_settings['voltages'] = full_voltages
    
    if len(full_voltages[0]) != len(SRS_list):
        raise ValueError('different number of DC supplies and voltages are specified')

    #optional power sweep
    start_power  = exp_settings['start_power'] + CAV_Attenuation
    stop_power   = exp_settings['stop_power'] + CAV_Attenuation
    power_points = exp_settings['power_points']
    powers = np.linspace(start_power, stop_power, power_points)
    
    if len(exp_settings['avg_times']) != len(powers):
        raise ValueError('incorrect number of averaging times specified')
    
    mags   = np.zeros((len(full_voltages), exp_settings['freq_points']))
    phases = np.zeros((len(full_voltages), exp_settings['freq_points']))
    
    for i in range(len(SRS_list)):
        if SRS_list[i].Output == 'Off':
            SRS_list[i].voltage_ramp(0)
            SRS_list[i].Output = 'On'
    
    tstart = time.time()
    for pind in range(len(powers)):
        power = powers[pind]
        exp_settings['RFpower']  = power
        exp_settings['avg_time'] = exp_settings['avg_times'][pind]
        identifier = 'Cav Power : ' + str(exp_settings['RFpower'] - CAV_Attenuation) + ' dB'
        
        stamp    = userfuncs.timestamp()
        filename = filename_template.format(power - CAV_Attenuation)
        #filename = 'transFluxScan_' + settings['scanname'] + '_Power'+str(exp_settings['RFpower'] - CAV_Attenuation) + '_' + stamp
        
        print('Power: {}'.format(exp_settings['RFpower'] - CAV_Attenuation))
        
        for vind in range(len(full_voltages)):
            for sind in range(len(SRS_list)):
                SRS_list[sind].voltage_ramp(full_voltages[vind][sind])
                time.sleep(0.1)
                if vind == 0:
                    print('Voltage {}: initial {}, final {}'.format(str(sind+1),full_voltages[vind][sind],full_voltages[-1][sind]))
            print('')
            print('Progress: ' + str(vind+1) + '/' + str(len(full_voltages)))                            
            print('Current Flux {}, Ending Flux {}'.format(str(np.round(fluxes[vind],6)),str(fluxes[-1])))
            print('')

            time.sleep(0.1)
            
            data = vna.trans_meas(exp_settings)
            
            vna.autoscale()
            
            mags[vind]   = data['mag']
            phases[vind] = data['phase']

            freqs = data['xaxis']  
            
            if vind==0 and pind == 0:
                tstop=time.time()
                mean_avg_time = np.mean(exp_settings['avg_times'])/exp_settings['avg_times'][0]
                estimate_time(tstart, tstop, len(powers)*len(full_voltages)*mean_avg_time)
                
            freqs = data['xaxis']   

            full_data = {}
            full_data['xaxis']  = freqs/1e9
            full_data['mags']   = mags[0:vind+1]
            full_data['phases'] = phases[0:vind+1]
    
            single_data = data
            single_data['xaxis'] = freqs/1e9
    
            labels = ['Freq (GHz)', 'Flux']
            yaxis  = fluxes[0:vind+1]
            plots.simplescan_plot(full_data, single_data, yaxis, filename, labels, identifier=identifier, fig_num=2)
            
            userfuncs.SaveFull(saveDir, filename, ['full_data', 'single_data', 'powers', 'fluxes', 'filename',
                                                   'full_fluxes', 'full_voltages', 'labels','meas_type'], 
                                locals(), expsettings=settings, instruments=true_instruments)
            plt.savefig(os.path.join(saveDir, filename+'.png'), dpi = 150)
            
    t2 = time.time()
    print('Elapsed time: {}'.format(t2-tstart))


    data = {'saveDir': saveDir, 'filename': filename, 'full_data': full_data, 'powers': powers, 'fluxes':fluxes}

    return data
