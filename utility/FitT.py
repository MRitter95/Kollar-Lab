
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.fftpack import rfft, rfftfreq


def T1_model(x, tau, amp, offset):
    ''' 
    Returns the amplitude value of a T1 qubit measurement at a given time

    INPUTS:
    ########
        x (float or array of floats): time value
        tau (float) = T1
        amp (float) = amplitude
        offset (float) = the value to which the state decays
    
    OUTPUTS:
    ######### 
        float, Amplitude value at specified tau
    '''
    
    return amp*np.exp(- (x)/tau) + offset



def noisy_T1(x, tau, amp, offset, noise):
    '''
    Returns a noisy amplitude value of a T1 qubit measurement at a given time
    
    INPUTS:
    #########
        x (float or array of floats): time value
        tau (float): T1
        amp (float): amplitude
        offset (float): the value to which the state decays
        noise (float): Standard deviation of the Gaussian noise.
    
    OUTPUTS: 
    ########
        float, Noisy amplitude value at specified tau
    
    '''
    
    genData = T1_model(x, tau, amp, offset)
    noise = np.random.normal(0, noise, x.size)
    return genData + noise



def fit_T1(taus, amps):
    '''
    Automatically fits the parameters of a T1 qubit decay to given data.

    INPUTS:
    ########

        taus (float array): set of time values
        amps (float array): set of amplitude values 
    
    OUTPUT:
    ########
        Dictionary containing fitted parameters and analytics
    '''
    
    ts = np.linspace(min(taus), max(taus), 10*len(taus))
    fit_curve = np.zeros(len(ts))
    
    ## Hack to auto find the amplitude and fix rising vs decaysing exp
    og_amps = np.copy(amps)
    start_val = np.mean(amps[:5])
    stop_val = np.mean(amps[-5:])
    flipped=False
    if stop_val-start_val>0:
        flipped = True
    amps = abs(amps-stop_val)#+start_val
    [m,b] = np.polyfit(taus[:20], np.log(amps[:20]),1)
    tauinit = -1/m
    offsetinit = np.average(amps[-5:-1])
    ampinit = amps[0]#np.exp(b) - offsetinit

    '''print('T1 initial guess = {:.3}'.format(tauinit*1e6))
    print('Amplitude initial guess = {:.5}'.format(ampinit))
    print('Offset initial guess = {:.5}'.format(offsetinit))'''
    
    fit_guess = [tauinit, ampinit, offsetinit]

    tau = 0
    amp = 0
    offset = 0

    try:
        fit_out, pcov = curve_fit(T1_model, taus, amps, p0 = fit_guess)
        tau, amp, offset, *_ = fit_out
        fit_curve = T1_model(ts, tau, amp, offset)
    except:
        print('Fit did not converge, returning zeros')
        return {'tau':tau, 'amp':amp, 'offset':offset, 'ts':ts, 'fit_curve':fit_curve, 'fit_guess':fit_guess}
    if flipped:
        fit_curve= abs(fit_curve-fit_curve[0])+og_amps[0] #fit_curve[-1]
        #print('echo')
    return {'tau':tau, 'amp':amp, 'offset':offset, 'ts':ts, 'fit_curve':fit_curve, 'fit_guess':fit_guess}

def T2_model(x, tau, amp, offset, freq, phi):
    
    '''
    Returns an amplitude value of a T2 qubit measurement at a given time
    
    INPUTS:
    ##########
        x (float or array of floats): time value
        tau (float): T2 value
        amp (float): amplitude
        offset (float): The value to which the state decays
        freq (float): The frequency difference Delta
        phi (float): The T2 phase
    
    OUTPUTS: 
    #########
        float, amplitude value at specified tau
    
    '''
    
    pi = np.pi
    return amp*np.cos(2*pi*freq*x+phi)*np.exp(- (x)/tau) + offset


def noisy_T2(x, tau, amp, offset, freq, phi, noise):
    '''
    Returns a noisy amplitude value of a T2 qubit measurement at a given time
    
    INPUTS:
    #########
        x (float or array of floats): time value
        tau (float): T2 value
        amp (float): amplitude
        offset (float): The value to which the state decays
        freq (float): The frequency difference Delta
        phi (float): The T2 phase
        noise (float): Standard deviation of the Gaussian noise.
    
    OUTPUTS: 
    #########
        float, noisy amplitude value at specified tau
    
    '''
    
    genData = T2_model(x, tau, amp, offset, freq, phi)
    noise = np.random.normal(0, noise, x.size)
    return genData + noise    


def fit_T2(taus, amps, T2_guess=None):
    
    '''
    Automatically fits the parameters of a T2 qubit decay to given data.
    
    INPUTS:
    ##########
        taus (float array): set of time values
        amps (float array): set of amplitude values 
    
    OUTPUT:
    #########
        Dictionary containing fitted parameters and analytics
    
    '''
    
    ts = np.linspace(min(taus), max(taus), 10*len(taus))
    fit_curve = np.zeros(len(ts))
    
    ##Step 1: estimate frequency
    sample_rate = 1/(taus[1] - taus[0]) #compute sample rate
    N = len(taus) #The number of samples in the data
    xf = rfftfreq(N, 1 / sample_rate)
    yf = rfft(amps[0:2*len(xf)-1] )

    points_per_freq = len(xf) / (sample_rate / 2)
    target_idx = np.argmax( np.abs( yf[1:] ) ) +1
    target_freq = xf[target_idx]#target_idx/points_per_freq
    
    ##Step 2: Estimate Offset and amplitude
    target_offset = np.average(amps)
    target_amp = ( amps.max() - amps.min() )/2
    
    ##Step 4: Calculate Phi
    target_phi = 0
    
    ##Step 5: divide data by sinusoid constructed with parameters estimated so far, estimate T1
    isolated_decay = np.abs(amps - target_offset)
    pt_per_period = int(sample_rate/target_freq)
    num_periods = int(np.floor(len(isolated_decay)/pt_per_period))
    filt_decay_arr = np.split(isolated_decay[:num_periods*pt_per_period], num_periods)
    filt_decay = np.mean(filt_decay_arr, 1)
    new_time = np.linspace(taus[0], taus[-1], num_periods)
    
    try:
        [m,b] = np.polyfit(new_time[:5], np.log(filt_decay[:5]),1)
        target_tau = -1/m
    except:
        m=0
        b=0
        target_tau = 1
    if target_tau<0:
        target_tau = 1
    #plt.plot(taus, m*taus+b)
    

    tau = target_tau
    amp = target_amp
    offset = target_offset
    freq = target_freq
    phi = target_phi
    
    if T2_guess:
        tau = T2_guess
    fit_guess = [tau, amp, offset, freq, phi]

    try:
        fit_out, pcov = curve_fit(T2_model, taus, amps, p0=fit_guess)
        tau, amp, offset, freq, phi, *_ = fit_out
        fit_curve = T2_model(ts, tau, amp, offset, freq, phi)   
    except:
        print('Fit did not converge, returning zeros')
        return {'tau': tau, 'amp': amp, 'offset': offset, 'freq': freq, 'phi': phi, 'ts': ts, 
                'fit_curve': fit_curve, 'fit_guess': fit_guess}
    
    print()
    
    return {'tau': tau, 'amp': amp, 'offset': offset, 'freq': freq, 'phi': phi, 'ts': ts, 
            'fit_curve': fit_curve, 'fit_guess': fit_guess}