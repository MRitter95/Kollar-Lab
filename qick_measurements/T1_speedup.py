# -*- coding: utf-8 -*-
"""
Created on Wed Feb  1 10:16:54 2023

@author: kollarlab
"""

from qick.averager_program import QickSweep, NDAveragerProgram, AveragerProgram

import numpy as np
import os
import matplotlib.pyplot as plt
import userfuncs
import time

from utility.userfits import fit_T1
from utility.plotting_tools import general_colormap_subplot
from utility.measurement_helpers import estimate_time

      
class T1_speedup(NDAveragerProgram):
    '''
    T1_speedup _summary_

    :param NDAveragerProgram: _description_
    :type NDAveragerProgram: _type_
    '''    
    def initialize(self):
        '''
        initialize _summary_
        '''        
        cfg=self.cfg   
        gen_ch = cfg["cav_channel"]
        qub_ch = cfg["qub_channel"]

        # set the nyquist zone
        # Implement an if statement here to catch? 
        self.declare_gen(ch=cfg["cav_channel"], nqz=cfg["nqz_c"])
        self.declare_gen(ch=cfg["qub_channel"], nqz=cfg["nqz_q"])
        
        # configure the readout lengths and downconversion frequencies (ensuring it is an available DAC frequency)
        
        readout = self.us2cycles(cfg["readout_length"],ro_ch=cfg["ro_channels"][0])
        for ch in cfg["ro_channels"]:
            self.declare_readout(ch=ch, length=readout,
                                 freq=self.cfg["cav_freq"], gen_ch=cfg["cav_channel"])

        # convert frequency to DAC freqency (ensuring it is an available ADC frequency)
        freq_c  = self.freq2reg(cfg["cav_freq"],gen_ch=gen_ch, ro_ch=cfg["ro_channels"][0])
        phase_c = self.deg2reg(cfg["cav_phase"], gen_ch=gen_ch)
        gain_c  = cfg["meas_gain"]
        
        self.default_pulse_registers(ch=gen_ch, freq=freq_c, phase=phase_c, gain=gain_c)
        self.set_pulse_registers(ch=gen_ch, style="const", length=self.us2cycles(self.cfg["meas_window"],gen_ch=gen_ch))
        
        freq_q  = self.freq2reg(cfg["qub_freq"],gen_ch=qub_ch)
        phase_q = self.deg2reg(cfg["qub_phase"], gen_ch=gen_ch)
        gain_q  = cfg["qub_gain"]
        
        self.default_pulse_registers(ch=qub_ch, phase=phase_q, freq=freq_q, gain=gain_q)
        
        sigma = self.us2cycles(cfg["qub_sigma"],gen_ch=qub_ch)
        num_sigma = cfg["num_sigma"]
        
        self.add_gauss(ch=qub_ch, name="ex", sigma=sigma,length=int(sigma*num_sigma))        
        self.set_pulse_registers(ch=qub_ch, style="arb", waveform="ex")
        
        ### Adding sweep on time register        
        
        meas_time = self.us2cycles(self.cfg["meas_time"],gen_ch=self.cfg["cav_channel"])
        raw_ex_time = meas_time - int(num_sigma*sigma)
        
        self.tau = self.get_gen_reg(qub_ch,'t') #Find empty register
        
        self.add_sweep(QickSweep(self, self.tau, raw_ex_time-self.us2cycles(cfg["Tau_min"]),raw_ex_time-self.us2cycles(cfg["Tau_max"]),cfg["Tau_points"]))

        
        # give processor some time to configure pulses, I believe it sets the offset time 200 cycles into the future?
        # Try varying this and seeing if it moves. Also try putting a synci after the trigger in the body
        self.synci(200)   
    
    def body(self):
        '''
        body _summary_
        '''        
        #The body sets the pulse sequence, it runs through it a number of times specified by "reps" and takes averages
        #specified by "soft_averages." Both are required if you wish to acquire_decimated, only "reps" is otherwise.
        
        offset = self.us2cycles(self.cfg["adc_trig_offset"])
        meas_time = self.us2cycles(self.cfg["meas_time"])

        #Sets off the ADC
        self.trigger(adcs=self.ro_chs,
                    pins=[0],
                    adc_trig_offset=offset)
        
        #Sends measurement pulse
        self.pulse(ch=self.cfg["qub_channel"],t=None) #Will go to time register to grab the value being swept
        self.pulse(ch=self.cfg["cav_channel"],t=meas_time)
        self.wait_all() #Tells TProc to wait until pulses are complete before sending out the next command
        self.sync_all(self.us2cycles(self.cfg["relax_delay"])) #Syncs to an offset time after the final pulse is sent

class CavitySweep(AveragerProgram):
    '''
    CavitySweep _summary_

    :param AveragerProgram: _description_
    :type AveragerProgram: _type_
    '''    
    def initialize(self):
        '''
        initialize _summary_
        '''        
        cfg=self.cfg   
        gen_ch = cfg["cav_channel"]

        # set the nyquist zone
        # Implement an if statement here to catch? 
        self.declare_gen(ch=cfg["cav_channel"], nqz=cfg["nqz_c"])
        
        # configure the readout lengths and downconversion frequencies (ensuring it is an available DAC frequency)
        
        readout = self.us2cycles(cfg["readout_length"],ro_ch=cfg["ro_channels"][0])
        for ch in cfg["ro_channels"]:
            self.declare_readout(ch=ch, length=readout,
                                 freq=self.cfg["cav_freq"], gen_ch=cfg["cav_channel"])

        # convert frequency to DAC freqency (ensuring it is an available ADC frequency)
        freq = self.freq2reg(cfg["cav_freq"],gen_ch=gen_ch, ro_ch=cfg["ro_channels"][0])
        phase = self.deg2reg(cfg["cav_phase"], gen_ch=gen_ch)
        gain = cfg["meas_gain"]
        self.default_pulse_registers(ch=gen_ch, freq=freq, phase=phase, gain=gain)

        
        self.set_pulse_registers(ch=gen_ch, style="const", length=self.us2cycles(self.cfg["meas_window"],gen_ch=gen_ch))

        
        # give processor some time to configure pulses, I believe it sets the offset time 200 cycles into the future?
        # Try varying this and seeing if it moves. Also try putting a synci after the trigger in the body
        self.synci(200)   
    
    def body(self):
        '''
        body _summary_
        '''        
        #The body sets the pulse sequence, it runs through it a number of times specified by "reps" and takes averages
        #specified by "soft_averages." Both are required if you wish to acquire_decimated, only "reps" is otherwise.
        offset = self.us2cycles(self.cfg["adc_trig_offset"],gen_ch=self.cfg["cav_channel"])
        meas_time = self.us2cycles(self.cfg["meas_time"],gen_ch=self.cfg["cav_channel"])
        #Sets off the ADC
        self.trigger(adcs=self.ro_chs,
                    pins=[0],
                    adc_trig_offset=offset)
        
        #Sends measurement pulse
        self.pulse(ch=self.cfg["cav_channel"],t=meas_time)
        self.wait_all() #Tells TProc to wait until pulses are complete before sending out the next command
        self.sync_all(self.us2cycles(self.cfg["relax_delay"]))


def get_T1_settings():
    '''
    get_T1_settings _summary_

    :return: _description_
    :rtype: _type_
    '''    
    settings = {}
    
    settings['scanname'] = 'initial_power_scan_q4'
    settings['meas_type'] = 'Tmeas'
    
    settings['cav_freq'] = 1e9
    settings['meas_gain'] = 1000
    
    settings['qub_freq'] = 4e9
    settings['qub_gain'] = 1000
    
    #Sweep parameters    
    settings['Tau_min']    = 200e-9
    settings['Tau_max']    = 30e-6
    settings['Tau_points'] = 5
    
    settings['T1_guess'] = 10e-6
    #Card settings
    settings['reps'] = 1
    settings['soft_avgs'] = 5e3
    
    return settings

def meas_T1(soc,soccfg,instruments,settings):
    '''
    meas_T1 _summary_

    :param soc: _description_
    :type soc: _type_
    :param soccfg: _description_
    :type soccfg: _type_
    :param instruments: _description_
    :type instruments: _type_
    :param settings: _description_
    :type settings: _type_
    '''    
    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings'] 
    m_pulse      = exp_globals['measurement_pulse']
    q_pulse      = exp_globals['qubit_pulse']
    
    if exp_globals['LO']:
        logen = instruments['LO']
        
        logen.freq   = exp_globals['LO_freq']
        logen.power  = exp_globals['LO_power']
        logen.output = 1
    else:
        print("Warning: No LO has been initialized.")

    stamp    = userfuncs.timestamp()
    saveDir  = userfuncs.saveDir(settings)
    filename = exp_settings['scanname'] + '_' + stamp

    config = {
        'cav_channel'     : exp_globals['cav_channel'],
        'qub_channel'     : exp_globals['qub_channel'],
        'ro_channels'     : exp_globals['ro_channels'],

        'nqz_c'           : 1,
        'cav_phase'       : m_pulse['cav_phase'],
        'meas_window'     : m_pulse['meas_window'],
        'meas_time'       : m_pulse['meas_pos'],
        'meas_gain'       : exp_settings['meas_gain'],
        'cav_freq'        : (exp_settings['cav_freq']-exp_globals['LO_freq'])/1e6,
        
        'nqz_q'           : 2,
        'qub_phase'       : q_pulse['qub_phase'],
        'qub_freq'        : exp_settings['qub_freq']/1e6,
        'qub_gain'         : exp_settings['qub_gain'],
        'qub_sigma'        : q_pulse['sigma'],
        'Tau_min'         : exp_settings['Tau_min']*1e6,
        'Tau_max'         : exp_settings['Tau_max']*1e6,
        'Tau_pts'         : exp_settings['Tau_pts'],
        'num_sigma'       : q_pulse['num_sigma'],
        
        'readout_length'  : m_pulse['meas_window'],
        'adc_trig_offset' : m_pulse['emp_delay'] + m_pulse['meas_pos'],


        'relax_delay'     : exp_globals['relax_delay'],
        'reps'            : exp_settings['reps'],
        'soft_avgs'       : exp_settings['soft_avgs']
        }

    ################## Most things from this point onwards are wrong.    
    
    prog = T1_speedup(soccfg,config)
    
    
    tstart = time.time()
    
    if exp_settings['subtract_background']:
        #Acquire background trace
#            qubitgen.freq=3.8e9
#            time.sleep(0.1)
        print('Starting Background Trace')
        bprog = CavitySweep(soccfg,config)
        holder = bprog.acquire_decimated(soc, load_pulses=True, progress=False, debug=False)
        print('Background Trace Complete')
        I_full_b = holder[0][0]
        Q_full_b = holder[0][1] 
    else:
        I_full_b, Q_full_b = 0,0,0,0

    I_back, Q_back = [np.mean(I_full_b), np.mean(Q_full_b)] #<I>, <Q> for background trace
    
      
    expt_pts, avg_di, avg_dq = prog.acquire(soc, load_pulses=True, progress=False, debug=False)

    

    Is = avg_di[0][0]
    Qs = avg_dq[0][1]
    

    taus = expt_pts[0]
        
    I_final = Is-I_back #compute <I_net> in the data window
    Q_final = Qs-Q_back

    powerdat = np.sqrt(I_final**2 + Q_final**2)
    phasedat = np.arctan(Q_final,I_final)*180/np.pi



    t2 = time.time()
    print('Elapsed time: {}'.format(t2-tstart))       
        
    fig = plt.figure(1, figsize=(13,8))
    plt.clf()
    plt.subplot(121)
    plt.plot(taus, powerdat, 'x')
    plt.xlabel('Tau (us)')
    plt.ylabel('Amplitude')  
    plt.subplot(122)
    plt.plot(taus, phasedat, 'x')
    plt.xlabel('Tau (us)')
    plt.ylabel('Phase')  
    plt.title('Live T1 data (no fit)\n'+filename)
    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.savefig(os.path.join(saveDir, filename+'_no_fit.png'), dpi = 150)
        
    

    T1_guess = exp_settings['T1_guess']
    amp_guess = max(powerdat)-min(powerdat)
    offset_guess = powerdat[-1]

    fit_guess = [T1_guess, amp_guess, offset_guess]
    T1, amp, offset, fit_xvals, fit_yvals = fit_T1(taus/1e6, powerdat, fit_guess)
    fig2 = plt.figure(2)
    plt.clf()
    plt.plot(taus, powerdat)
    plt.plot(fit_xvals*1e6, fit_yvals)
    plt.title('T1:{}us \n {}'.format(np.round(T1*1e6,3), filename))
    plt.xlabel('Time (us)')
    plt.ylabel('Amplitude')
    fig2.canvas.draw()
    fig2.canvas.flush_events()
    plt.savefig(os.path.join(saveDir, filename+'_fit.png'), dpi=150)

    userfuncs.SaveFull(saveDir, filename, ['taus', 'powerdat', 'phasedat', 'tau', 'amp', 'offset', 'fit_guess'],
                         locals(), expsettings=settings, instruments=instruments)
    
    if exp_globals['LO']:
        logen.output = 0

    return T1, taus, powerdat
   




        