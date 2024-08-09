# -*- coding: utf-8 -*-
"""
Created on Tue Dec 13 11:52:24 2022

@author: kollarlab
"""

from qick.averager_program import QickSweep, NDAveragerProgram

import numpy as np
import os
import time
import matplotlib.pyplot as plt
import userfuncs

      
#Heavily considering getting rid of the initial and post buffers for the speedup classes...
#Don't see the use when we can't acquire_decimated` anyway.

class GainSweepPi2(NDAveragerProgram):
    def initialize(self):
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

        # Configure cavity DAC
        freq_c  = self.freq2reg(cfg["cav_freq"],gen_ch=gen_ch, ro_ch=cfg["ro_channels"][0])
        phase_c = self.deg2reg(cfg["cav_phase"], gen_ch=gen_ch)
        gain_c  = cfg["meas_gain"]
        
        self.default_pulse_registers(ch=gen_ch, freq=freq_c, phase=phase_c, gain=gain_c)
        self.set_pulse_registers(ch=gen_ch, style="const", length=self.us2cycles(self.cfg["meas_window"],gen_ch=gen_ch))
        
        # Configure qubit DAC
        freq_q  = self.freq2reg(cfg["qub_freq"],gen_ch=qub_ch)
        phase_q = self.deg2reg(cfg["qub_phase"], gen_ch=gen_ch)
        gain_q  = cfg["gain_start"]
        
        self.default_pulse_registers(ch=qub_ch, phase=phase_q, freq=freq_q, gain=gain_q)
        
        sigma = self.us2cycles(cfg["qub_sigma"],gen_ch=qub_ch)
        num_sigma = cfg["num_sigma"]
        
        self.add_gauss(ch=qub_ch, name="ex", sigma=sigma,length=int(sigma*num_sigma))        
        self.set_pulse_registers(ch=qub_ch, style="arb", waveform="ex")

        ###Start sweep definition
        
        self.qub_r_gain = self.get_gen_reg(qub_ch,"gain")
        
        self.add_sweep(QickSweep(self, self.qub_r_gain,cfg["gain_start"],cfg["gain_stop"],cfg["gain_points"]))
        
        # give processor some time to configure pulses, I believe it sets the offset time 200 cycles into the future?
        # Try varying this and seeing if it moves. Also try putting a synci after the trigger in the body
        self.synci(200)   
    
    def body(self):
        #The body sets the pulse sequence, it runs through it a number of times specified by "reps" and takes averages
        #specified by "soft_averages." Both are required if you wish to acquire_decimated, only "reps" is otherwise.
        sigma = self.us2cycles(self.cfg["qub_sigma"])
        num_sigma = self.cfg["num_sigma"]
        
        #ex_time_fixed = meas_time - self.us2cycles(self.cfg['qub_delay'],gen_ch=self.cfg["qub_channel"]) - int(num_sigma*sigma)
        
        pulse_len = int(num_sigma*sigma)

        offset = self.us2cycles(self.cfg["adc_trig_offset"],gen_ch=self.cfg["cav_channel"])
        meas_time = self.us2cycles(self.cfg["meas_time"],gen_ch=self.cfg["cav_channel"])
        ex_time = meas_time - self.us2cycles(self.cfg['qub_delay'],gen_ch=self.cfg["qub_channel"]) - pulse_len
        ex_time_2 = ex_time - self.us2cycles(0.1,gen_ch=self.cfg['qub_channel']) - pulse_len
        #Sets off the ADC
        self.trigger(adcs=self.ro_chs,
                    pins=[0],
                    adc_trig_offset=offset)
        
        #Sends measurement pulse
        self.pulse(ch=self.cfg["qub_channel"],t=ex_time_2)
        self.pulse(ch=self.cfg["qub_channel"],t=ex_time)
        self.pulse(ch=self.cfg["cav_channel"],t=meas_time)
        self.wait_all() #Tells TProc to wait until pulses are complete before sending out the next command
        self.sync_all(self.us2cycles(self.cfg["relax_delay"])) #Syncs to an offset time after the final pulse is sent


def get_gainpi2_settings():
    settings = {}
    
    settings['scanname'] = 'initial_power_scan_q4'
    settings['meas_type'] = 'GainSweepPi2'
    
    settings['cav_freq'] = 1e9
    settings['cav_gain'] = 1000

    settings['qub_freq'] = 1e9

    #Sweep parameters
    settings['gain_start']  = 1000
    settings['gain_stop']   = 2000
    settings['gain_points'] = 3
    



    #Card settings
    settings['reps'] = 1
    settings['soft_avgs'] = 5e3
    
    return settings

def gain_sweep_pi2(soc,soccfg,instruments,settings):

    exp_globals  = settings['exp_globals']
    exp_settings = settings['exp_settings'] 
    m_pulse      = exp_globals['measurement_pulse']
    q_pulse      = exp_globals['qubit_pulse']
    
    soc.reset_gens()
    
    lo_freq = 0
    
    if exp_globals['LO']:
        logen = instruments['LO']
        lo_freq = exp_globals['LO_freq']
        logen.freq   = lo_freq
        logen.power  = exp_globals['LO_power']
        logen.output = 1

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
        'meas_gain'       : exp_settings['cav_gain'],
        'cav_freq'        : (exp_settings['cav_freq']-lo_freq)/1e6,
        
        'nqz_q'           : 2,
        'qub_phase'       : q_pulse['qub_phase'],

        'qub_freq'        : exp_settings['qub_freq']/1e6,
        ### Fix the freq_start stuff in the original class

        'gain_start'      : exp_settings['gain_start'],
        'gain_stop'       : exp_settings['gain_stop'],
        'gain_points'     : exp_settings['gain_points'],

        'qub_sigma'       : q_pulse['sigma'],
        'qub_delay'       : q_pulse['delay'],
        'num_sigma'       : q_pulse['num_sigma'],

        'readout_length'  : m_pulse['meas_window'],
        'adc_trig_offset' : m_pulse['emp_delay'] + m_pulse['meas_pos'],


        'relax_delay'     : exp_globals['relax_delay'],
        'reps'            : exp_settings['reps'],
        'soft_avgs'       : exp_settings['soft_avgs']
        }


    prog = GainSweepPi2(soccfg,config)
    rep_period = config['adc_trig_offset'] + config['readout_length'] + config['relax_delay']
    
    
    
    projected_time = config['soft_avgs']*config['gain_points']*rep_period/1e6
    print("Projected Time: " + str(projected_time))
    
    t_i = time.time()
    
    
    
    exp_pts, avg_di, avg_dq = prog.acquire(soc, load_pulses=True, progress=False, debug=False)
    
    
    Is = avg_di[0][0]
    Qs = avg_dq[0][0]
    
    gains = exp_pts[0]
    
    powerdat = np.sqrt(Is**2 + Qs**2)
    phasedat = np.arctan(Qs,Is)*180/np.pi

    full_data = {}

    full_data['xaxis']  = gains
    full_data['mags']   = powerdat
    full_data['phases'] = phasedat
    full_data['Is']     = Is
    full_data['Qs']     = Qs

    fig1 = plt.figure(1)
    plt.clf()
    plt.plot(gains, powerdat)
    plt.title('Mag {}'.format(filename))
    plt.xlabel('Gain')
    plt.ylabel('Amplitude')
    fig1.canvas.draw()
    fig1.canvas.flush_events()
    plt.savefig(os.path.join(saveDir, filename+'.png'), dpi=150)

    userfuncs.SaveFull(saveDir, filename, ['gains','full_data','filename'],
    locals(), expsettings=settings, instruments={})
    
    if exp_globals['LO']:
        logen.output = 0

    t_f    = time.time()
    t_single = t_f - t_i
    
    print("Elapsed Time: " + str(t_single))

    data = {'saveDir': saveDir, 'filename': filename, 'full_data': full_data}

    return data
