#import visa
import pyvisa

class RFgen():

    def __init__(self, address):
#        rm=visa.ResourceManager()
        rm=pyvisa.ResourceManager()
        self.inst=rm.open_resource(address)
        self.inst.write('*RST')

    @property
    def settings(self):
        return {}
    @settings.setter
    def settings(self, fullsettings):
        print('Tried to set SGS settings')

    def set_Amp_V(self,amp):
        self.inst.write('SOURce:POWer {} V'.format(amp))
        
    def set_Amp(self,amp):
        #set power in dB
        self.inst.write('SOURce:POWer {}'.format(amp))

    def set_Freq(self,freq):
        self.inst.write('SOURce:FREQuency:CW {} GHz'.format(freq))
        
    def set_Offset(self, offset):
        self.inst.write('SOURce:FREQuency:OFFSet {} MHz'.format(offset))
        
    def set_External_Reference(self, freq=10):
        self.inst.write(':SOURce:ROSCillator:SOURce EXTernal')
        self.inst.write(':SOURce:ROSCillator:EXTernal:FREQuency {} MHz'.format(freq))
        
    def set_Internal_Reference(self):
        self.inst.write(':SOURce:ROSCillator:SOURce Internal')
        
    def set_External_LO(self):
        self.inst.write(':SOURce:LOSCillator:SOURce EXTernal')
    
    def set_Internal_LO(self):
        self.inst.write(':SOURce:LOSCillator:SOURce INTernal')
    
    def set_RefLO_output(self, output = 'Ref', freq = 10):
        self.inst.write(':CONNector:REFLo:OUTPut {}'.format(output))
        if output == 'Ref':
            self.inst.write(':SOURce:ROSCillator:OUTPut:FREQuency {} MHz'.format(freq))
        
    def set_Phase(self, phase):
        #degrees
        self.inst.write(':SOURce:PHASe {}'.format(phase))
        
        
    def power_On(self):
        self.inst.write(':OUTPut:STATe ON')
        
    def power_Off(self):
        self.inst.write(':OUTPut:STATe OFF')
        
        
    def mod_On(self):
        self.inst.write(':SOURce:IQ:STATe ON')
        
    def mod_Off(self):
        self.inst.write(':SOURce:IQ:STATe OFF')
        
        

    def send_cmd(self,cmd):
        self.inst.write(cmd)

    def query(self,cmd):
        print(self.inst.query(cmd))

#    def run(self):
#        self.inst.write('OUTPut:STATe ON')