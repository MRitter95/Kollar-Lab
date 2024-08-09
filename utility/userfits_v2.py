import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.signal import periodogram

def T1_model(t_ax, amp, offset, tau):
    '''
    T1_model _summary_

    :param t_ax: _description_
    :type t_ax: _type_
    :param amp: _description_
    :type amp: _type_
    :param offset: _description_
    :type offset: _type_
    :param tau: _description_
    :type tau: _type_
    :return: _description_
    :rtype: _type_
    '''    
    return np.exp(-t_ax/tau)*amp+offset

def T2_model(t_ax, amp, offset, tau, freq, phi):
    '''
    T2_model _summary_

    :param t_ax: _description_
    :type t_ax: _type_
    :param amp: _description_
    :type amp: _type_
    :param offset: _description_
    :type offset: _type_
    :param tau: _description_
    :type tau: _type_
    :param freq: _description_
    :type freq: _type_
    :param phi: _description_
    :type phi: _type_
    :return: _description_
    :rtype: _type_
    '''    
    return amp*np.cos(2*np.pi*freq*t_ax+phi)*np.exp(-t_ax/tau)+offset

def cos_model(t_ax, amp, offset, freq, phi):
    '''
    cos_model _summary_

    :param t_ax: _description_
    :type t_ax: _type_
    :param amp: _description_
    :type amp: _type_
    :param offset: _description_
    :type offset: _type_
    :param freq: _description_
    :type freq: _type_
    :param phi: _description_
    :type phi: _type_
    :return: _description_
    :rtype: _type_
    '''    
    return amp*np.cos(2*np.pi*t_ax*freq+phi)+offset

def gaussian_model(f_ax, amp, offset, center, sigma):
    '''
    gaussian_model _summary_

    :param f_ax: _description_
    :type f_ax: _type_
    :param amp: _description_
    :type amp: _type_
    :param offset: _description_
    :type offset: _type_
    :param center: _description_
    :type center: _type_
    :param sigma: _description_
    :type sigma: _type_
    :return: _description_
    :rtype: _type_
    '''    
    exponent = -(f_ax-center)**2/(2*sigma**2)
    return offset+amp/(sigma*np.sqrt(2*np.pi))*np.exp(exponent)

def lorenztian_model(f_ax, amp, offset, center, sigma):
    '''
    lorenztian_model _summary_

    :param f_ax: _description_
    :type f_ax: _type_
    :param amp: _description_
    :type amp: _type_
    :param offset: _description_
    :type offset: _type_
    :param center: _description_
    :type center: _type_
    :param sigma: _description_
    :type sigma: _type_
    :return: _description_
    :rtype: _type_
    '''    
    return offset+amp/np.pi*(sigma/((f_ax-center)**2+sigma**2))

def T1_guess(t_ax, amps, plot=False):
    '''
    T1_guess _summary_

    :param t_ax: _description_
    :type t_ax: _type_
    :param amps: _description_
    :type amps: _type_
    :param plot: _description_, defaults to False
    :type plot: bool, optional
    :return: _description_
    :rtype: _type_
    '''    
    #Amplitude guess
    amp_guess = amps[0]-amps[-1]
    #Offset guess
    off_guess = np.mean(amps[-10:])
    #Time constant guess
    tau_max = 5*t_ax[-1]
    lin_range = int(len(amps)/5)
    norm_amps = (amps-off_guess)/amp_guess
    m,b = np.polyfit(t_ax[:lin_range], np.log(norm_amps[:lin_range]),1)
    if plot:
        plt.plot(t_ax, np.log(norm_amps))
        plt.plot(t_ax, m*t_ax+b)
    tau_guess = -1./m
    if tau_guess<0 or tau_guess>tau_max:
        tau_guess = tau_max
    
    return [amp_guess, off_guess, tau_guess]

def cos_guess(t_ax, amps, plot=False):
    '''
    cos_guess _summary_

    :param t_ax: _description_
    :type t_ax: _type_
    :param amps: _description_
    :type amps: _type_
    :param plot: _description_, defaults to False
    :type plot: bool, optional
    :return: _description_
    :rtype: _type_
    '''    
    #Amplitude guess
    amp_guess = (max(amps)-min(amps))/2
    #Offset guess
    off_guess = np.mean(amps)
    #Frequency guess
    fs = 1./np.mean(np.diff(t_ax))
    freq, fft = periodogram(amps, fs)
    freq_guess = freq[np.argmax(fft[1:])+1]
    #Phase guess
    max_contrast = max(abs(amps))-off_guess
    init_amp = max(-1,min((amps[0]-off_guess)/max_contrast,1))
    init_slope = amps[1]-amps[0]
    try:
        phi_guess = np.arccos(init_amp)
    except:
        print('Phi guess out of range')
        phi_guess = 0
    print(init_amp)
    print(max_contrast)
    phi_guess = 0
    if init_slope>0:
        phi_guess+=np.pi

    return [amp_guess, off_guess, freq_guess, phi_guess]

def T2_guess(t_ax, amps, plot=False):
    '''
    T2_guess _summary_

    :param t_ax: _description_
    :type t_ax: _type_
    :param amps: _description_
    :type amps: _type_
    :param plot: _description_, defaults to False
    :type plot: bool, optional
    :return: _description_
    :rtype: _type_
    '''    
    
    [amp_guess, off_guess, freq_guess, phi_guess] = cos_guess(t_ax, amps)
    fs = 1./np.mean(np.diff(t_ax))
    #Tau guess
    tau_max = 5*t_ax[-1]
    norm = np.abs(amps-off_guess)
    pt_per_period = int(fs/freq_guess)
    #Average out the oscillations but dividing the array into chunks that
    #are roughly a period before taking the mean
    num_periods = int(np.floor(len(norm)/pt_per_period))
    filtered_data = np.split(norm[:num_periods*pt_per_period], num_periods)
    envelope = np.mean(filtered_data, 1)
    new_time = np.linspace(t_ax[0], t_ax[-1], num_periods)
    
    try:
        [m,b] = np.polyfit(new_time[:5], np.log(envelope[:5]),1)
        tau_guess = -1/m
        if tau_guess<0:
            tau_guess = tau_max
    except:
        tau_guess = tau_max

    if plot:
        plt.plot(t_ax, envelope)

    return [amp_guess, off_guess, tau_guess, freq_guess, phi_guess]

def peak_guess(f_ax, amps):
    '''
    peak_guess _summary_

    :param f_ax: _description_
    :type f_ax: _type_
    :param amps: _description_
    :type amps: _type_
    :return: _description_
    :rtype: _type_
    '''    
    #check if we have a hanger vs a peak type feature
    edge = np.mean(amps[:5])
    min_val = min(amps)
    max_val = max(amps)
    if edge-min_val>max_val-edge:
        #print('hanger?')
        amps = abs(amps-max(amps))
        #If we have a hanger, we know that the amplitude should be negative and 
        #we have a positive offset
        flip = -1
        add_off = 1
    else:
        #print('Normal?')
        #Don't flip the amplitude and add 0 to the offset
        flip = 1
        add_off = 0
    center_ind = np.argmax(amps)
    center_guess = f_ax[center_ind]
    #find the larger fraction of the data to calculate HWHM
    start_ind = 0
    stop_ind = center_ind
    left_peak = False
    if center_ind<len(amps)/2:
        start_ind = center_ind
        stop_ind = -1
        left_peak = True
    hwhm_ind = np.argmin(abs(amps[center_ind]/2-amps[start_ind:stop_ind]))+start_ind
    #print(hwhm_ind)
    #plt.plot(f_ax, amps)
    #plt.plot(f_ax[start_ind:stop_ind], amps[start_ind:stop_ind])
    #plt.hlines(amps[center_ind]/2,f_ax[0], f_ax[-1])
    sigma_guess = abs(center_guess-f_ax[hwhm_ind])
    if left_peak:
        offset_guess = np.mean(amps[-int(center_ind/4):])
    else:
        offset_guess = np.mean(amps[0:int(center_ind/4)])
    amp_guess = max(amps)-offset_guess
    scaled_amp = amp_guess
    return [scaled_amp*flip, offset_guess+add_off*edge, center_guess, sigma_guess]

def gaussian_guess(f_ax, amps):
    '''
    gaussian_guess _summary_

    :param f_ax: _description_
    :type f_ax: _type_
    :param amps: _description_
    :type amps: _type_
    :return: _description_
    :rtype: _type_
    '''    
    [amp, offset, center, sigma] = peak_guess(f_ax, amps)
    sigma = sigma/np.sqrt(2*np.log(2))
    amp_scale = amp*np.sqrt(2*np.pi)*sigma
    return [amp_scale, offset, center, sigma]

def lorenztian_guess(f_ax, amps):
    '''
    lorenztian_guess _summary_

    :param f_ax: _description_
    :type f_ax: _type_
    :param amps: _description_
    :type amps: _type_
    :return: _description_
    :rtype: _type_
    '''    
    [amp, offset, center, sigma] = peak_guess(f_ax, amps)
    amp_scale = amp*np.pi*sigma
    return [amp_scale, offset, center, sigma]

def create_param_dict(names, vals):
    '''
    create_param_dict _summary_

    :param names: _description_
    :type names: _type_
    :param vals: _description_
    :type vals: _type_
    :return: _description_
    :rtype: _type_
    '''    
    params = {}
    for name, val in zip(names, vals):
        params[name] = val
    return params

def convert_prefix(string, val):
    '''
    convert_prefix _summary_

    :param string: _description_
    :type string: _type_
    :param val: _description_
    :type val: _type_
    :return: _description_
    :rtype: _type_
    '''    
    SI = {
        'n':1e-9,
        'u':1e-6,
        'm':1e-3,
        '':1,
        'k':1e3,
        'M':1e6,
        'G':1e9
    }
    prefix = string[0]
    return val/SI[prefix]

def fit_model(t_ax, amps, model, plot=False, guess=None, ax=None):
    '''
    fit_model _summary_

    :param t_ax: _description_
    :type t_ax: _type_
    :param amps: _description_
    :type amps: _type_
    :param model: _description_
    :type model: _type_
    :param plot: _description_, defaults to False
    :type plot: bool, optional
    :param guess: _description_, defaults to None
    :type guess: _type_, optional
    :param ax: _description_, defaults to None
    :type ax: _type_, optional
    :return: _description_
    :rtype: _type_
    '''    
    xlabel = 'Time (us)'
    scale = 1e-6
    if model=='T1':
        fit_func = T1_model
        guess_func = T1_guess
        params = ['amp', 'offset', 'tau']
        key_params = ['tau']
        units = ['us']
    elif model=='T2':
        fit_func = T2_model
        guess_func = T2_guess
        params = ['amp', 'offset', 'tau', 'freq', 'phi']
        key_params = ['tau', 'freq']
        units = ['us', 'MHz']
    elif model=='cos':
        fit_func = cos_model
        guess_func = cos_guess
        params = ['amp', 'offset', 'freq', 'phi']
        key_params = ['freq']
        units = ['MHz']
    elif model=='gauss':
        fit_func = gaussian_model
        guess_func = gaussian_guess
        params = ['amp', 'offset', 'center', 'sigma']
        key_params = ['center', 'sigma']
        units = ['GHz', 'MHz']
        xlabel = 'Freq (GHz)'
        scale = 1e9
    elif model=='lorenz':
        fit_func = lorenztian_model
        guess_func = lorenztian_guess
        params = ['amp', 'offset', 'center', 'sigma']
        key_params = ['center', 'sigma']
        units = ['GHz', 'MHz']
        xlabel = 'Freq (GHz)'
        scale = 1e9
    else:
        print('{} is not yet implemented'.format(model))
        return {}
    
    if not guess:
        guess = guess_func(t_ax, amps) 
        
    fit_params, pcov = curve_fit(fit_func, t_ax, amps, guess)

    t_ax_fit = np.linspace(t_ax[0], t_ax[-1], len(t_ax)*10)
    param_dict = create_param_dict(params, fit_params)
    if plot:
        if not ax:
            plt.figure()
            ax = plt.subplot(111)
        ax.plot(t_ax/scale, amps, label='Data')
        ax.plot(t_ax_fit/scale, fit_func(t_ax_fit, *guess), label='Init guess')
        ax.plot(t_ax_fit/scale, fit_func(t_ax_fit, *fit_params), label='Best Fit')
        base_string = 'Fit results, model:{}'.format(model)
        for p,u in zip(key_params, units):
            param_val = convert_prefix(u,param_dict[p])
            base_string+=',{}:{:.5f}{}'.format(p, param_val,u)
        ax.set_title(base_string)
        ax.legend()
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Amp (arb)')
    
    return param_dict
        
    

