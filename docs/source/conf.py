# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join('..', '..')))



print(sys.path)

project = 'Kollar-Lab Repository'
copyright = '2024, Kollar Lab'
author = 'Kollar Lab'
release = '2024'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.autosummary',
              'sphinx.ext.viewcode',
              ]

master_doc = 'index'
toc_object_entries_show_parents = 'domain'
add_module_names = False

templates_path = ['_templates']
exclude_patterns = [
    "initialize_hardware", 
    "exp_globals*", 
    "measurement_globals*", 
    "_build", 
    "_templates", 
    "rabi_chevron_fit*", 
    "SketchExpFit*", 
    "initialize_hardware_FPGA*",
    "Keithley2400_example*"
    "exp_globals_FPGA*",

    ]
autodoc_mock_imports = ['AqMD3', "hdawg", "pynq", 'xrfdc']
show_warning_types = True
suppress_warnings = ['index', 'docutils']

autosummary_generate = True





# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme" 
html_static_path = ['_static']

html_css_files = [
    'css/custom_style.css',
]

html_context = {
    "github_repo" : "https://github.com/MRitter95/Kollar-Lab"
}

html_theme_options = {
    "show_nav_level": 1,
    "primary_sidebar_end": ["indices.html"],
    "secondary_sidebar_items": ["page-toc", "edit-this-page", "sourcelink"],
    "navbar_align": "right",
    "navigation_depth": 2,
    "icon_links":[
        {
            "name": "Github",
            "url" : "https://github.com/MRitter95/Kollar-Lab",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        }
    ]
}


html_sidebars = {
    '**': [
        'globaltoc.html',
        'sourcelink.html',
        'searchbox.html',
    ], 

}