# -*- coding: utf-8 -*-
"""
Created on Thu Apr 30 15:44:05 2020

@author: Kollarlab
"""
from Acqiris import Acqiris
import sys

hardwareAddress = "PXI23::0::0::INSTR"

IVIbinPath = "C:\\Program Files\\IVI Foundation\\IVI\\Bin\\"
if not IVIbinPath in sys.path:
    sys.path.append(IVIbinPath)



#class Base(object): 
#    __slots__ = 'val'
#    
#b = Base()
    
    
#card = Acqiris(hardwareAddress) 
    
    
#card.segements = 1

#card.Close()
    
    
    
    
from Instruments.SGS import RFgen


#rfgen = RFgen('192.168.1.16')
rfgen = RFgen('TCPIP0::rssgs100a110739::inst0::INSTR')