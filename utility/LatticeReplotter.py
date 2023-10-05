#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  1 15:03:07 2023

@author: kollar2


8-10-23 Making this able to load spec data too.

8-17-23 Found a bug that subtraction ind was not actually being set. Fixed it.

9-1-23 Going to change the spec data option so that it normalizes to the 
       peak of the transmission, rather than the average of the trace, see if we get
       anything better for some replots.
       
       Nevermind. That didn't work well. I took it out
       
       
9-1-23 Adding option to make phase data the default for plot.
        Differential transmission remains always in mag    
        
        
10-5-23 AK adding the ability to auto fill from a file and display stuff
        by crawling the data file for relevant values



"""

import re
import random
# from scipy import *
import scipy
# import pylab
import matplotlib.pyplot as plt
import numpy as np
import time



import pickle
import datetime
import os
import sys

import copy

from scipy.ndimage import gaussian_filter




################
#making a custom colormap


# found that a dark in the middle color map works very well for the 
#differential transmission data, so I'm going to try to build a custom one.
import matplotlib as mpl
from matplotlib.colors import ListedColormap, LinearSegmentedColormap

# viridis = mpl.cm.get_cmap('viridis')
# viridis_r = mpl.cm.get_cmap('viridis_r')
# comboMap_colors = viridis_r.colors + viridis.colors 
# comboMap = ListedColormap(comboMap_colors)

#my favorites (old double sided)
colorlist = ['khaki','royalblue', 'midnightblue','royalblue', 'khaki']
khakiBlue_double = LinearSegmentedColormap.from_list('khakiBlue', colorlist)

colorlist = ['antiquewhite', 'lightskyblue','royalblue', 'navy','royalblue','lightskyblue','antiquewhite']
whiteBlueBlue_double = LinearSegmentedColormap.from_list('whiteBlueBlue', colorlist)








class replotter(object):
    def __init__(self, folder,filename,
                 vmin = -35,
                 vmax = -5,
                 cmap = 'YlGnBu_r',
                 div_cmap = whiteBlueBlue_double,
                 xlims = '',
                 ylims = '',
                 fig_xSize = 8,
                 fig_ySize = 6,
                 diff_cutoff = -35,
                 subtraction_ind = 0,
                 diff_colorBound = 10,
                 smoothe_data = False,
                 smoothing_sigma = 0.75,
                 verbose = False,
                 GHzVHz_correction = False,
                 default_phase = False,
                 auto_fill_from_file = False):
        
        self.verbose = verbose
        
        self.folder = folder
        self.filename = filename
        self.filepath = os.path.join(folder, filename)
        
        #color bar limits for transmission plots
        self.vmin = vmin
        self.vmax = vmax
        self.diff_cutoff = diff_cutoff
        self.diff_colorBound = diff_colorBound
        
        #settings for differential transmission
        self.subtraction_ind = subtraction_ind
        
        #setting whether the default displayed data is phase of mag
        self.default_phase = default_phase
        
        #color maps to use
        self.cmap = cmap
        self.div_cmap = div_cmap
        
        
        #smoothing settings
        self.smoothe_data = smoothe_data
        self.smoothing_sigma = smoothing_sigma
        
        #correction factor for old data that has frequncy axis in GHz
        self.GHzVHz_correction = GHzVHz_correction
        
        #load the data and determine the plot limits
        self.load_data()
        if xlims == '':
            #no limits given, determine automatically
            self.xlims = [self.freqs[0], self.freqs[-1]]
        else:
            self.xlims = xlims
            
        if ylims == '':
            #no limits given, determine automatically
            self.ylims = [self.voltages[0], self.voltages[-1]]
        else:
            self.ylims = ylims
            
        
        #default figure size and limits
        self.fig_xSize = fig_xSize
        self.fig_ySize = fig_ySize
        
        #trim the data and compute differential transmission
        self.compute_trimmed_data()
        self.compute_diff_transmission()
        
        if self.verbose:
            self.show_default_plots()
            
        if auto_fill_from_file:
            self.auto_fill_from_file()
            
            
        
    def load_data(self):
        pickledict = pickle.load(open(self.filepath, "rb" ) )

        self.datadict = pickledict['Data']
        self.settings = pickledict['ExpSettings']
        
        if 'specdata' in self.datadict.keys():
            #this is spec data and I need to load differently
            specdict = self.datadict['specdata']
            
            self.voltages = self.datadict['voltages']
            self.labels = self.datadict['spec_labels']
            
            self.mags = specdict['mags']
            self.phases = specdict['phases']
            if self.GHzVHz_correction:
                self.freqs = specdict['xaxis']
            else:
                self.freqs = specdict['xaxis']/1e9
            
            #pull up the transmission data to use for background subtractions
            self.transdatadict= self.datadict['transdata']
            self.transmags = self.transdatadict['mags']
            self.transphases = self.transdatadict['phases']
            self.hangerBool = self.settings['exp_globals']['hanger'] 
            
            
            self.mags = specdict['mags']
            self.phases = specdict['phases']
            #do the rolling background subtraction
            for vind in range(0, len(self.voltages)):
                
                # #get the baseline by finding the cavity and taking transmission there.
                # #this is looking in the right place, but it might not have
                # #enough averaging.
                # trans_row = self.transmags[vind,:]
                # #find where the max or the min is. Fit would be safe, but I'm too lazy
                # #and the stupid way is somewhat robust.
                # if self.hangerBool:
                #     cav_ind = np.where(trans_row == np.min(trans_row))[0][0]
                # else:
                #     cav_ind = np.where(trans_row == np.max(trans_row))[0][0]  
                # mag_baseline = self.transmags[vind,cav_ind]
                # phase_baseline = self.transphases[vind,cav_ind]
            
            
                # #old way of finding the baseline by averaging the entire row of the spec
                # #this is a bit sketch if there are a lot of dips in a narrow window, but it averages 
                # #a lot.
                mag_baseline = np.mean(self.mags[vind,:])
                phase_baseline = np.mean(self.phases[vind,:])
                
                self.mags[vind,:] = self.mags[vind,:] - mag_baseline
                self.phases[vind,:] = self.phases[vind,:] - phase_baseline
            
            
            
        else:
            self.data = self.datadict['full_data']
            self.voltages = self.datadict['voltages']
            # filename = datadict['filename']
            self.labels = self.datadict['labels']
            
            self.mags = self.data['mags']
            self.phases = self.data['phases']
            if self.GHzVHz_correction:
                self.freqs = self.data['xaxis']
            else:
                self.freqs = self.data['xaxis']/1e9
        
        if self.smoothe_data:
            raw_mags = copy.deepcopy(self.mags)
            self.mags = gaussian_filter(self.mags, sigma = self.smoothing_sigma)
            
        return
        
    def compute_trimmed_data(self):
        #zeroout the noisy stuff at low power
        self.trimmedMat = copy.deepcopy(self.mags)
        noise_region = np.where(self.trimmedMat < self.diff_cutoff)
        self.trimmedMat[noise_region] = self.diff_cutoff
        return
    
    def compute_diff_transmission(self):
        #take a reference trace
        self.ref_trace = self.trimmedMat[self.subtraction_ind,:]
        

        self.deltaMat = copy.deepcopy(self.trimmedMat) - self.ref_trace
        
        self.delta_max = np.max(self.deltaMat)
        self.delta_min = - np.max(self.deltaMat) #np.min(deltaMat)
        return
    
    def show_baseline_plot(self, fignum = 1):
        ####plot the raw data, and the cutoff for differential transmission
        if self.default_phase:
            plot_data = self.phases
            labels = ['Raw Phase Data', 'S21 Phase (deg)']
        else:
            plot_data = self.mags
            labels = ['Raw Mag Data', 'S21 Log Mag (dB)']
        
        fig1 = plt.figure(fignum)
        plt.clf()
        
        ax = plt.subplot(1,2,1)
        plt.pcolormesh(self.freqs, self.voltages, plot_data, cmap = 'hot',shading = 'auto')
        plt.xlabel(self.labels[0])
        plt.ylabel(self.labels[1])
        plt.title(labels[0])
        plt.colorbar()
        
        ax = plt.subplot(1,2,2)
        plt.plot(self.freqs, plot_data[-1,:], color = 'mediumblue', label = 'data')
        plt.plot(self.freqs, self.diff_cutoff * np.ones(len(self.freqs)), color = 'firebrick', label = 'cutoff')
        plt.xlabel(self.labels[0])
        plt.ylabel(labels[1])
        plt.title('Single Trace')
        ax.legend(loc = 'lower right')
        
        fig1.set_size_inches([14, 6.5])
        plt.tight_layout()
        plt.show()
        # save_name = filename + '_Replot.png'
        # fig1.savefig(save_name, dpi = 400)
        ######################## 
        return
    
    def show_transmission_plot(self, fignum = 2, savefig = False):
        fig2 = plt.figure(fignum)
        plt.clf()
        
        ax = plt.subplot(1,1,1)
        if self.default_phase:
            plot_data = self.phases
        else:
            plot_data = self.mags
        plt.pcolormesh(self.freqs, self.voltages, plot_data , 
                       cmap = self.cmap,
                       vmin = self.vmin,
                       vmax = self.vmax,
                       shading = 'auto')
        plt.xlabel(self.labels[0])
        plt.ylabel(self.labels[1])
        plt.title('Transmission v Applied Flux')
        plt.colorbar()
        ax.set_xlim(self.xlims)
        ax.set_ylim(self.ylims)
        
        plt.suptitle(self.filename)
        
        fig2.set_size_inches([self.fig_xSize, self.fig_ySize])
        plt.tight_layout()
        plt.show()
        
        if savefig:
            save_name = self.filename + '_' + self.cmap + '.png'
            fig2.savefig(save_name, dpi = 500)
            # save_name = filename + '_' + cmap + '.pdf'  #WARNING - PDF save seems to crash. Maybe map is too big
            # fig22.savefig(save_name)
        
        return
    
    def show_differential_plot(self, fignum = 3, savefig = True):
        #plot the subtracted data, but using deltMat wich zeros
        #out parts of the data that are too low to have signal
        fig3 = plt.figure(fignum)
        plt.clf()
        
        ax = plt.subplot(1,1,1)
        plt.pcolormesh(self.freqs, self.voltages, self.deltaMat, 
                       cmap = self.div_cmap, 
                       vmax = self.diff_colorBound, 
                       vmin = -self.diff_colorBound,
                       shading = 'auto')
        plt.xlabel(self.labels[0])
        plt.ylabel(self.labels[1])
        plt.title('Differential Transmission v Applied Flux (cutoff, log mode)')
        plt.colorbar()
        ax.set_xlim(self.xlims)
        ax.set_ylim(self.ylims)
        
        plt.suptitle(self.filename)
        
        # fig23.set_size_inches([7.5, 2.75])
        fig3.set_size_inches([self.fig_xSize, self.fig_ySize])
        plt.tight_layout()
        plt.show()
        
        if savefig:
            save_name = self.filename + '_Differential.png'
            fig3.savefig(save_name, dpi = 500)
            # save_name = filename + '_Differential.pdf' #WARNING - PDF save seems to crash. Maybe map is too big
            # fig23.savefig(save_name)
        
        return
        
    
    def show_default_plots(self, savefig = False):
        
        self.show_baseline_plot(fignum =1)
        
        self.show_transmission_plot(fignum = 2, savefig = savefig)       
        
        self.show_differential_plot(fignum = 3, savefig = savefig)
        
        return
    
    
    def auto_fill_from_file(self, 
                            trans_dynamic_range = 35, 
                            max_offset = 3,
                            diff_dynamic_range = 30,
                            replot = True,
                            savefig = False,
                            figNums = [41,42],
                            show_diff_baseline_plot = False):
        '''crawl the data file for relevant variables
        and try to guess the right limits for x and y and colorplots etc.
        
        It won't be perfect, but it should be a pretty good guess'
        '''
        self.vmax = np.max(self.mags) - max_offset
        self.vmin = self.vmax - trans_dynamic_range
        self.xlims = [self.freqs[0], self.freqs[-1]]
        self.ylims = [self.voltages[0], self.voltages[-1]]
        
        
        self.diff_cutoff = self.vmax - diff_dynamic_range  #cutoff for differential transmission
        #background subtraction parameters
        self.subtraction_ind = 0
        
        #recompute the differential transmission
        self.compute_trimmed_data()
        self.compute_diff_transmission()
        
        if show_diff_baseline_plot:
            self.show_baseline_plot(fignum =71)
        
        if replot:
            self.show_transmission_plot(fignum = figNums[0], savefig = False)       
        
            self.show_differential_plot(fignum = figNums[1], savefig = False)

            if savefig:
                base_path= self.filepath[0:-4]
                
                trans_fig_path = base_path + '_TransReplot.png'
                currFig = plt.figure(figNums[0])
                currFig.savefig(trans_fig_path)
                
                diff_fig_path = base_path + '_DiffReplot.png'
                currFig = plt.figure(figNums[1])
                currFig.savefig(diff_fig_path)
    
    
    
    
    
    