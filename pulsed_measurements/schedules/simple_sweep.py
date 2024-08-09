# -*- coding: utf-8 -*-
"""
Created on Wed Feb 22 16:19:28 2023

@author: Kollarlab
"""
'''
Our code should be pretty simple
1. Initialize all the stuff (all instruments/ objects)
2. Perform sweep:
    a. update the state of the experiment
    b. collect a measurement
    c. plot the data and stuff 
    d. save data
3. Return data to user 

'''
import os
import numpy as np
import matplotlib.pyplot as plt
from utility.measurement_helpers import configure_card, read_and_process
from pulsed_measurements.schedules.SI_conversion import get_prefix, convert_to_prefix
from userfuncs import timestamp, saveDir, SaveFull
import scipy.signal as signal

class measurement(object):
    def __init__(self, card, settings):
        self.card = card
        self.settings = settings
        configure_card(card, settings)
    def acquire(self, plot, IQstorage=True):
        I, Q, Ifull, Qfull, x = read_and_process(self.card, self.settings, plot, IQstorage)
        self.I = np.mean(I)
        self.Q = np.mean(Q)
        self.Ifull = Ifull
        self.Qfull = Qfull
        self.x = x
        return self.I, self.Q, Ifull, Qfull, x
            
class simple_sweeper(measurement):
    def __init__(self, instruments, settings, calibration):
        '''
        Initialize/ configure all the instruments, generate the folder to save the data in,
        configure the filter for DDC

        Parameters
        ----------
        instruments : dict
            Dictionary holding all the instruments to be used for this particular measurement. 
            The topology/naming is fixed for this basic simple sweep to a: cavity, LO, qubit, 
            card and AWG but more can be added by inheriting this class and adding more 
            functions
        settings : dict
            Dictionary of dictionaries (exp globals, exp settings, calibration) holding all the
            settings. Exp globals contains things like the HW attenuation, the mixer corrections,
            rep rate etc., exp settings hold the specific settings for this measurement (name, 
            number of points, range etc.), and calibration is the dictionary holding: qubit 
            power/freq, hold time, cavity power/freq and the AWG amplitude for a pi pulse

        Returns
        -------
        None.

        '''
        self.instruments = instruments
        self.settings    = settings
        self.calibration = calibration
        
        self.exp_globals  = settings['exp_globals']
        self.exp_settings = settings['exp_settings'] 
        
        self.LO        = instruments['LO']
        self.cavitygen = instruments['cavitygen']
        self.qubitgen  = instruments['qubitgen']
        self.hdawg     = instruments['AWG']
        self.card      = instruments['card']
        self.schedule  = instruments['schedule']
        
        self.configure_instruments(instruments, calibration)
        
        # create directory/ filename
        stamp    = timestamp()
        self.saveDir  = saveDir(settings)
        self.filename = self.exp_settings['scanname'] + '_' + stamp
        
        # initialize dictionary of sweeps if we want to start queuing up a few
        self.sweeps = {}
        
        # generate the filter used for DDC and adding it to the settings dict 
        self.define_filter()
    
    def configure_instruments(self, instruments, calibration):
        '''
        
        Helper function to set up all the instruments using a provided calibration dict.
        This does have a built in/implied naming convention but since all measurements
        should inherit this I think this will be more consistent?
        Parameters
        ----------
        instruments : dict
            Dictionary holding all the instruments to be used for this particular measurement. 
            The topology/naming is fixed for this basic simple sweep to a: cavity, LO, qubit, 
            card and AWG but more can be added by inheriting this class and adding more 
            functions
        calibration : dict
            Dictionary holding all the calibration parameters (cavity power/freq, qubit powre/freq
                                                               hold time etc.)

        Returns
        -------
        None.

        '''
        self.cavitygen.freq = calibration['CAV_Freq']
        self.cavitygen.power = calibration['CAV_Power']+self.exp_globals['CAV_Attenuation']
        self.cavitygen.enable_pulse()
        self.cavitygen.output = 'On'
        
        self.LO.freq = self.cavitygen.freq-self.exp_globals['IF']
        self.LO.power = 12
        self.LO.output = 'On'
        
        self.qubitgen.freq = calibration['Q_Freq']
        self.qubitgen.power = calibration['Q_Power']+self.exp_globals['Qbit_Attenuation']
        self.qubitgen.enable_pulse()
        self.qubitgen.enable_IQ()
        self.qubitgen.output = 'On'
        
        configure_card(self.card, self.settings)
        
    def define_filter(self):
        exp_globals = self.exp_globals
        if exp_globals['IF'] != 0:
            #create Chebychev type II digital filter
            filter_N = exp_globals['ddc_config']['order']
            filter_rs = exp_globals['ddc_config']['stop_atten']
            filter_cutoff = np.abs(exp_globals['ddc_config']['cutoff'])
            LPF = signal.cheby2(filter_N, filter_rs, filter_cutoff, btype='low', 
                                analog=False, output='sos', fs=self.card.sampleRate)
            
            xaxis = np.arange(0, self.card.samples, 1) * 1/self.card.sampleRate
            digLO_sin = np.sin(2*np.pi*exp_globals['IF']*xaxis)
            digLO_cos = np.cos(2*np.pi*exp_globals['IF']*xaxis)
            
            #store in settings so that the processing functions can get to them
            self.settings['digLO_sin'] = digLO_sin 
            self.settings['digLO_cos'] = digLO_cos
            self.settings['LPF'] = LPF
            
    def plot(self, name, ind=None, values=np.array([])):
        ## Get the correct SI prefix so we can plot nicely
        sweep_params = self.sweeps[name]
        sweep_vals = sweep_params['values']
        sweep_prefix = sweep_params['prefix']
        sweep_label  = sweep_params['label']
        if not ind:
            ind = -1
        if not values.size:
            values = convert_to_prefix(sweep_vals, sweep_prefix)
        IQ_mag = sweep_params['IQ_mag']
        self.fig = plt.figure(1)
        plt.clf()
        plt.plot(values[:ind+1], IQ_mag[:ind+1])
        plt.xlabel(sweep_label)
        plt.title(self.filename)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        
    def save(self, name, save_inst_settings=True):
        var_list = ['sweeps']
        SaveFull(self.saveDir, 
                 self.filename, 
                 var_list, 
                 self.__dict__, 
                 self.settings, 
                 self.instruments, 
                 saveHWsettings=save_inst_settings)
        self.fig.savefig(os.path.join(self.saveDir, self.filename+'_'+name+'.png'), dpi=250)
        
    def initialize_sweep(self, name, unit, instrument, parameter, values, prefix=None):
        if not prefix:
            val, prefix = get_prefix(max(values))
        sweep_params = {
                'name'       : name,
                'unit'       : unit,
                'prefix'     : prefix,
                'instrument' : instrument,
                'parameter'  : parameter,
                'values'     : values,
                'label'      : name+' ({}{})'.format(prefix, unit),
                'IQ_mag'     : np.zeros(len(values)),
                'IQ_phase'   : np.zeros(len(values))
                }
        self.sweeps[name] = sweep_params
        
    def run_sweep(self, name):
        sweep_params = self.sweeps[name]
        instrument = self.__getattribute__(sweep_params['instrument'])
        parameter  = sweep_params['parameter']
        values     = sweep_params['values']
        prefix     = sweep_params['prefix']
        
        unitfull_vals = convert_to_prefix(values, prefix)
        save_inst_settings = True
        plot = True
        for ind, val in enumerate(values):
            instrument.__setattr__(parameter, val)
            I, Q, Ifull, Qfull, x = self.acquire(plot)
            if self.exp_settings['subtract_background']:
                self.qubitgen.output='Off'
                Ib,Qb,Ifb,Qfb,x = self.acquire(plot)
                self.qubitgen.output='On'
            sweep_params['IQ_mag'][ind] = np.sqrt((I-Ib)**2+(Q-Qb)**2)
            sweep_params['IQ_phase'][ind] = np.arctan2(Q, I)*180/np.pi
            
            self.plot(name, ind, unitfull_vals)
            self.save(name, save_inst_settings)
            save_inst_settings = False
            plot = False
        self.save(name)
            
