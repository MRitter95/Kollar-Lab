# -*- coding: utf-8 -*-
"""
Created on Thu Dec  3 18:04:20 2020

@author: Kollarlab
"""
import pyvisa
import numpy as np

class HS9000B():
    '''
    Holzworth class, currently hard coded to 2 channels.
    Attributes:
    
    settings: property that returns the settings of the submodules (channels and reference)
    ch1, ch2: channel objects with frequency, phase, power, output control
    ref: reference objet that controls the reference clock source (INT/EXT) and frequency (10/100MHz)
    
    '''
    def __init__(self, address):
        '''
        Constructor for Holzworth
        Arguments:
            address (string): pyvisa resource string (e.g. 'ASRL3::INSTR')

        '''
        self.instrument_type = 'holzworth'
        
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(address)
        #We have to explictly set the baud rate and termination because 
        #they don't match the pyvisa defaults
        self.inst.baud_rate = 115200
        self.inst.write_termination = '\n'
        self.inst.read_termination = '\n'

        self.ch1 = channel(self.inst, 1)
        self.ch2 = channel(self.inst, 2)
        self.ref = reference(self.inst)

    @property
    def settings(self):
        fullsettings = {}
        fullsettings['ch1'] = self.ch1.settings
        fullsettings['ch2'] = self.ch2.settings
        fullsettings['ref'] = self.ref.settings
    
        return fullsettings

    def reset(self):
        self.ch1.reset()
        self.ch2.reset()

    def close(self):
        self.inst.close()

class reference(object):
    def __init__(self, inst):
        self.inst = inst
        
        #strings to have around because source and frequency cannot be set separately at the bottom later
        self._source_str = 'INT'
        self._frequency_str = '100MHz'
    
        #make sure that the actual setting match the stored strings, to start with
        self.source = 'INT'
        self.frequency = 100e6
        
    @property
    def source(self):
#        print('reading ref')
        [mode, freq] = self.inst.query(':REF:STATUS?').split()
        return mode
    @source.setter
    def source(self, mode):
#        print('setting mode')
        if mode in ['INT', 'Int', 'Internal']:
            mode_str = 'INT'
            self.frequency = 100e6
        elif mode in ['EXT', 'Ext', 'External']:
            mode_str = 'EXT'
        else:
            raise ValueError('Unknown refernce source mode. Try Ext, Int')
        self.inst.query(':REF:{}:{}'.format(mode_str, self._frequency_str))
        self._source_str = mode_str
    
    @property
    def frequency(self):
#        print('reading ref(freq)')
        [mode, freq_str] = self.inst.query(':REF:STATUS?').split()
        freq = float(freq_str[:-3])*1e6
        return freq
    @frequency.setter
    def frequency(self, value):
#        print('trying to set {}'.format(value))
        value_MHz = value/1e6
        value_int = int(np.round(value_MHz,0))
        if self._source_str == 'INT':
            if not value_int== 100:
                raise ValueError('Internal reference frequency must be 100 MHz')
        elif self._source_str == 'EXT':
            if not value_int in [10,100]:
                raise ValueError('External ref freq must be 10 or 100 MHz')
        value_str = str(value_int) + 'MHz'
        self.inst.query(':REF:{}:{}'.format(self._source_str, value_str))
        self._frequency_str  = value_str
    
    @property
    def settings(self):
        fullsettings = {}
        fullsettings['source'] = self.source
        fullsettings['frequency'] = self.frequency
        return fullsettings

class channel(object):
    '''
    Channel object for Holzworth. Very similar to SCPIinst object but with tweaked syntax
    because Holzworth doesn't follow the SCPI standard...
    Behavior is pretty much the same: a dictionary of commands is defined and the keys define 
    properties of the object that are accessed (e.g,: channel.freq queries the instrument and
    channel.freq = '5GHz' sets the instrument frequency to 5 GHz)
    All interactions with the instrument happen as queries because that's just how it is
    not sure why.
    
    Attributes:
        
    ID: channel number
    inst: pyvisa handle
    props: dictionary of commands that can be set/ read from the instrument
        
        
    9-6-21 Going in to force the holzworth channel to have the same syntax (as much as possible)
    as the SGS for compatibility. Auto behavior is too persnickety.
    
    '''
    def __init__(self, inst, number):
        
        self.instrument_type = 'holzworth_channel'

        self.init = True

        self.ID = number
        self.inst = inst

        self.channel = ':CH{}'.format(self.ID)
        self.props = {}
        self.props['freq'] = ':FREQ'
        self.props['phase'] = ':PHASE'
        self.props['output'] = ':PWR:RF'
        self.props['power'] = ':PWR'
#        self.props['ext_mod_enable'] = ':MOD'
#        self.props['ext_mod'] = ':MOD:MODE'
        self.props['mod'] = ':MOD:MODE'

        self.init = False

    @property
    def settings(self):
        fullsettings = {}
        for setting in self.props:
#            fullsettings[setting] = self.__getattr__(setting)
            fullsettings[setting] =getattr(self,setting)
        return fullsettings
    
    def reset(self):
        self.inst.query(':CH{}*RST'.format(self.ID))
        self.output = 'OFF'


    @property
    def freq(self):
        'returns frequency in Hz'
        channel = self.__dict__['channel']
        writeStr = channel + ':FREQ?'
        output = self.inst.query(writeStr)
        # example '1980.00000 MHz'
        val = float(output[0:-3])*1e6
        return val
    @freq.setter
    def freq(self, val):
        '''value should be a number in Hz '''
        val_MHz = val/1e6
        val_MHz = np.round(val_MHz,9)
#        print(val_MHz)
        channel = self.__dict__['channel']
        writeStr = channel + ':FREQ:' + str(val_MHz) + 'MHz'
#        print(writeStr)
        self.inst.query(writeStr)

    @property
    def Freq(self):
        return self.freq
    @Freq.setter
    def Freq(self,val):
        self.freq = val
        
        
    @property
    def power(self):
        'returns power in dB (probably)'
        channel = self.__dict__['channel']
        writeStr = channel + ':PWR?'
        output = self.inst.query(writeStr)
        val = float(output)
        return val
    @power.setter
    def power(self,val):
        channel = self.__dict__['channel']
        writeStr = channel + ':PWR:' + str(val)
        self.inst.query(writeStr)
        
    @property
    def Power(self):
        return self.power
    @Power.setter
    def Power(self,val):
        self.power = val
        
    @property
    def phase(self):
        '  phase in degrees (probably) '
        channel = self.__dict__['channel']
        writeStr = channel + ':PHASE?'
        output = self.inst.query(writeStr)
        val = float(output)
        return val
    @phase.setter
    def phase(self,val):
        channel = self.__dict__['channel']
        if val<0:
            raise ValueError('Only positive phase angles allowed')
        val = np.round(val,1)
        writeStr = channel + ':PHASE:' + str(val)
        self.inst.query(writeStr)
        
    @property
    def Phase(self):
        return self.phase
    @Phase.setter
    def Phase(self,val):
        self.phase = val
        
        
    @property
    def output(self):
        channel = self.__dict__['channel']
        writeStr = channel + ':PWR:RF?'
        output = self.inst.query(writeStr)
        if output == 'ON':
            return 'On'
        elif output == 'OFF':
            return 'Off'
        else:
            raise ValueError('Unknown output state')
    @output.setter
    def output(self,val):
        channel = self.__dict__['channel']
        baseStr = channel + ':PWR:RF'
        if val in ['ON', 'On', 1]:
            #set the power to the desired level
            writeStr = channel + ':PWR:' + str(self.power)
            self.inst.query(writeStr)
#            print('Setting power before turning on')
            
            #turn the output on
            writeStr = baseStr + ':ON'
            self.inst.query(writeStr)
#            print('turning the output on')
            
            #set the power to the desired level again after the output is on
            writeStr = channel + ':PWR:' + str(self.power)
            self.inst.query(writeStr)
#            print('Setting power after turning on')
            
            
        elif val in ['OFF', 'Off', 0]:
            writeStr = baseStr + ':OFF'
            self.inst.query(writeStr)
        else:
            raise ValueError('invalid output setting. Should be ON, On, 1, or OFF, Off, 0')
     
    @property
    def Output(self):
        return self.output
    @Output.setter
    def Output(self,val):
        self.output = val
        
    @property
    def mod(self):
        channel = self.__dict__['channel']
        writeStr = channel + ':MOD:MODE?'
        output = self.inst.query(writeStr)
        if output == 'OFF':
            return 'Off'
        elif output == 'PULSE:EXT':
            return 'On'
        else:
            return output
    @mod.setter
    def mod(self, val):
        channel = self.__dict__['channel']
        baseStr = channel + ':MOD:MODE'
        if val in ['ON', 'On', 1]:
            writeStr = baseStr + ':PULSE:SRC:EXT'
            self.inst.query(writeStr)
        elif val in ['OFF', 'Off', 0]:
            writeStr = baseStr + ':OFF'
            self.inst.query(writeStr)
        else:
            raise ValueError('invalid output setting. Should be ON, On, 1, or OFF, Off, 0')
        
    @property
    def Mod(self):
        return self.mod
    @Mod.setter
    def Mod(self,val):
        self.mod = val
    
    def enable_pulse(self):
        self.mod = 'On'
    
    def disable_pulse(self):
        self.mod = 'Off'
    
    
#    @property
#    def triggerSlope(self):
#        activeTrigger = self.driver.Trigger.Sources[self.triggerSource]
#        temp = activeTrigger.Edge.Slope
##        self._triggerSlope = temp
#        if temp == 0:
#            val = 'Falling'
#        elif temp == 1:
#            val = 'Rising'
#        else:
#            raise ValueError("Unkown trigger slope returned")
#        self._triggerSlope = val
#        return val
#    @triggerSlope.setter
#    def triggerSlope(self,val):
#        if val == 'Falling':
#            triggerSlopeC = 0
#        elif val == 'Rising':
#            triggerSlopeC = 1
#        else:
#            raise ValueError("Edge trigger slope must be either 'Rising' or 'Falling'")
##        self._triggerSlope = triggerSlopeC
#        self._triggerSlope = val
#        activeTrigger = self.driver.Trigger.Sources[self.triggerSource]
#        activeTrigger.Edge.Slope = triggerSlopeC





#    def __getattr__(self, name):
#        '''
#        Overwriting the get attr method so that we can have the instrument
#        behave like a normal python object without having to write properties
#        or getters/setters for every single setting
#        Avoids infinite loops by invoking the standard getattr for the init 
#        phase
#        '''
#        initializing = self.__dict__['init']
#        full_dict = self.__dict__
#        if initializing or name in full_dict.keys():
#            super().__getattribute__(self, name)
#        else:
#            prop_dict = self.__dict__['props']
#            channel = self.__dict__['channel']
#            if name in prop_dict.keys():
#                val =  self.inst.query(channel+prop_dict[name]+'?')
#                try:
#                    return eval(val)
#                except:
#                    return val
#            else:
#                print('invalid command')
    
#    def __setattr__(self, name, value):
#        '''
#        Overwriting the set attribute method
#        It will behave 'normally' for the defined properties (ID etc) but
#        execute a command on the instrument for the standard operations (freq, phase
#        etc.)
#        The code at the beginning avoids infinite recursion for the very first setting (init)
#        '''
#        try:
#            initializing = self.__dict__['init']
#        except:
#            initializing = True
#        full_dict = self.__dict__
#        if initializing or name in full_dict.keys():
#            super().__setattr__(name, value)
#        else:
#            prop_dict = self.__dict__['props']
#            channel = self.__dict__['channel']
#            if name in prop_dict.keys():
#                self.inst.query(channel+prop_dict[name]+':{}'.format(value))
#            else:
#                print('setting an invalid command')
                
                
if __name__ == '__main__':
    
    try:
        holzworth.close()
    except:
        pass
    hardwareAddress = 'ASRL7::INSTR'
    holzworth = HS9000B(hardwareAddress)
    
    
#    #frequency, lower case
#    f1 = holzworth.ch1.freq
#    print(str(f1/1e9))
#
##    holzworth.ch1.freq = 1e9
#    holzworth.ch1.freq = (3.2e9 + np.random.rand()*100e6)
#    f2 = holzworth.ch1.freq
#    print(str(f2/1e9))
    
#    #frequency, upper case
#    f1 = holzworth.ch1.Freq
#    print(str(f1/1e9))
#
##    holzworth.ch1.freq = 1e9
#    holzworth.ch1.Freq = (3.2e9 + np.random.rand()*100e6)
#    f2 = holzworth.ch1.Freq
#    print(str(f2/1e9))
    
#    #power, lower case
#    p1 = holzworth.ch1.power
#    print(str(p1))
#
#    holzworth.ch1.power = (-3.2+ np.random.rand()*1)
#    p2 = holzworth.ch1.power
#    print(str(p2))
    
#    #phase, lower case
#    p1 = holzworth.ch1.phase
#    print(str(p1))
#
##    holzworth.ch1.phase = (6)
#    holzworth.ch1.phase = (23.2+ np.random.rand()*1)
#    p2 = holzworth.ch1.phase
#    print(str(p2))
    
#    #phase, upper case
#    p1 = holzworth.ch1.Phase
#    print(str(p1))
#
##    holzworth.ch1.Phase = (6)
#    holzworth.ch1.Phase = (23.2+ np.random.rand()*1)
#    p2 = holzworth.ch1.Phase
#    print(str(p2))
    
#    #output, lower case
#    out = holzworth.ch1.output
#    print(out)
#    
#    holzworth.ch1.output = 'OFF'
#    out = holzworth.ch1.output
#    print(out)
#    
#    holzworth.ch1.output = 'On'
#    out = holzworth.ch1.output
#    print(out)
#    
#    holzworth.ch1.output = 0
#    out = holzworth.ch1.output
#    print(out)
    
#    #output, upper case
#    out = holzworth.ch1.Output
#    print(out)
#    
#    holzworth.ch1.Output = 'OFF'
#    out = holzworth.ch1.Output
#    print(out)
#    
#    holzworth.ch1.Output = 'On'
#    out = holzworth.ch1.Output
#    print(out)
#    
#    holzworth.ch1.Output = 0
#    out = holzworth.ch1.Output
#    print(out)
    
#    #mod, lower case
#    out = holzworth.ch1.mod
#    print(out)
#    
#    holzworth.ch1.mod = 'OFF'
#    out = holzworth.ch1.mod
#    print(out)
#    
#    holzworth.ch1.mod = 'On'
#    out = holzworth.ch1.mod
#    print(out)
#    
#    holzworth.ch1.mod = 0
#    out = holzworth.ch1.mod
#    print(out)
#    
    
    #mod, upper case
    out = holzworth.ch1.Mod
    print(out)
    
    holzworth.ch1.Mod = 'OFF'
    out = holzworth.ch1.Mod
    print(out)
    
    holzworth.ch1.Mod = 'On'
    out = holzworth.ch1.Mod
    print(out)
    
    holzworth.ch1.Mod = 0
    out = holzworth.ch1.Mod
    print(out)
    
    
    
    
    
    




                