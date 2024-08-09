# -*- coding: utf-8 -*-
"""
Created on Fri Dec  4 18:26:25 2020

@author: Kollarlab
"""
import numpy

t1 = 5.5e-6
maxVal = 0.016
minVal = 0.003

#ys = (maxVal - minVal)*numpy.exp(-taus/t1) + minVal
ys = (maxVal - minVal)*numpy.exp(-xaxis/t1) + minVal

# Ruthie added in a throwaway definition for xaxis so this script would import 
xaxis = numpy.ones(1e4)


plt.figure(4)
plt.clf()
plt.plot(xaxis/1e-6, amp, 'b.')
plt.plot(xaxis/1e-6, ys, color = 'firebrick')
plt.xlabel('time (us)')
plt.ylabel('voltage')
plt.title('T1 = ' + str(numpy.round(t1*1e6,3)) + ' $\mu$s')
plt.show()