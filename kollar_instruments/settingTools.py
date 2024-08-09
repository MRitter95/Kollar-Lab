import re

def _get_level(line, genSection, gensetting):
    '''
    Get section depth inside dictionary (i.e. settings['HDAWG'] has depth one, 
    section['Channels']['Channel1'] has depth 2 etc.). Settings will return a 
    depth of zero and anything that cannot be matched to the reg ex will return 
    a negative number

    Arguments:
        line: string to be analyzed (expected section format: [sectionname] where # of [] gives level)
    
    Returns:
        level (int): depth inside dictionary of specific section, settings return 0
    '''

    #Check if input live is a setting
    setting = re.match(gensetting,line)
    if setting:
        return [0,setting]

    #Calculate how far down the section is by counting the number of square brackets
    for i in range(1,10):
        tagLevel = genSection %(i,i)
        ismatch = re.match(tagLevel,line)
        if ismatch:
            return [i,ismatch]
    
    #No match, return negative number
    return [-1, setting]


def _store_settings(settings, names, localset):
    '''
    Store the collection of settings at a specific location in the dictionary.
    This will automatically create entries if needed to achieve the correct depth
    Uses the names list as a series of keys in the dictionary:
    names=[Top section, subsection, subsubsection]
    locaset={setting1:a,setting2:b}
    settings[Topsection][subsection][subsubsection]=localset
    Arguments:
        settings (dict): dictionary to hold settings
        names (list): list of nodes to traverse to get to desired location
        localset (dict): dictionary of settings for particular node
    Returns:
        Nothing but updates the settings dictionary
    '''

    #Check if names is empty
    if not names:
        return
    else:
        #Get section name
        section = names[0]
        #Create dict if needed
        if section not in settings.keys():
            settings[section] = {}
        #Check if we are at the root
        if len(names)==1:
            settings[section] = localset
            return
        #Go one layer deeper
        _store_settings(settings[section],names[1:],localset)

def load_settings(inputfile):
    '''
    Helper function that reads in a file and turns it into a dictionary
    The file MUST have the following formatting standards:
    -[sections] that describe the main blocks/ modules of the instrument where more [] indicates subsections
    -settings = value that match attributes of the section/subsection they are in
    Can format this, modify reg-exes in function to do so

    Argurments:
    ############
        inputfile (str): 
            file where the settings are stored
    
    Returns:
    ##########
        dictionary organized as follows:
        settings = {sectionA:{settings},sectionB:{subsectionB:{settings},etc.},etc.}
    
    '''
    #Reg-exes to match sections and settings
    gensetting = r'(\S*)\s*=\s*(.*)' #Matches anything of 'Setting = value' format
    genSection = r'\[{1,%s}(\w*)\]{1,%s}' #Looks for arbitrary number of [] surrounding a section name

    #Initialize everything and open the file
    file = open(inputfile,'r')
    names = [] #Used to track where we are in the setting tree
    oldlevel = 0 #Used to see how we have to move to get to the next section
    settings = {} #Dictionary containing final settings
    localset = {} #Temp dict to store local settings of section of interest

    #Go through the entire file
    for line in file.readlines():
        #Figure out what the line is (section/ setting) and its breakdown in reg ex
        [level, regexp] = _get_level(line, genSection, gensetting)

        #Section or some sort
        if level > 0:
            #Store settings in path determined by names
            if names:
                _store_settings(settings,names,localset)
            #Check if we need to move up a section in the tree
            if oldlevel >= level:
                #print('Need to go up a section')
                leveldif = oldlevel-level
                for i in range(leveldif+1):
                    #Remove sections from names until we reached the desired level
                    names.pop()
            #Add current section to names list
            names.append(regexp.group(1))
            #Update section level
            oldlevel = level
            #Reset local dictionary
            localset = {}

        #Setting
        if level == 0:
            #Store setting in local dict 
            key = regexp.group(1)
            try:
                value = eval(regexp.group(2).split()[0])
            except:
                value = regexp.group(2)

            localset[key] = value

    #Store final set of local settings
    _store_settings(settings,names,localset)
    return settings

def print_settings(settings, file = None, sectionstyle = '[{}]', sectionheading = '{}'):
    '''
    Helper function to display the settings stored in a dictionary
    
    Arguments:
    ###########
        settings (str) : 
            dictionary structured with nested dictionaries composed of sections, subsections and settings
        Optional:
            file (filehandle): handle to file. If provided, will save to file instead of printing (default=None)
            sectionheading (str): format to display sections as (default=[{}])
    
    '''
    sectionheading = sectionheading.format(sectionstyle)
    if not settings:
        return
    for key in settings.keys():
        if isinstance(settings[key],dict):
            if file:
                file.write(sectionheading.format(key))
                file.write('\n')
            else:
                print(sectionheading.format(key))
            print_settings(settings[key],file, sectionstyle=sectionstyle, sectionheading = sectionheading)
        else:
            if file:
                file.write('{} = {}\n'.format(key,settings[key]))
            else:
                print('{} = {}'.format(key,settings[key]))

def save_settings(settings, savefile, sectionstyle = '[{}]'):
    '''
    Helper function to save settings to file, expects a dictionary with nested
    dictionaries coresponding to the various sections, subsections of the instrument settings

    Arguments:
        settings (dict): 
            dictionary containing all the relevant settings
        savefile (str): 
            path to file where settings should be saved
        Optional:
            sectionheading (str): format string for section style (default=[{}]\\n)

    '''
    
    if not settings:
        return
    fID = open(savefile,'w')
    print_settings(settings, file = fID, sectionstyle = sectionstyle)


############################################################
############################################################
#Old settings codes
############################################################
############################################################

def load_settings_old(inputfile):
    '''
    Helper function that reads in a file and turns it into a dictionary
    The file MUST have the following formatting standards:
    -[sections] that describe the main blocks/ modules of the instrument
    -[subsections] that describe subblocks such as channels
    -settings = value that match attributes of the section/subsection they are in
    
    Arguments:
    ###########
        inputfile (str) : 
            file where the settings are stored
    
    Returns:
    #########
        dictionary organized as follows:
        settings = {sectionA:{settings},sectionB:{subsectionB:{settings},etc.},etc.}
    
    '''

    #Regular expression that denote the style of the different setting labels
    sectionTag    = r'\[(\w*)\]'
    subsectionTag = r'\[\[(\w*)\]\]'
    settingTag    = r'(\S*)\s*=\s*(\S*)'

    confFile = open(inputfile,'r')
    line=confFile.readline()

    settings={}
    subset={}

    while True:
        #Determine the label associated with the line
        section    = re.match(sectionTag,line)
        subsection = re.match(subsectionTag,line)
        setting    = re.match(settingTag,line)

        if section:
            #Get the name of the section
            sectionName = section.group(1)
            #Read next line and check label
            line       = confFile.readline()
            section    = re.match(sectionTag,line)
            subsection = re.match(subsectionTag,line)
            setting    = re.match(settingTag,line)
            #Create dictionary for section entry
            settings[sectionName] = {}

            #Keep reading lines until we reach the next section
            while not section:
                #If we have a subsection, we need to go a layer deeper
                if subsection:
                    subset={}
                    #Get subsection name
                    subsectionName = subsection.group(1)
                    #Read next line
                    line    = confFile.readline()
                    setting = re.match(settingTag,line)
                    #Continue until we reach a non setting entry (section, subsection)
                    while setting:
                        subset[setting.group(1)] = setting.group(2)
                        #Read next line and check label
                        line       = confFile.readline()
                        setting    = re.match(settingTag,line)
                        section    = re.match(sectionTag,line)
                        subsection = re.match(subsectionTag,line)
                    #Store settings in the appropriate dict entry
                    settings[sectionName][subsectionName]=subset
                #If we just have settings, loop until we arrive to the next section
                elif setting:
                    while setting:
                        subset[setting.group(1)] = setting.group(2)
                        #Read next line and check label
                        line       = confFile.readline()
                        setting    = re.match(settingTag,line)
                        section    = re.match(sectionTag,line)
                        subsection = re.match(subsectionTag,line)
                    #Store settings in the section entry
                    settings[sectionName]=subset
                #If we reach the end of the file or something like that this should avoid infinite loops
                if not setting and not subsection:
                    break
        else:
            break

    return settings


def print_settings_old(settings):
    '''
    Helper function to display the settings stored in a dictionary
    
    Arguments:
        settings (str) : 
            dictionary structured with nested dictionaries composed of sections, subsections and settings
    
    '''

    #Formatting the output
    sectionStyle    = '[{}]'
    subsectionStyle = '[[{}]]'
    settingStyle    = '{}={}'

    #Loop through all the entries in settins
    for key in settings.keys():
        #Print the section header
        print(sectionStyle.format(key))
        #Making sure that the section is actually populated
        if isinstance(settings[key],dict):
            for subkey in settings[key]:
                #Checks to see if we have a subsection
                if isinstance(settings[key][subkey],dict):
                    #Print subsection header
                    print(subsectionStyle.format(subkey))
                    #Loop over all the settings in the subsection
                    for setting in settings[key][subkey].keys():
                        print(settingStyle.format(setting,settings[key][subkey][setting]))
                else:
                    #Print the settings
                    print(settingStyle.format(subkey,settings[key][subkey]))

def save_settings_old(settings, savefile):
    '''
    Helper function to save settings to file, expects a dictionary with nested
    dictionaries coresponding to the various sections, subsections of the instrument settings
    
    Arguments:
    ###########

        settings (dict) : 
            dictionary containing all the relevant settings
        savefile (str) : 
            path to file where settings should be saved
    
    '''

    #Formatting strings
    sectionStyle    = '[{}]\n'
    subsectionStyle = '[[{}]]\n'
    settingStyle    = '{}={}\n'

    saveTo=open(savefile,'w')
    #Loop through all the sections
    for key in settings.keys():
        saveTo.write(sectionStyle.format(key))
        #Check if section is populated
        if isinstance(settings[key],dict):
            for subkey in settings[key]:
                #Check if we have subsections
                if isinstance(settings[key][subkey],dict):
                    saveTo.write(subsectionStyle.format(subkey))
                    #Loop through all settings in subsection
                    for setting in settings[key][subkey].keys():
                        #Write settings to file
                        saveTo.write(settingStyle.format(setting,settings[key][subkey][setting]))
                else:
                    #Write settings to file
                    saveTo.write(settingStyle.format(subkey,settings[key][subkey]))

    saveTo.close()
            