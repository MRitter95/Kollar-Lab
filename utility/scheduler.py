import numpy as np
import matplotlib.pyplot as plt

def gaussian(sample_rate, amp, sigma, num_sigma):
    '''
    gaussian _summary_

    :param sample_rate: _description_
    :type sample_rate: _type_
    :param amp: _description_
    :type amp: _type_
    :param sigma: _description_
    :type sigma: _type_
    :param num_sigma: _description_
    :type num_sigma: _type_
    :return: _description_
    :rtype: _type_
    '''

    samples = int(sigma*num_sigma*sample_rate)
    t = np.linspace(0,sigma*num_sigma, samples)
    t0 = num_sigma*sigma/2
    wave = np.exp(-(t-t0)**2/(2*sigma**2))
    offset = wave[0]
    init_amp = max(wave)
    wave = (wave-offset)/(init_amp-offset)
    return wave*amp

def gaussian_square(sample_rate, amp, length, num_sigma, ramp_sigma):
    '''
    gaussian_square _summary_

    :param sample_rate: _description_
    :type sample_rate: _type_
    :param amp: _description_
    :type amp: _type_
    :param length: _description_
    :type length: _type_
    :param num_sigma: _description_
    :type num_sigma: _type_
    :param ramp_sigma: _description_
    :type ramp_sigma: _type_
    :return: _description_
    :rtype: _type_
    '''

    ramp = gaussian(sample_rate, amp, ramp_sigma, num_sigma)
    square = np.ones(int(length*sample_rate))*amp
    ramp_up, ramp_down = np.split(ramp, 2)
    final = np.concatenate((ramp_up, square, ramp_down))
    return final
       
class AnalogChannel():
    '''
    AnalogChannel _summary_
    '''    
    def __init__(self, chanID, sample_rate, samples, name='waveform'):
        '''
        __init__ _summary_

        :param chanID: _description_
        :type chanID: _type_
        :param sample_rate: _description_
        :type sample_rate: _type_
        :param samples: _description_
        :type samples: _type_
        :param name: _description_, defaults to 'waveform'
        :type name: str, optional
        '''

        self.ID = chanID
        self.sample_rate = sample_rate
        self.samples = samples
        self.time_array = samples/sample_rate
        self.wave_array = np.zeros(samples)
        self.name = name
    
    def add_pulse(self, type, position, amplitude=1, **keyargs):
        '''
        add_pulse _summary_

        :param type: _description_
        :type type: _type_
        :param position: _description_
        :type position: _type_
        :param amplitude: _description_, defaults to 1
        :type amplitude: int, optional
        '''        
        if type=='gaussian':
            sigma = keyargs['sigma']
            num_sigma = keyargs['num_sigma']
            pulse = gaussian(self.sample_rate, amplitude, sigma, num_sigma)
            pos_index = int(position*self.sample_rate)
            self.wave_array[pos_index:pos_index+len(pulse)] = pulse
        if type=='gaussian_square':
            ramp_sigma = keyargs['ramp_sigma']
            num_sigma  = keyargs['num_sigma']
            length = keyargs['length']
            pulse = gaussian_square(self.sample_rate, amplitude, length, num_sigma, ramp_sigma)
            pos_index = int(position*self.sample_rate)
            self.wave_array[pos_index:pos_index+len(pulse)] = pulse
        if type=='custom':
            pos_index = int(position*self.sample_rate)
            wave_data = keyargs['wave']
            self.wave_array[pos_index:pos_index+len(wave_data)] = amplitude*wave_data
            
    def reset(self):
        '''
        reset _summary_
        '''        
        self.wave_array = np.zeros(self.samples)
            

class DigitalChannel():
    '''
    DigitalChannel _summary_
    '''    
    def __init__(self, chanID, sample_rate, samples, name='marker', HW_offset_on=0, HW_offset_off=0, polarity='Pos'):
        '''
        __init__ _summary_

        :param chanID: _description_
        :type chanID: _type_
        :param sample_rate: _description_
        :type sample_rate: _type_
        :param samples: _description_
        :type samples: _type_
        :param name: _description_, defaults to 'marker'
        :type name: str, optional
        :param HW_offset_on: _description_, defaults to 0
        :type HW_offset_on: int, optional
        :param HW_offset_off: _description_, defaults to 0
        :type HW_offset_off: int, optional
        :param polarity: _description_, defaults to 'Pos'
        :type polarity: str, optional
        '''

        self.ID = chanID
        self.polarity = polarity
        self.sample_rate = sample_rate
        self.samples = samples
        if polarity=='Pos':
            self.marker_array = np.zeros(samples)
        elif polarity=='Neg':
            self.marker_array = np.ones(samples)*chanID
        else:
            print("Acceptable polarity is 'Neg' or 'Pos'")
        self.polarity = polarity
        self.HW_offset_on  = HW_offset_on
        self.HW_offset_off = HW_offset_off
        self.name = name
        self.window_list = []

    def add_window(self, start, stop):
        '''
        add_window _summary_

        :param start: _description_
        :type start: _type_
        :param stop: _description_
        :type stop: _type_
        '''        
        self.window_list.append([start, stop])
    
    def compile_channel(self):
        '''
        compile_channel _summary_
        '''        
        for window in self.window_list:
            start_ind  = int(window[0]*self.sample_rate)
            stop_ind   = int(window[1]*self.sample_rate)
            offset_on  = int(self.HW_offset_on*self.sample_rate)
            offset_off = int(self.HW_offset_off*self.sample_rate)
            if self.polarity=='Pos':
                self.marker_array[start_ind-offset_on:stop_ind+offset_off] = self.ID
            if self.polarity=='Neg':
                self.marker_array[start_ind-offset_on:stop_ind+offset_off] = 0
    
    def reset(self, polarity=None):
        '''
        reset _summary_

        :param polarity: _description_, defaults to None
        :type polarity: _type_, optional
        '''        
        if not polarity:
            polarity = self.polarity
        if polarity=='Pos':
            self.marker_array = np.zeros(self.samples)
        elif polarity=='Neg':
            self.marker_array = np.ones(self.samples)*self.chanID
        self.window_list = []

class scheduler():
    '''
    scheduler _summary_
    '''    
    def __init__(self, total_time, num_dig_channels=0, num_analog_channels=0, sample_rate=2.4e9):
        '''
        __init__ _summary_

        :param total_time: _description_
        :type total_time: _type_
        :param num_dig_channels: _description_, defaults to 0
        :type num_dig_channels: int, optional
        :param num_analog_channels: _description_, defaults to 0
        :type num_analog_channels: int, optional
        :param sample_rate: _description_, defaults to 2.4e9
        :type sample_rate: _type_, optional
        '''        
        self.sample_rate = sample_rate
        self.total_time = total_time
        samples = int(total_time*sample_rate)
        if samples%32!=0:
            print('Warning, waveform lengths not a multiple of 32, padding to match AWG reqs')
            samples = np.ceil(samples/32)*32
        self.samples = int(samples)
        self.time_array = np.linspace(0, total_time, self.samples)
        self.analog_channels = {}
        self.digital_channels = {}
        for chan in range(num_analog_channels):
            self.add_analog_channel(chan+1)
        for chan in range(num_dig_channels):
            self.add_digital_channel(chan+1)

    def add_analog_channel(self, HW_ID, name='waveform{}'):
        '''
        add_analog_channel _summary_

        :param HW_ID: _description_
        :type HW_ID: _type_
        :param name: _description_, defaults to 'waveform{}'
        :type name: str, optional
        '''        
        sample_rate = self.sample_rate
        samples = self.samples
        name = name.format(HW_ID)
        self.analog_channels[name] = AnalogChannel(HW_ID, sample_rate, samples, name)
    
    def add_digital_channel(self, HW_ID, name='marker{}', polarity='Pos', HW_offset_on=0, HW_offset_off=0):
        '''
        add_digital_channel _summary_

        :param HW_ID: _description_
        :type HW_ID: _type_
        :param name: _description_, defaults to 'marker{}'
        :type name: str, optional
        :param polarity: _description_, defaults to 'Pos'
        :type polarity: str, optional
        :param HW_offset_on: _description_, defaults to 0
        :type HW_offset_on: int, optional
        :param HW_offset_off: _description_, defaults to 0
        :type HW_offset_off: int, optional
        '''        
        
        sample_rate = self.sample_rate
        samples = self.samples
        name = name.format(HW_ID)
        self.digital_channels[name] = DigitalChannel(HW_ID, sample_rate, samples, name, HW_offset_on, HW_offset_off, polarity)

    def compile_schedule(self, AWG_type='HDAWG', analog_list=[], digital_list=[]):
        '''
        compile_schedule _summary_

        :param AWG_type: _description_, defaults to 'HDAWG'
        :type AWG_type: str, optional
        :param analog_list: _description_, defaults to []
        :type analog_list: list, optional
        :param digital_list: _description_, defaults to []
        :type digital_list: list, optional
        :return: _description_
        :rtype: _type_
        '''        
        
        if AWG_type=='HDAWG':
            if digital_list:
                mark1 = self.digital_channels[digital_list[0]]
                mark2 = self.digital_channels[digital_list[1]]
                mark1.compile_channel()
                mark2.compile_channel()
                final_markers = mark1.marker_array + mark2.marker_array
            else:
                print('No markers provided, using blank array')
                final_markers = np.zeros(self.samples)
            if analog_list:
                analog1 = self.analog_channels[analog_list[0]].wave_array
                analog2 = self.analog_channels[analog_list[1]].wave_array
            else:
                print('No analog wf provided, using blank array')
                analog1 = np.zeros(self.samples)
                analog2 = np.zeros(self.samples)
            return [analog1, analog2, final_markers]
        else:
            print('Not implemented')

    def plot_waveforms(self):
        '''
        plot_waveforms _summary_
        '''        
        
        analog_traces = len(self.analog_channels)
        digital_traces = len(self.digital_channels)
        num_traces = analog_traces+digital_traces
        fig = plt.figure(111, figsize=(10,8))
        plt.clf()
        ax_a = plt.subplot(211)
        ax_a.set_title('Analog Traces')
        ax_a.set_xlabel('Time (us)')
        ax_a.set_ylabel('Amp')
        ax_b = plt.subplot(212, sharex=ax_a)
        ax_b.set_title('Digital Traces')
        ax_b.set_xlabel('Time (us)')
        ax_b.set_ylabel('Amp')
        for a,b in zip(self.analog_channels.keys(), self.digital_channels.keys()):
            active_channel = self.analog_channels[a]
            wave_data = active_channel.wave_array
            time_data = self.time_array*1e6
            ax_a.plot(time_data, wave_data,label=a)
            active_channel = self.digital_channels[b]
            active_channel.compile_channel()
            wave_data = active_channel.marker_array
            time_data = self.time_array*1e6
            ax_b.plot(time_data, wave_data, label=b)
        ax_a.legend()
        ax_b.legend()
        # for i, key in enumerate(self.analog_channels.keys()):
        #     if i==0:
        #         ax1 = plt.subplot(num_traces, 1, i+1)
        #         ax = ax1
        #     else:
        #         ax = plt.subplot(num_traces, 1, i+1, sharex=ax1)
        #     active_channel = self.analog_channels[key]
        #     wave_data = active_channel.wave_array
        #     time_data = self.time_array*1e6
        #     ax.plot(time_data, wave_data)
        #     ax.set_title(key)
        #     ax.set_xlabel('Time (us)')
        #     ax.set_ylabel('Amp')

        # for i, key in enumerate(self.digital_channels.keys()):
        #     ax = plt.subplot(num_traces, 1, i+analog_traces+1, sharex=ax1)
        #     active_channel = self.digital_channels[key]
        #     active_channel.compile_channel()
        #     marker_data = active_channel.marker_array
        #     time_data = self.time_array*1e6
        #     ax.plot(time_data, marker_data)
        #     ax.set_title(key)
        #     ax.set_xlabel('Time (us)')
        #     ax.set_ylabel('Amp')

#        fig.canvas.draw()
#        fig.canvas.flush_events()
    
    def reset(self):
        '''
        reset _summary_
        '''        
        for chan in self.analog_channels.values():
            chan.reset()
        for chan in self.digital_channels.values():
            chan.reset()
