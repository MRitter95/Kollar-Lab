# -*- coding: utf-8 -*-
"""
Created on Tue Oct 17 11:45:34 2023

@author: kollarlab
"""

'''
## General flow I'd like to see:
    run the calibration and store it in a dictionary or something
    update the params for all the instruments accordingly
    user defines schedule in a different file and specifies how it should update params
    sweep any parameter for instrument or schedule (at this point schedule should behave like an instrument)
    sweep results (values and sweep values) should be accessible in the "top" layer of the code, i.e. here
'''
from pulsed_measurements.schedules.scheduler_v2 import marker, flat_top
import matplotlib.pyplot as plt
import numpy as np
from pulsed_measurements.schedules.basic_single_pulse import basic_single_pulse

from pulsed_measurements.schedules.simple_sweep import simple_sweeper

#fake import to make the documentation work

def test_schedule(hdawg, holz, card, qubitgen):
    qsettings = {'sigma':2.1e-9, 'hold_time':3e-9, 'angle':0, 'amp':0.5}
    qpulse = flat_top(1000e-9, qsettings)
    qpulse.compile_pulse()
    # plt.figure()
    # plt.plot(qpulse.I)
    # plt.plot(qpulse.Q)
    msettings = {'position':155e-6, 'length':10e-6}
    mpulse = marker(msettings)

    schedule = basic_single_pulse(175e-6, qpulse, mpulse, awg=hdawg.AWGs[0])

    instruments = {}
    instruments['cavitygen'] = holz.ch1
    instruments['qubitgen'] = qubitgen
    instruments['LO'] = holz.ch2
    instruments['card'] = card
    instruments['AWG'] = hdawg
    instruments['schedule'] = schedule

    exp_settings = {}
    exp_settings['averages'] = 2e3
    exp_settings['segments'] = 1
    exp_settings['reads']    = 1
    exp_settings['meas_type'] = '1D_sweep'
    exp_settings['scanname'] = 'calibration'
    exp_settings['subtract_background'] = True

    settings = {}
    settings['exp_globals'] = exp_globals
    settings['exp_settings'] = exp_settings
    sweeper = simple_sweeper(instruments, settings, calibration)

    sweeper.initialize_sweep('Spec', 'Hz', 'qubitgen', 'freq', np.linspace(-50,50,101)*1e6+calibration['Q_Freq'])
    sweeper.initialize_sweep('Hold_time', 's', 'schedule', 'hold_time', np.linspace(0,100,51)*1e-9)
    sweeper.initialize_sweep('T1', 's', 'schedule', 'tau', np.linspace(0.1,150,51)*1e-6)

    fig, [[ax1,ax2],[ax3,ax4]] = plt.subplots(2,2,num=79)

    schedule.tau = 0.1e-6
    schedule.hold_time = 30e-6
    calibration['Q_Power'] = -10
    sweeper.configure_instruments(instruments, calibration)
    sweeper.run_sweep('Spec')
    data = sweeper.sweeps['Spec']
    fit_results = fit_model(data['values'], data['IQ_mag'], 'lorenz', True, ax=ax1)
    calibration['Q_Freq'] = fit_results['center']
    calibration['Q_Power'] = 15
    sweeper.configure_instruments(instruments, calibration)
    sweeper.run_sweep('Hold_time')
    data = sweeper.sweeps['Hold_time']
    fit_results = fit_model(data['values'], data['IQ_mag'], 'cos', True, ax=ax2)
    schedule.hold_time=3e-9
    sweeper.run_sweep('T1')
    data = sweeper.sweeps['T1']
    fit_results = fit_model(data['values'], data['IQ_mag'], 'T1', True, ax=ax3)