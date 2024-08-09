# -*- coding: utf-8 -*-
"""
Created on Fri Feb 26 13:33:50 2021

@author: Kollarlab
"""

import userfuncs
import os

import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as opt

def rabi_blobs(data_in, amp, w0, rabi_rate, phi):
    (freq, time) = data_in
    detuning = 2*np.pi*(freq-w0)
    eff_rabi_rate = np.sqrt(detuning**2+rabi_rate**2)
    eff_amp = rabi_rate**2/eff_rabi_rate**2
    
    rabi_blobs = amp*eff_amp*np.sin(phi+eff_rabi_rate*time/2)**2
    
    return rabi_blobs.ravel()
##### testing
## Create x and y indices
#freq = np.linspace(-5, 5, 51)
#time = np.linspace(0, 20, 51)
#freq, time = np.meshgrid(freq, time)
#
##create data
#data = rabi_blobs((freq, time), 0.5, 0, 3, np.pi/2)
#
## plot twoD_Gaussian data generated above
#plt.figure()
#plt.imshow(data.reshape(51, 51), origin='bottom', extent=(freq[0][0], freq[-1][-1], time[0][0], time[-1][-1]), aspect='auto')
#plt.colorbar()




saveDir = r'Z:\Data\HouckQuadTransmon\rabi_chevron\20210226'
filename = 'rabi_chevron_fine_20210226_110039.pkl'
raw_data = userfuncs.LoadFull(os.path.join(saveDir, filename))

times = raw_data[0]['times']
freqs = raw_data[0]['freqs']
amp   = raw_data[0]['timedat']

freq, time = np.meshgrid(freqs, times)
initial_guess = (0.0272,5.36e9,74e6,np.pi/2)

plt.figure()
data = rabi_blobs((freq, time), *initial_guess)
plt.imshow(data.reshape(len(times), len(freqs)), origin='bottom', extent=(freqs.min(), freqs.max(), times.min(), times.max()), aspect='auto')
plt.colorbar()

popt, pcov = opt.curve_fit(rabi_blobs, (freq, time), amp.ravel(), p0=initial_guess)

data_fitted = rabi_blobs((freq, time), *popt)

plt.figure()
plt.imshow(amp, origin='bottom', extent=(freqs.min(), freqs.max(), times.min(), times.max()), aspect='auto')
plt.colorbar()
plt.contour(freqs, times, data_fitted.reshape(len(times), len(freqs)), 1, colors='w')
amp_fit, w0, rabi, phi = popt
plt.title('w0:{}GHz, rabi rate:{}MHz, amp: {}'.format(np.round(w0/1e9,5), np.round(rabi/1e6, 3), np.round(amp_fit,3)))
plt.tight_layout()