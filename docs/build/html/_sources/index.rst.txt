======================================
Kollar-Lab Repository Documentation
======================================

**Welcome to the documentation site for the Kollar-Lab github repository!**

This repository contains the main scripts that are used for taking data across all projects within the Kollar Lab. 
Each folder is titled by the exact name that it's called in the actual repository to minimize confusion. 

This documentation was originally created by Ruthie Vogel in 2024. There's a file in the Z drive tutorials folder that has information on how to update
the docs and some information on how to navigate the site. If you have any particulatly gnarly questions, you can email vogelruthie at gmail dot com ":)"


Source Code Folders
=====================

.. autosummary::
   :toctree: cw_measurements
   :template: custom_module.rst 
   :recursive:

   cw_measurements

This folder contains all of the various VNA measurement scripts.

.. autosummary::
    :toctree: kollar_instruments
    :template: custom_module.rst
    :recursive:

    kollar_instruments   

This folder contains the SCPIinst drivers for most of the instruments in the lab.  


.. autosummary::
   :toctree: pulsed_measurements
   :template: custom_module.rst 
   :recursive:

   pulsed_measurements

This is where a lot of the standard measurement scripts for the analog system are located, including calibration and T1/T2 scripts.
There's also some scripts that are more specific to individual projects, and the analog scheduler in a ``schedules`` subfolder.

.. autosummary::
   :toctree: qick_measurements
   :template: custom_module.rst 
   :recursive:

   qick_measurements

This folder is to the FPGA/qick board as ``pulsed_measurements`` is to the analog system. It has all the calibration scripts and the randomized benchmarking
code. There's a separate folder with the drivers that exists in the repository but isn't documented here.

.. autosummary::
   :toctree: utility
   :template: custom_module.rst 
   :recursive:

   utility

Utility has a bunch of helpful stuff like plotting tools and generally useful functions. 

.. autosummary::
   :toctree: miscellaneous 
   :template: custom_module.rst 
   :recursive:

   userfuncs

This is where all of the files just within the Kollar-Lab folder and not within any subfolders are located. 

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`