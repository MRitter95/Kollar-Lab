
import pyvisa

class Module(object):
    '''
    Module is a class that holds a collection of scpi commands/ properties. It
    overwrites the standard getattr and setattr object functions to replace them
    with a SCPI function call. Currently it does not allow for submodules but
    this could be implemented in the future. TO DO: add recursive option for modules, 
    add general mapping from instrument return value to "useful" value (cast 0/1 
    to "On"/"Off" for example), add bound checking for settings like frequency
    Properties:
        inst: handle to SCPI inst object where all the commands get sent
        commands: dictionary of the SCPI command strings and "key", i.e. properties
        the can be queried by the user
        errcmd: dictionnary holding the error command (or commands for some instruments)
        to perform error checking after applying a setting
    '''
    def __init__(self,inst, commands, errcmd):
        self.init = True
        
        self.inst = inst
        self.commandset = commands
        self.errcmd = errcmd
        self.modules = []
        self.init = False
        
    def __getattr__(self, name):
        '''
        Wrapper for reading value from the instrument. We have to do some shenanigans
        because we need to distinguish between the instrument properties (like voltage, 
        frequency etc.) and software properties (like submodules, commandset etc.). The
        normal use case for this is: instrument.property is called in the control code
        which then leads to this function where the appropriate SCPI function call is
        read out of the commandset dictionnary. The property is queried then returned to
        the user. 
        '''
        initializing = self.__dict__['init']
        full_dict = self.__dict__
        #Checking if the property is a SW property instead of a HW property
        if initializing or name in full_dict.keys():
            super().__getattribute__(self, name)
        else:
            #We cast all variables and settings to lower case to avoid problems with case
            name = name.lower()
            cmds = self.__dict__['commandset']
            for k in cmds.keys():
                if name == k.lower():
                    if isinstance(cmds[k], list):
                        #Hack to recast enum type return values to a useful text
                        val = self.inst.query(cmds[k][0]+'?').rstrip()
                        try:
                            val = eval(val)
                            strings = cmds[k][1]
                            return strings[val]
                        except:
                            return val
                    else:
                        val = self.inst.query(cmds[k]+'?').rstrip()
                        #Converts numbers in strings to regular numbers (e.g '5000000' to 5e6)
                        try:
                            return eval(val)
                        except:
                            return val
            #We have to add this so that spyder doesn't complain that we've overwritten all the 
            #object specific functions it likes to call (like size etc.). These properties aren't 
            #used at all
            super().__getattribute__(name)
            print('Trying to get an invalid command: {}'.format(name))
    
    def __setattr__(self, name, value):
        '''
        Overwrites the setattr method so that we can intercept calls like: instrument.setting=value
        As with the getattr function, we find the appropriate SCPI function call, check the valid
        settings and apply them to the instrument. Every setting is accompanied by an error check
        which simply calls the error command and returns the error code if it's not zero. Again, 
        we have to distinguish between hardware and software settings as the SW settings need to 
        behave like normal object settings
        '''
        #Checking if we are in initialization mode and if the setting is one of the SW properties
        try:
            initializing = self.__dict__['init']
        except:
            initializing = True
        full_dict = self.__dict__
        if initializing or name in full_dict.keys():
            super().__setattr__(name, value)
        
        else:
            #Made our properties case insensitive
            name = name.lower()
            cmds = {}
            try:
                cmds = self.__dict__['commandset']
            except:
                pass 
            
            for k in cmds.keys():
                if name == k.lower():
                    setting = cmds[k]
                    if isinstance(setting, list):
                        command = setting[0]
                        # Check that input value/ string is a valid option and print options if not
                        try:
                            value = setting[1].inverse[value]
                        except:
                            print('Invalid input, valid options are: {}'.format(list(setting[1].inverse.keys())))
                    else:
                        command = setting
                    cmd = '{} {}'.format(command, value)
                    self.inst.write(cmd)
                    self.inst.write('*OPC')
                    self.error
                    return

            print('Trying to set an invalid setting: {}'.format(name))
            
    @property
    def error(self):
        errcmd = self.__dict__['errcmd']
        if isinstance(errcmd, dict):
            for errtype in errcmd.keys():
                code = 0
                string = {}
                error_struct = errcmd[errtype]
                if isinstance(error_struct, list):
                    errorstring = self.inst.query(errcmd[errtype][0])
                    errstr = errcmd[errtype][1]
                else:
                    errorstring = self.inst.query(errcmd[errtype])
                try:
                    (code, string) = eval(errorstring)
                except:
                    code = eval(errorstring)
                    string = errstr[code]
                if code != 0:
                    print('{}:{},{}'.format(errtype, code, string))
        else:
            (code, string) = eval(self.inst.query(errcmd))
            if code != 0:
                print('{},{}'.format(code, string))
        self.inst.write('*CLS')
        return code, string
    
    @property
    def settings(self):
        '''
        Collect all the settings inside the module and loops through all other modules
        to accumulate their settings in subdictionnaries. 
        '''
        fullsettings = {}
        for setting in self.commandset:
            fullsettings[setting] = self.__getattr__(setting)
        for module in self.modules:
            fullsettings[module] = {}
            mod = getattr(self, module)
            fullsettings[module] = mod.settings
        return fullsettings
    
    @settings.setter
    def settings(self, fullsettings):
        for setting in fullsettings.keys():
            if not isinstance(fullsettings[setting], dict):
                self.__setattr__(setting, fullsettings[setting])
            else:
                try:
                    mod = getattr(self, setting)
                    mod.settings = fullsettings[setting]
                except:
                    print('invalid')

class SCPIinst(Module):
    '''
    Base class for all single channel instruments that use the SCPI standard. The idea is that the user
    can specify the basic commands for each property of the instrument in a dictionary and structure the
    property "chunks" into submodules. The base case usage is: instrument.setting (where setting is a prop)
    For example, an SGS might have a set of settings relating to the reference clock (internal/ external, 
    freq etc.), by making a subdictionary in the main "commandset" dictionary this code will create 
    submodules that can be accessed as SGS.submodule.property
    Properties:
        address: the VISA address of the instrument
        commands: the dictionary holding all the SCPI commands for the properties of the instrument. Can
        include subdictionaries if submodules are a natural description of the instrument
        errcmd: dictionary holding the basic error checking commands for the instrument
        reset: boolean flag that sets whether the reset command is sent to the device, default: True
        baud_rate: baud_rate for USB/ serial connections, defaults to 115200
    '''
    def __init__(self, address, commands, errcmd, reset = True, baud_rate=115200):
        
        self.init = True
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(address)
        try:
            self.inst.baud_rate = baud_rate
        except:
            pass
        if reset:
            self.inst.write('*RST; *CLS')
        self.errcmd = errcmd
        self.modules = []
        for key in commands.keys():
            if key == 'core':
                self.commandset = commands['core']
            elif isinstance(commands[key],dict):
                setattr(self,key,Module(self.inst, commands[key], errcmd))
                self.modules.append(key)
        
        self.init = False
            
    def reset(self):
        '''
        Calls the standard SCPI reset and clear commands ('*RST' and '*CLS'). 
        This function can be overwritten if the instrument does not follow the standard. 
        '''
        self.inst.write('*RST; *CLS')
        
    def close(self):
        '''
        Closes the connection to the instrument (using the pyvisa.inst close method)
        '''
        self.inst.close()