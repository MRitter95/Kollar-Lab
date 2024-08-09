# -*- coding: utf-8 -*-
"""
Created on Fri Feb 26 10:28:57 2021

@author: Kollarlab
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt

import userfuncs
from utility.measurement_helpers import configure_card, estimate_time, read_and_process
#from topo_helpers import rotating_field_schedule
import scipy.signal as signal

    
class Bz_osc():
    def __init__(self,instruments, settings):
        
        self.settings     = settings
        self.exp_globals  = settings['exp_globals']
        self.exp_settings = settings['exp_settings'] 
        self.calibration  = settings['calibration']
        self.instruments  = instruments
        self.exp_settings['spec'] = {'meas_type':'Bz_osc'}
        
        start   = self.exp_settings['start_time']
        stop    = self.exp_settings['stop_time']
        points  = self.exp_settings['time_points']
        self.evolution_times = np.round(np.linspace(start,stop,points), 9)
        
        self.generate_filename()
        self.config_instruments()
        self.generate_filter()
        
        self.schedule = rotating_field_schedule(settings, self.hdawg)
        
        self.timedat  = np.zeros(points)
        self.phasedat = np.zeros(points)
        
    def generate_filename(self):
        stamp    = userfuncs.timestamp()
        self.saveDir  = userfuncs.saveDir(self.settings)
        self.filename = self.exp_settings['scanname'] + '_' + stamp
        
    def config_instruments(self):
        
        exp_globals = self.exp_globals
        calibration = self.calibration
        instruments = self.instruments
        ##Instruments used
        qubitgen  = instruments['qubitgen']
        cavitygen = instruments['cavitygen']
        card      = instruments['card']
        hdawg     = instruments['AWG']
        LO        = instruments['LO']
        
        ##Cavity settings
        CAV_Attenuation = exp_globals['CAV_Attenuation']
        CAV_power = calibration['CAV_Power'] + CAV_Attenuation
        CAV_freq  = calibration['CAV_Freq']
        
        ##Qubit settings
        Q_freq = calibration['Q_Freq']
        Q_power = calibration['Q_Power']+exp_globals['Qbit_Attenuation']
        
        ## Generator settings
        cavitygen.freq   = CAV_freq
        cavitygen.power  = CAV_power
        cavitygen.enable_pulse()
    
        qubitgen.freq   = Q_freq
        qubitgen.power  = Q_power
        
        qubitgen.enable_pulse()
        qubitgen.enable_IQ()
    
        cavitygen.output = 'On'
        qubitgen.output  = 'On'
        
        LO.power  = 12
        LO.freq   = CAV_freq - exp_globals['IF']
        LO.output = 'On'
        
        ##Card settings
        configure_card(card, self.settings)
        
        self.qubitgen = qubitgen
        self.cavitygen = cavitygen
        self.card = card
        self.hdawg = hdawg
        self.LO = LO
    
    def generate_filter(self):
        settings = self.settings
        #create Chebychev type II digital filter
        filter_N = self.exp_globals['ddc_config']['order']
        filter_rs = self.exp_globals['ddc_config']['stop_atten']
        filter_cutoff = np.abs(self.exp_globals['ddc_config']['cutoff'])
        LPF = signal.cheby2(filter_N, filter_rs, filter_cutoff, btype='low', analog=False, output='sos', fs=self.card.sampleRate)
        
        xaxis = np.arange(0, self.card.samples, 1) * 1/self.card.sampleRate
        digLO_sin = np.sin(2*np.pi*self.exp_globals['IF']*xaxis)
        digLO_cos = np.cos(2*np.pi*self.exp_globals['IF']*xaxis)
        
        #store in settings so that the processing functions can get to them
        settings['digLO_sin'] = digLO_sin 
        settings['digLO_cos'] = digLO_cos
        settings['LPF'] = LPF
        self.settings = settings

    def sweep_evolution_time(self):    
        tstart = time.time()
        self.cavitygen.Output = 'On'
        self.qubitgen.Output  = 'On'
        self.LO.Output        = 'On'
        first_it = True
            
        for timeind,t_evolv in enumerate(self.evolution_times):
            
            ##Update schedule and upload to the AWG
            self.schedule.update_schedule(t_evolv)
            
            [ch1, ch2, marker] = self.schedule.awg_0_data
            [ch3, ch4, marker2] = self.schedule.awg_1_data
    
            self.hdawg.AWGs[0].stop()
            self.hdawg.AWGs[0].load_waveform('0', ch1, ch2, marker)
            self.hdawg.AWGs[1].load_waveform('0', ch3, ch4, marker2)
            self.hdawg.AWGs[0].run_loop()
            
            ##Acquire data and background trace
            I_window, Q_window, I_full, Q_full, xaxis = read_and_process(self.card, self.settings, 
                                                                         plot=first_it, 
                                                                         IQstorage = True)
            if self.exp_settings['subtract_background']:
                #Acquire background trace
                self.qubitgen.output='Off'
                I_window_b, Q_window_b, I_full_b, Q_full_b, xaxis_b = read_and_process(self.card, self.settings, 
                                                                 plot=first_it, 
                                                                 IQstorage = True)
                self.qubitgen.output='On'
            else:
                I_window_b, Q_window_b, I_full_b, Q_full_b = 0,0,0,0
            
            if first_it:
                first_it=False
            ##Useful handles for variables
            I_sig, Q_sig   = [np.mean(I_window), np.mean(Q_window)] #<I>, <Q> for signal trace
            I_back, Q_back = [np.mean(I_window_b), np.mean(Q_window_b)] #<I>, <Q> for background trace
            theta_sig  = np.arctan2(Q_sig,I_sig)*180/np.pi #angle relative to x axis in IQ plane
            theta_back = np.arctan2(Q_back, I_back)*180/np.pi #angle relative to x axis in IQ plane 
            
            I_final = I_sig-I_back #compute <I_net> in the data window
            Q_final = Q_sig-Q_back #compute <Q_net> in the data window
            
            amp = np.sqrt(I_final**2 + Q_final**2)
            phase = np.arctan2(Q_final, I_final)*180/np.pi    
            
            ##Save and plot data
            self.timedat[timeind]  = np.mean(amp)
            self.phasedat[timeind] = np.mean(phase)
            
            t_axis = self.evolution_times[:timeind+1]*1e6
            fig = plt.figure(1)
            plt.clf()
            plt.subplot(121)
            plt.plot(t_axis, self.timedat[:timeind+1])
            plt.xlabel('Hold time (us)')
            plt.ylabel('Mag')
            plt.subplot(122)
            plt.plot(t_axis, self.phasedat[:timeind+1])
            plt.xlabel('Hold time (us)')
            plt.ylabel('Phase')
            plt.suptitle('Bz oscillation\n'+self.filename)
            fig.canvas.draw()
            fig.canvas.flush_events()
            plt.savefig(os.path.join(self.saveDir, self.filename+'.png'), dpi = 150)
            
            times = self.evolution_times
            timedat = self.timedat
            phasedat = self.phasedat
            userfuncs.SaveFull(self.saveDir, self.filename, ['times','timedat', 'phasedat'], 
                                locals(), expsettings=self.settings, instruments=self.instruments, 
                                saveHWsettings=first_it)
            
        t2 = time.time()
        
        print('elapsed time = ' + str(t2-tstart))
    
        self.cavitygen.Output = 'Off'
        self.qubitgen.Output  = 'Off'
        self.LO.Output        = 'Off'