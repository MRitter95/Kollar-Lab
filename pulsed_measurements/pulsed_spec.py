import os
import time
import numpy as np
import matplotlib.pyplot as plt

import userfuncs
from utility.plotting_tools import simplescan_plot
from utility.measurement_helpers import configure_card, configure_hdawg, estimate_time, read_and_process

def get_default_settings():
    settings = {}
    
    settings['scanname'] = 'scanname'
    settings['meas_type'] = 'pulsed_spec'
    
    #Cavity parameters
    settings['CAV_Power']        = -60
    settings['CAV_freq']        = 7e9
    
    #Qubit parameters
    settings['start_freq']      = 4.15*1e9  
    settings['stop_freq']       = 4.25*1e9 
    settings['freq_points']     = 50

    settings['start_power']     = -30
    settings['stop_power']      = -20
    settings['power_points']    = 5

    #Card settings
    settings['segments']         = 1
    settings['reads']            = 1
    settings['averages']         = 5e3
    
    #Measurement settings
    settings['Quasi_CW']    = False
    
    return settings

def pulsed_spec(instruments, settings):
    
    ##Instruments used
    qubitgen  = instruments['qubitgen']
    cavitygen = instruments['cavitygen']
    card      = instruments['card']
    hdawg     = instruments['AWG']
    LO        = instruments['LO']
    
    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings']

    ##Data saving and naming
    stamp    = userfuncs.timestamp()
    saveDir  = userfuncs.saveDir(settings)
    filename = exp_settings['scanname'] + '_' + stamp
    
    ##Cavity settings
    CAV_Attenuation = exp_globals['CAV_Attenuation']
    CAV_power = exp_settings['CAV_Power'] + CAV_Attenuation
    CAV_freq  = exp_settings['CAV_freq']
    
    ##Qubit settings
    start_freq  = exp_settings['start_freq']
    stop_freq   = exp_settings['stop_freq']
    freq_points = exp_settings['freq_points']
    freqs  = np.round(np.linspace(start_freq,stop_freq,freq_points),-3)
    
    Qbit_Attenuation = exp_globals['Qbit_Attenuation']
    start_power  = exp_settings['start_power'] + Qbit_Attenuation
    stop_power   = exp_settings['stop_power']  + Qbit_Attenuation
    power_points = exp_settings['power_points']
    powers = np.round(np.linspace(start_power,stop_power,power_points),2)
    
    ## Generator settings
    cavitygen.Freq   = CAV_freq
    cavitygen.Power  = CAV_power
    cavitygen.IQ.Mod = 'On'

    #setting qubit generator to some safe starting point before we turn it on
    qubitgen.Freq   = 4e9
    qubitgen.Power  = -20
    
    if exp_settings['Quasi_CW']:
        qubitgen.IQ.Mod = 'Off'
    else:
        qubitgen.IQ.Mod = 'On'

    cavitygen.Output = 'On'
    qubitgen.Output  = 'On'
    
    LO.Power = 12
    LO.Freq = CAV_freq - exp_globals['IF']
    LO.Output = 'On'
    
    configure_card(card, settings)

    ##HDAWG settings
    configure_hdawg(hdawg, settings)
    
    progFile = open(r"C:\Users\Kollarlab\Desktop\Kollar-Lab\pulsed_measurements\HDAWG_sequencer_codes\T1.cpp",'r')
    rawprog  = progFile.read()
    loadprog = rawprog
    progFile.close()
    
    q_pulse = exp_globals['qubit_pulse']
    m_pulse = exp_globals['measurement_pulse']
    loadprog = loadprog.replace('_max_time_', str(m_pulse['meas_pos']))
    loadprog = loadprog.replace('_meas_window_', str(m_pulse['meas_window']))
    loadprog = loadprog.replace('_tau_',str(q_pulse['delay']))
    loadprog = loadprog.replace('_qsigma_',str(q_pulse['sigma']))
    loadprog = loadprog.replace('_num_sigma_',str(q_pulse['num_sigma']))

    hdawg.AWGs[0].load_program(loadprog)

    hdawg.AWGs[0].run_loop()
    time.sleep(0.1)
    
    powerdat = np.zeros((len(powers), len(freqs)))
    phasedat = np.zeros((len(powers), len(freqs)))
    
    tstart = time.time()
    first_it = True
    
    for powerind in range(len(powers)):
        qubitgen.Power = powers[powerind]
        time.sleep(0.2)
        
        total_samples = card.samples

        amps_full = np.zeros((len(freqs), total_samples))
        phases_full = np.zeros((len(freqs), total_samples))
        
        print('Current power:{}, max:{}'.format(powers[powerind]-Qbit_Attenuation, powers[-1]-Qbit_Attenuation))
    
        for find in range(0, len(freqs)):
            freq = freqs[find]
            
            qubitgen.Freq = freq
            time.sleep(0.2)

            amp, phase, amp_full, phase_full, xaxis = read_and_process(card, settings, plot = first_it)

            if first_it:
                tstop = time.time()
                estimate_time(tstart, tstop, len(powers)*len(freqs))
                first_it = False
            
            powerdat[powerind, find] = np.mean(amp)
            phasedat[powerind, find] = np.mean(phase)
            amps_full[find,:]   = amp_full
            phases_full[find,:] = phase_full

        full_data = {}
        full_data['xaxis'] = freqs/1e9
        full_data['mags'] = powerdat[0:powerind+1]
        full_data['phases'] = phasedat[0:powerind+1]

        single_data = {}
        single_data['xaxis'] = freqs/1e9
        single_data['mag'] = powerdat[powerind, :]
        single_data['phase'] = phasedat[powerind, :]

        yaxis = powers[0:powerind+1] - Qbit_Attenuation
        labels = ['Freq (GHz)', 'Power (dBm)']
        simplescan_plot(full_data, single_data, yaxis, filename, labels, identifier='', fig_num=1) 
        plt.savefig(os.path.join(saveDir, filename+'_fullColorPlot.png'), dpi = 150)

        full_time = {}
        full_time['xaxis'] = xaxis*1e6
        full_time['mags'] = amps_full
        full_time['phases'] = phases_full

        single_time = {}
        single_time['xaxis'] = xaxis*1e6
        single_time['mag'] = amp_full
        single_time['phase'] = phase_full

        time_labels = ['Time (us)', 'Freq (GHz)']
        identifier = 'Power: {}dBm'.format(powers[powerind]-Qbit_Attenuation)
        
        simplescan_plot(full_time, single_time, freqs/1e9, 'Raw_time_traces\n'+filename, time_labels, identifier, fig_num=2)
        plt.savefig(os.path.join(saveDir, filename+'_Raw_time_traces.png'), dpi = 150)

        userfuncs.SaveFull(saveDir, filename, ['powers','freqs', 'powerdat', 'phasedat','xaxis','full_data', 'single_data', 'full_time', 'single_time'],
                             locals(), expsettings=settings, instruments=instruments)

    t2 = time.time()
    
    print('elapsed time = ' + str(t2-tstart))
       
    cavitygen.Output = 'Off'
    qubitgen.Output = 'Off'
    LO.Output = 'Off'