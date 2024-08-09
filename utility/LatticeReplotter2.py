#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 13 14:51:51 2023

@author: kollar2

10-13 AK is creating a new version of replotter class to help with book keeping for 
the lattice project.

Main features being added or modified
1) Default is to auto load all settings and limits from the file, with an option 
to overwrite if desired
2) add save command so the replotter object can be pickled
-make sure not to resave the data itself.
3) add an option to reload and refill from pickled replotter, rather than a pickled data file
4) Automatically save record of settings when saving the replotter. This is for version tracking.


10-16-23 AK making differntial cutoff an attribute so that changing it
        will automatically trigger a recompute of the differential stuff.
        Differential plot methods should now automatically check if this is up to date
        
        Also changing show_plots so that if you don't specify something, 
        it uses the default instead of overwriting
        
10-17-23 AK adding proper flags to detect if this is a raw voltage scan or 
        if it's something where fluxes are put in and the voltages computed
        according to precalibtation
        
        -Add making the color limit guessing adjust if there is phase data.

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






class replotter2(object):
    def __init__(self, folder = '',filename = '',
                 name = '',
                 savedir = '',
                 vmin = np.nan,
                 vmax = np.nan,
                 xlims = [np.nan,np.nan],
                 ylims = [np.nan,np.nan],
                 diff_cutoff = np.nan,
                 cmap = 'YlGnBu_r',
                 div_cmap = whiteBlueBlue_double,
                 fig_xSize = 8,
                 fig_ySize = 6,
                 subtraction_ind = 0,
                 diff_colorBound = 10,
                 auto_display_plots = False,
                 default_phase = False):
        '''
        new version of replotter class.
        
        Init will now automatically fill values from the data file or a prepickled replotter object
        
        settings with default of nan will automatically load from the file
        If they are set to not nan, then the manually entered value will be used instead
        
        for compatibility with first replotter, folder argument comes firts, but will try to make it optional
        
        
        name is now an important attribute. The idea is that this will be a convenient handle
        that can be given to the replotter, rather then the really long data file name
        
        if a name is not given it will 
        
        removing old data smoothing option. it was not being used.
        
        savedir sets where any outputs should be saved. 
        by default this will be the same as the location
        of the corresponding raw data pickle.
        
        
        '''
        
        
        self.auto_display_plots = auto_display_plots
        

        self.raw_data_folder = folder
        self.filename = filename
        if not filename[-4:] == '.pkl':
            raise ValueError('No valid file given. Please give "something.pkl"   ')
        
        if name == '':
            self.name = self.filename[:-4]
        else:
            self.name = name
            
        if savedir == '':
            self.savedir = self.raw_data_folder
        else:
            self.savedir = savedir #location to save replotter files. Defaults to same location as script
        
        

        self.filepath = os.path.join(self.raw_data_folder, self.filename)
        
        #flag for identify saved pickles as replotter instead of raw data
        self.replotter_flag = True 
        
        #flag for warning if it can't find the raw data
        self.data_load_failed = False
        
        #open the .pkl and check if it is a raw data file
        #or a replotter
        raw_pickledict = pickle.load(open(self.filepath, "rb" ) )
        if 'replotter_flag' in raw_pickledict.keys():
            if raw_pickledict['replotter_flag'] == True:
                self.load_from_replot_pickle(raw_pickledict)
        else:
            #this must be a raw data file, 
            self.pickledict = raw_pickledict #this pickle is the actual data file pickle
            
            #fill in settings that won't be defined just from raw data
            self.subtraction_ind = subtraction_ind
            self.diff_colorBound = diff_colorBound
            
            self.fig_xSize =fig_xSize
            self.fig_ySize =fig_ySize
            
            self.default_phase = default_phase
            
            self.cmap = cmap
            self.div_cmap = div_cmap
            
            #so load from the data file
            # self.load_from_raw_data()
            self.parse_raw_data_file()
            self.semiauto_color_limits()
        
        ####potentially overwrite settings, given inuts at creation
        ##########
        if not np.isnan(xlims[0]):
            #overwrite the default
            self.xlims = xlims
        
        if not np.isnan(ylims[0]):
            #overwrite the default
            self.ylims = ylims
            
        if not np.isnan(vmin):
            #overwrite the default
            self.vmin = vmin
            
        if not np.isnan(vmax):
            #overwrite the default
            self.vmax = vmax

        if not np.isnan(diff_cutoff):
            #overwrite the default
            self.diff_cutoff = diff_cutoff     
        ############
        
        if (not self.data_load_failed):
            #compute final stuff
            #recompute the differential transmission
            self.compute_trimmed_data()
            self.compute_diff_transmission()
            
            if self.auto_display_plots:
                self.show_default_plots()
                
        return

    @property
    def diff_cutoff(self):
        return self._diff_cutoff
    
    @diff_cutoff.setter
    def diff_cutoff(self, val):
        self._diff_cutoff = val
        self._stale_diff_cutoff = True
        
    def save(self, autolog = True, 
             saveplots = True,
             fignums = [401,402]):
        '''save the replotter object as a pickle
        --but make sure not to resave the raw data matrices again,
        or this will get huge
        '''
        #these are variables that shouldn't be saved
        exceptions_list = ['datadict',
                           'mags',
                           'phases',
                           'transdatadict',
                           'transmags',
                           'transphases',
                           'deltaMat',
                           'trimmedMat',
                           'pickledict',
                           'freqs',
                           'voltages',
                           'fluxes',
                           'ref_trace',
                           'data']
        
        #make a dictionary will all of the other settings
        savedict = {}
        for key in self.__dict__.keys():
            if key in exceptions_list:
                pass
            else:
                savedict[key] = self.__dict__[key]
        self.savedict= savedict ####
        
        if os.path.exists(self.savedir):
            pass
        else:
            os.mkdir(self.savedir)
        
        savename = self.name + '.pkl'
        savepath = os.path.join(self.savedir, savename)
        pickle.dump(savedict, open(savepath, 'wb'))
        
        #now to automatically back up the currrent settings
        if autolog:
            backupdir = os.path.join(self.savedir, 'Backup')
            if os.path.exists(backupdir):
                pass
            else:
                os.mkdir(backupdir)
            savename_backup = self.name + '_' + self.timestamp() + '.pkl' 
            savepath_backup = os.path.join(backupdir, savename_backup)
            pickle.dump(savedict, open(savepath_backup, 'wb'))
        
        if saveplots:
            #save the plots
            self.show_default_plots(savefig = True, 
                           show_diff_baseline_plot = False,
                           fignums = fignums)
        return

    def timestamp(self):
        '''time stamp for auto saving '''
        date  = datetime.datetime.now()
        stamp = date.strftime('%Y%m%d_%H%M%S')
        return stamp   

    def load_from_replot_pickle(self,raw_pickledict):
        '''
        laod structure from pickle file of the replotter class
        '''
        
        for key in raw_pickledict.keys():
            setattr(self, key, raw_pickledict[key])

        try:
            #and now I just need to repload the data
            
            ####trying to fix the fact that the raw data file path is absolute at creation
            ####this is a temporary hack
            if os.path.exists(self.filepath):
                pass
            else:
                testPath1 = os.path.join(r'Z:\Data\PeterChainPaperData\Raw Data Files', self.filename)
                testPath2 = os.path.join(r'/Volumes/Kollar/Data/PeterChainPaperData/Raw Data Files', self.filename)
            
                if os.path.exists(testPath1):
                    self.old_filepath = self.filepath
                    self.filepath = testPath1
                if os.path.exists(testPath2):
                    self.old_filepath = self.filepath
                    self.filepath = testPath2
            
            
            self.pickledict = pickle.load(open(self.filepath, "rb" ) )
            
            #fix differential cutoff, because I made it an attribute
            #and so it doesn't auto load right
            self.diff_cutoff = self._diff_cutoff
            
            #some old saved versions will have self.voltages instead of self.yaxis
            #so I will manually fix the issue
            if 'voltages' in raw_pickledict.keys():
                self.yaxis = self.voltages
                delattr(self, 'voltages')
        
            self.parse_raw_data_file()
        except:
            print('Something went wrong in reloading the original data file!!!!!!')
            print('Finishing object creation, so you can check the paths')
            print('but the object is BLANK!!!!!')
            
            self.data_load_failed = True
        
        return 

    # def load_from_raw_data(self):
    #     #drab the data matrices from the raw data file
    #     self.parse_raw_data_file()
        
    #     #configure the replotter settings
    #     self.auto_fill_plot_limits_from_file()
        
        
    def parse_raw_data_file(self):    
        '''populate data files from the raw data file '''

        self.datadict = self.pickledict['Data']
        self.settings = self.pickledict['ExpSettings']
        
        #figure out some general settings of the data file
        self.hanger = self.settings['exp_globals']['hanger']   #whether or not this is hanger data
        
        #check if the y axis is uncalibrated voltage or if it
        # should be some fluxes. This is going to be a bit messy
        #because some data files come from before such a distinction was made
        if 'voltages' in self.datadict.keys():
            self.yaxiskey = 'voltages'
        elif 'fluxes' in self.datadict.keys():
            self.yaxiskey = 'fluxes' 
        else:
            raise ValueError('Was looking for a y axis in either voltages or fluxes and found neither')
        
        if 'specdata' in self.datadict.keys():
            self.spec_flag = True
            
            #this is spec data and I need to load differently
            specdict = self.datadict['specdata']
            
            # self.voltages = self.datadict['voltages']
            self.yaxis = self.datadict[self.yaxiskey]
            self.labels = self.datadict['spec_labels']
            
            self.mags = specdict['mags']
            self.phases = specdict['phases']
            temp = specdict['xaxis']
            if np.max(temp) < 100:
                #clear sign that the frequency axis is in GHz
                self.GHzVHz_correction = True
                self.freqs = temp
            else:
                #axis isn't in GHz. It had better be in Hz
                self.GHzVHz_correction = False
                self.freqs = temp/1e9
            # if self.GHzVHz_correction:
            #     self.freqs = specdict['xaxis']
            # else:
            #     self.freqs = specdict['xaxis']/1e9
            
            #pull up the transmission data to use for background subtractions
            self.transdatadict= self.datadict['transdata']
            self.transmags = self.transdatadict['mags']
            self.transphases = self.transdatadict['phases']
            self.hangerBool = self.settings['exp_globals']['hanger'] 
            
            
            self.mags = specdict['mags']
            self.phases = specdict['phases']
            #do the rolling background subtraction
            # for vind in range(0, len(self.voltages)):
            for vind in range(0, len(self.yaxis)):
                
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
            self.spec_flag = False
            
            self.data = self.datadict['full_data']
            
            # self.voltages = self.datadict['voltages']
            self.yaxis = self.datadict[self.yaxiskey]

            self.labels = self.datadict['labels']
            
            self.mags = self.data['mags']
            self.phases = self.data['phases']
            
            temp = self.data['xaxis']
            if np.max(temp) < 100:
                #clear sign that the frequency axis is in GHz
                self.GHzVHz_correction = True
                self.freqs = temp
            else:
                #axis isn't in GHz. It had better be in Hz
                self.GHzVHz_correction = False
                self.freqs = temp/1e9
            # if self.GHzVHz_correction:
            #     self.freqs = self.data['xaxis']
            # else:
            #     self.freqs = self.data['xaxis']/1e9
        
        #gather the plotting limits
        self.xlims = [self.freqs[0], self.freqs[-1]]
        # self.ylims = [self.voltages[0], self.voltages[-1]]
        self.ylims = [self.yaxis[0], self.yaxis[-1]]
        
        # if self.smoothe_data:
        #     # raw_mags = copy.deepcopy(self.mags)
        #     self.mags = gaussian_filter(self.mags, sigma = self.smoothing_sigma)
            
        return


    def semiauto_color_limits(self, 
                            dynamic_range = 35, 
                            max_offset = 3,
                            diff_dynamic_range = 30,
                            show_diff_baseline_plot = False):
        '''crawl the data file for relevant variables
        and try to guess the right limits for colorplots etc.
        
        It won't be perfect, but it should be a pretty good guess'
        
        For safety will also recomute differential transmission
        
        '''
        if self.default_phase:
            plot_data = self.phases #this will work a little funny if it's a hanger
        else:
            plot_data = self.mags
        
        if self.hanger:
            self.vmin = np.min(plot_data) + max_offset #set the color bar edge to the dip
            self.vmax = self.vmin + dynamic_range
        else:
            self.vmax = np.max(plot_data) - max_offset #set the colorbar edge to the peak
            self.vmin = self.vmax - dynamic_range
        # self.xlims = [self.freqs[0], self.freqs[-1]]
        # self.ylims = [self.voltages[0], self.voltages[-1]]
    
        self.diff_cutoff = self.vmax - diff_dynamic_range  #cutoff for differential transmission
        
        #recompute the differential transmission
        self.compute_trimmed_data()
        self.compute_diff_transmission()
     
        return
    
    def manual_color_limits(self, 
                            vmax,
                            vmin,
                            diff_cutoff):
        '''set the color bar limits as a group, but manually'
        
        For safety will also recompute differential transmission
        
        '''
        
        self.vmin = vmin
        self.vmax = vmax
        self.diff_cutoff = diff_cutoff
        
        #recompute the differential transmission
        self.compute_trimmed_data()
        self.compute_diff_transmission()
     
        return





    ###########
    #methods for computing differential transmission
    ######
    def compute_trimmed_data(self):
        #zero out the noisy stuff at low power
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

    def recompute_differential(self):
        '''Fully recompute the differential transmision including 
        both trimming matrices with the cutoff and computing the differential
        
        Then will reset the warning flag.'''
        self.compute_trimmed_data()
        self.compute_diff_transmission()
        self._stale_diff_cutoff = False




    #############
    #built in plot methods
    ######
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
        plt.pcolormesh(self.freqs, self.yaxis, plot_data, cmap = 'hot',shading = 'auto')
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
        '''Make a non-differential plot fo the main data.
        
        Originally this was written assuming transmission data, but 
        has since been modified to also work for spec data, but the old 
        name remains. 
        
        New wrapper show_data_plot and show_spec_plot will be created so that
        the names are more sensible and backwards compatibility is maintained
        '''
        fig2 = plt.figure(fignum)
        plt.clf()
        
        ax = plt.subplot(1,1,1)
        if self.default_phase:
            plot_data = self.phases
        else:
            plot_data = self.mags
        plt.pcolormesh(self.freqs, self.yaxis, plot_data , 
                       cmap = self.cmap,
                       vmin = self.vmin,
                       vmax = self.vmax,
                       shading = 'auto')
        plt.xlabel(self.labels[0])
        plt.ylabel(self.labels[1])
        if 'specdata' in self.datadict.keys():
            plt.title('Spec v Applied Flux')
        else:
            plt.title('Transmission v Applied Flux')
        
        plt.colorbar()
        ax.set_xlim(self.xlims)
        ax.set_ylim(self.ylims)
        
        plt.suptitle(self.filename)
        
        fig2.set_size_inches([self.fig_xSize, self.fig_ySize])
        plt.tight_layout()
        plt.show()
        
        if savefig:
            save_name = self.name + '.png'
            save_path = os.path.join(self.savedir, save_name)
            fig2.savefig(save_path , dpi = 500)
            # save_name = filename + '_' + cmap + '.pdf'  #WARNING - PDF save seems to crash. Maybe map is too big
            # fig22.savefig(save_name)
        
        return

    def show_data_plot(self, fignum = 2, savefig = False):
        '''Wrapper for the function show_transmission plot
        
        That function is no longer specific to transmission data.
        So this wrapper is to change the name.
        
        '''
        self.show_transmission_plot(fignum = fignum, savefig = savefig)
        
    def show_spec_plot(self, fignum = 2, savefig = False):
        '''Wrapper for the function show_transmission plot
        
        That function is no longer specific to transmission data.
        So this wrapper is to change the name.
        
        '''
        if 'specdata' in self.datadict.keys():
            self.show_transmission_plot(fignum = fignum, savefig = savefig)
        else:
            raise ValueError('This is not a spec data set.')

    
    def show_differential_plot(self, fignum = 3, savefig =False):
        #plot the subtracted data, but using deltMat wich zeros
        #out parts of the data that are too low to have signal
        
        if self._stale_diff_cutoff:
            #diff cutoff has been set, but the matrices 
            #have not been recomputed
            self.recompute_differential()
        
        fig3 = plt.figure(fignum)
        plt.clf()
        
        ax = plt.subplot(1,1,1)
        plt.pcolormesh(self.freqs, self.yaxis, self.deltaMat, 
                       cmap = self.div_cmap, 
                       vmax = self.diff_colorBound, 
                       vmin = -self.diff_colorBound,
                       shading = 'auto')
        plt.xlabel(self.labels[0])
        plt.ylabel(self.labels[1])
        
        if 'specdata' in self.datadict.keys():
            plt.title('Differential Spec v Applied Flux')
        else:
            plt.title('Differential Transmission v Applied Flux')
        plt.colorbar()
        ax.set_xlim(self.xlims)
        ax.set_ylim(self.ylims)
        
        plt.suptitle(self.filename)
        
        # fig23.set_size_inches([7.5, 2.75])
        fig3.set_size_inches([self.fig_xSize, self.fig_ySize])
        plt.tight_layout()
        plt.show()
        
        if savefig:
            save_name = self.name + '_diff.png'
            save_path = os.path.join(self.savedir, save_name)
            fig3.savefig(save_path , dpi = 500)
        
        return
        
    
    def show_default_plots(self, savefig = False, 
                           show_diff_baseline_plot = False,
                           fignums = [401, 402]):
        '''show all the plots with default values 
        color bar limits and dynamic ranges etc are whatever the latest guesses were
        '''
        
        if self.data_load_failed:
            print('WARNING!!! Data load failed. This file is blank!!!')
            return
        
        # #recomute differential transmission in case the settings are stale
        # self.compute_trimmed_data()
        # self.compute_diff_transmission()
        #this safety check was moved to the differential plot itself
        
        
        # self.show_transmission_plot(fignum = 2, savefig = savefig) 
        self.show_data_plot(fignum = fignums[0], savefig = savefig)  
        
        self.show_differential_plot(fignum = fignums[1], savefig = savefig)
        
        if show_diff_baseline_plot:
            self.show_baseline_plot(fignum =403)
        
        return
    
    # def show_plots(self, dynamic_range = 35, 
    #                 max_offset = 3,
    #                 diff_dynamic_range = 30,
    #                 savefig = False,
    #                 fignums = [401,402],
    #                 show_diff_baseline_plot = False):
    
    def show_plots(self, dynamic_range = 35, 
                    max_offset = 3,
                    diff_dynamic_range = np.nan,
                    diff_colorBound = np.nan,
                    savefig = False,
                    fignums = [401,402],
                    show_diff_baseline_plot = False):
        ''' will show the main plots, but allows you to plot with the dynamic ranges
        and limits.
        
        dynamic_range sets the extent of the color bar for the main plot
        
        max_offset sets how far off the extremum one end of the color scale is
        (max for regular and min for hangers)
        
        diff_dynamic_range sets how far below the extremum of the main data you
        put the cutoff for differential transmission
        
        diff_colorBound = color bar limits for differential data
        
        WARNING. If you specify limits for this stuff, it will get written
        to the object. 
        
        '''
        
        if np.isnan(diff_dynamic_range):
            #don't change the differential cutoff
            diff_dynamic_range = self.vmax - self.diff_cutoff

        if not np.isnan(diff_colorBound):
            #overwrite the default
            self.diff_colorBound = diff_colorBound
        
        #reset the colorscale limits to the new values, this automatially recomputes diff trans
        self.semiauto_color_limits(dynamic_range = dynamic_range,
                            max_offset = max_offset,
                            diff_dynamic_range = diff_dynamic_range)
        
        if show_diff_baseline_plot:
            self.show_baseline_plot(fignum =403)
        
        self.show_data_plot(fignum = fignums[0], savefig = savefig)  
        
        self.show_differential_plot(fignum = fignums[1], savefig = savefig)
        
        
        return

    
    
    def make_data_subplot(self, ax,
                          dynamic_range = np.nan, 
                          ref_offset = np.nan,
                          ref_level = np.nan,
                          xlims = [np.nan, np.nan],
                          ylims = [np.nan, np.nan],
                          plot_phase = np.nan,
                          title_with_filename = False,
                          colorbar = True):
        
        ''' 
        
        Replot that allows to you command that the plot be created in a specific subplot
        axis, rather than creating a new figure for it.
        
        ax = axis object in which to plot
        
        dynamic_range = dynamic range for the color bar
        
        ref_offset = how far the edge of the colorbar should be from the 
                        extremum of the data
                        Sign of offset will depend on hanger v not
        
        ref_level = level in the data that should be used as a marker for
                the edge of the color scale.
                This looks totally redundant with ref aoffset, but I envison
                that the auto behavior is ref_level = np.max(data),
                the the offset is say how far you want to rail the color scale
                on that side.
                
        xlims = x axis limtis (assumed these are frequencies)
        
        ylims = y axis limtis (assumed these are fvoltages)
        
        plot_phase = boolean to say whether should plot mag or phase.
                     if nan, will sue the object default
                     
        title_with_filename = boolean to determine if file name should go in the title
                            for easy identification
                    
        If any parameter is np.nan by default, that means that it will use
        the values already stored with the data file, rather than fine tuning.
        
        11-8-23 AK made dynamic_range default to vmax-vmin, and ref offset default to zero
        This should mean that if you don't pass any arguments to this function except the
        axis, then you should get the same colorbar limits as the default entire figure
        -- also adding the option to leave off the colorbar. This makes it easier
        to fine tune it later
        
        '''
        plt.sca(ax)

        if np.isnan(dynamic_range):
            #use the default
            dynamic_range = self.vmax - self.vmin
            
        if np.isnan(ref_offset):
            #use the default
            ref_offset = 0
        
        if np.isnan(ref_level):
            #use the default
            if self.hanger:
                ref_level = self.vmin
            else:
                ref_level = self.vmax
                
        if np.isnan(xlims[0]):
            #use the default
            xlims = self.xlims
        
        if np.isnan(ylims[0]):
            #use the default
            ylims = self.ylims
        
        # #configure the offset and the dynamic range to match the hanger v not
        # dynamic_range = signum*dynamic_range
        # ref_offset = signum*ref_offset
        
                
        #pull up the right data
        if np.isnan(plot_phase):
            #use the default
            if self.default_phase:
                plot_data = self.phases
            else:
                plot_data = self.mags
        elif plot_phase:
            plot_data = self.phases
        else:
            plot_data = self.mags
            
        #configure the plot limits
        if self.hanger:
            #set everything from the min value
            vmin = ref_level + ref_offset
            vmax = vmin + dynamic_range
        else:
            #set everything from the max value
            vmax = ref_level - ref_offset
            vmin = vmax - dynamic_range
            
        plt.pcolormesh(self.freqs, self.yaxis, plot_data , 
                       cmap = self.cmap,
                       vmin = vmin,
                       vmax = vmax,
                       shading = 'auto')
        plt.xlabel(self.labels[0])
        plt.ylabel(self.labels[1])
        if 'specdata' in self.datadict.keys():
            plt.title('Spec v Applied Flux')
        else:
            plt.title('Transmission v Applied Flux')
        
        if title_with_filename:
            plt.title(self.filename)
        
        if colorbar:
            plt.colorbar()
        ax.set_xlim(xlims)
        ax.set_ylim(ylims)

        return
    
    def make_diff_subplot(self, ax,
                          dynamic_range = np.nan, 
                          diff_cutoff = np.nan,
                          xlims = [np.nan, np.nan],
                          ylims = [np.nan, np.nan],
                          title_with_filename = False,
                          colorbar = True):
        ''' 
        
        Replot that allows to you command that the plot be created in a specific subplot
        axis, rather than creating a new figure for it. This version will plot the 
        differential transmission
        
        ax = axis object in which to plot
        
        dynamic_range = dynamic range for the color bar (+- val for this)
        
        diff_cutoff = absolute power below which we zero the data for differential
                
        xlims = x axis limtis (assumed these are frequencies)
        
        ylims = y axis limtis (assumed these are fvoltages)
        
        title_with_filename = boolean to determine if file name should go in the title for easy identification
                    
        If any parameter is np.nan by default, that means that it will use
        the values already stored with the data file, rather than fine tuning.
        
        WARNING - To change the minimu value, this will have to recompute the cutoff and 
        store the new version.
        
        11-8-23 Adding the option to leave off the colorbar. It makes it easier to 
        fine tune it later
        
        '''
        plt.sca(ax)

        if np.isnan(xlims[0]):
            #use the default
            xlims = self.xlims
        
        if np.isnan(ylims[0]):
            #use the default
            ylims = self.ylims
            
        if np.isnan(dynamic_range):
            #use the default
            dynamic_range = self.diff_colorBound
            
        if np.isnan(diff_cutoff):
            #use the default. Everything is already computed
            pass
        else:
            #need to reconfigure the minimum cutoff and recompute differential
            self.diff_cutoff = diff_cutoff
            
            #recompute the differential transmission
            self.compute_trimmed_data()
            self.compute_diff_transmission()
        
        #make sure that the differential matrices are up to date 
        if self._stale_diff_cutoff:
            #diff cutoff has been set, but the matrices 
            #have not been recomputed
            self.recompute_differential()
            
        plt.pcolormesh(self.freqs, self.yaxis, self.deltaMat, 
                       cmap = self.div_cmap, 
                       vmax = dynamic_range, 
                       vmin = -dynamic_range,
                       shading = 'auto')
        plt.xlabel(self.labels[0])
        plt.ylabel(self.labels[1])
        if 'specdata' in self.datadict.keys():
            plt.title('Differential Spec v Applied Flux')
        else:
            plt.title('Differential Transmission v Applied Flux')
        
        if title_with_filename:
            plt.title(self.filename)
        
        if colorbar:
            plt.colorbar()
        ax.set_xlim(xlims)
        ax.set_ylim(ylims)

        return










