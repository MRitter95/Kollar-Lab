# -*- coding: utf-8 -*-
"""
Created on Tue Sep  8 17:10:29 2020

@author: Kollarlab
"""


from .SCPIinst import SCPIinst
from bidict import bidict
import numpy as np
import time


class DC205(SCPIinst):
    '''
    :no-index:
    DC205 _summary_
    :param SCPIinst: _description_
    :type SCPIinst: _type_
    '''    
    
    LEXE = bidict({
            0:'No exec error',
            1:'Illegal value',
            2:'Wrong token',
            3:'Invalid bit',
            4:'Queue full',
            5:'Not compatible'
            })
    LCME = bidict({
            0:'No exec error',
            1:'Illegal command',
            2:'Undefined command',
            3:'Illegal query',
            4:'Illegal set',
            5:'Missing parameter',
            6:'Extra parameter',
            7:'Null parameter',
            8:'Parameter buffer overflow',
            9:'Bad floating-point',
            10:'Bad integer',
            11:'Bad integer token',
            12:'Bad token value',
            13:'Bad hex block',
            14:'Unknown token'
            })
    SOUT = bidict({
            0:'Off',
            1:'On'
            })
    RNGE = bidict({
            0:'1 V',
            1:'10 V',
            2:'100 V'
            })
    ISOL = bidict({
            0:'Ground',
            1:'Float'
            })
    
    commandlist = {}
    errcmds     = {}
    core        = {}
    
    commandlist['core'] = {}
    
    errcmds['LCME'] = ['LCME?', LCME]
    errcmds['LEXE'] = ['LEXE?', LEXE]
    
    core['Volt']   = 'VOLT'
    core['Output'] = ['SOUT', SOUT]
    core['Range']  = ['RNGE', RNGE]
    core['Ground'] = ['ISOL', ISOL]
    
    commandlist['core'] = core
    
    def __init__(self, address, reset):
        '''
        __init__ _summary_
        :param address: _description_
        :type address: _type_
        :param reset: _description_
        :type reset: _type_
        '''        
        super().__init__(address, self.commandlist, self.errcmds, reset)
    
    def voltage_ramp(self, newV, step_size = 0.005, step_time = 0.001):
        '''
        voltage_ramp _summary_
        :no-index:
        :param newV: _description_
        :type newV: _type_
        :param step_size: _description_, defaults to 0.005
        :type step_size: float, optional
        :param step_time: _description_, defaults to 0.001
        :type step_time: float, optional
        '''        
        deltaV = newV - self.Volt
        numSteps = max(2, int(np.abs(np.ceil(deltaV/step_size))))
        vsteps = np.linspace(self.Volt, newV, numSteps)
        for vstep in vsteps:
            self.Volt = np.round(vstep,6)
            time.sleep(step_time)
        return