# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 11:05:25 2020

@author: Mark
"""

from datetime import datetime

class ProdigyParserXY():
    """A parser for reading in ASCII-encoded .xy data from Specs Prodigy.
    
    Tested with SpecsLab Prodigy v 4.64.1-r88350.
    """
    
    def __init__(self, **kwargs): 
        """Construct the parser.
        
        Accepted kwargs: n_channels (INT) defining the number of addditional
        parallel data acquisition channels.        
        """
        self.normalize = 0
        if 'n_channels' in kwargs.keys():
            self.nr_channels = kwargs['n_channels']
        else:
            self.nr_channels = 0
            
        self.settings_map = {'Acquisition Date':'time_stamp',
                             'Analysis Method':'analysis_method',
                             'Analyzer Lens':'lens',
                             'Analyzer Slit': 'entrance_slit',
                             'Bias Voltage':'bias_voltage',
                             'Binding Energy':'start_energy',
                             'Scan Mode': 'scan_mode',
                             'Values/Curve':'n_values',
                             'Eff. Workfunction':'workfunction',
                             'Excitation Energy':'excitation_energy',
                             'Dwell Time':'dwell_time',
                             'Detector Voltage':'detector_voltage',
                             'Comment':'comments',
                             'Curves/Scan':'curves_per_scan',
                             'Pass Energy':'pass_energy',
                             'Source':'source_label'}
        
        self.unitsMap = {'kinetic energy':'eV',
                         'binding energy':'eV',
                         'excitation energy':'eV',
                         'ring current':'mA',
                         'mirror current':'mA',
                         'total electron yield': 'V',
                         'count rate':'counts per second',
                         'total counts':'counts',}
        
        self.keysToDrop = ['Kinetic Energy', 'OrdinateRange', 'comments',
                           'Spectrum ID',]
        
        
    def parseFile(self, filepath, commentprefix = '#', headerlines = 15):
        """Parse the .xy file into a list of dictionaries.
        
        Parsed data is stored in the attribute 'self.data'.
        Each dictionary in the data list is a grouping of related attributes.
        The dictionaries are later re-structured into a nested dictionary
        that more closely resembles the domain logic.
        """
        self.data = {}
        self.prefix = commentprefix
        self.filepath = filepath
        self.headerlines = headerlines
        self.header = {}
        
        with open(filepath) as fp:
            nr = 0
            block = 0
            last_number = False
            open_block = False
            channel_count = 0
            self.data[block] = {}
            for line in fp:
                """This first parses the header."""
                if nr < self.headerlines:
                    line = line.strip(self.prefix).strip()
                    if len(line) == 0:
                        pass
                    else:
                        self.header[line.split(':',1)[0].strip()] = line.split(':',1)[1].strip()
                        """If the line starts with a comment prefix and that is the 
                        only thing in the line or if the line is completely empty
                        then close the block.
                        """
                else:
                    """This intializes a new block."""
                    if (
                            ((line[0] == self.prefix) & 
                            (len(line.strip(self.prefix).strip()) == 0)) | 
                            (len(line.strip())==0) |
                            ((last_number == True) & (line[0] == self.prefix))
                            ):
                        open_block = False
                        last_number = False
                    """This if statement parses the metadata
                    if the line starts with the prefix, and the prefix is not 
                    the only thing in the line then check if a block is 
                    already open. If not, then start a new block then add 
                    data to the block."""
                    if((line[0] == self.prefix) & 
                            (len(line.strip(self.prefix).strip()) != 0)
                            ):
                        line = line.strip(self.prefix).strip()
                        if open_block == False:
                            open_block = True
                            block += 1
                            self.data[block]={}
                        key = line.split(':',1)[0]
                        val = line.split(':',1)[1].strip()
                        self.data[block][key] = val
                        """This condition is to count the number of channels 
                        in the data streams the word 'Cycle' indicates the 
                        start of a new set of data channels."""
                        if key == 'Cycle':
                            channel_count = 0
                            if (len(val.split(',')) > 1) and (':' in val):
                                comma_split = val.split(',')
                                self.data[block][key] = comma_split[0]
                                for s in comma_split[1:]:
                                    k = s.split(':')[0].strip()
                                    v = s.split(':')[1].strip()
                                    self.data[block][k] = v
                    
                        """If the line does not start with the prefix, and it 
                        is not empty then the line must be a data-stream and 
                        must start with a number."""
                    elif (line[0] != self.prefix) & (len(line.strip()) != 0):
                        """ If no block is open yet, then open one."""
                        if open_block == False:
                            block += 1
                            channel_count +=1
                            """This is to indicate a new data stream. Each 
                            data stream counts as a channel"""
                            if channel_count > self.nr_channels:
                                self.nr_channels = channel_count
                            self.data[block]={}
                            self.data[block]['data']=[]
                            open_block = True
                        self.data[block]['data'] += [[float(line.split(' ')[0]),float(line.split(' ')[-1])]]
                        last_number = True
                nr += 1
            self.data = [val for val in self.data.values() if len(val) !=0]
        return self._buildDict()         
    
    def _extractData(self, data, n_channels):
        data_array = []
        data_array += [self._getXData(data)]
        
        for n in range(n_channels):
            data_array += [self._getYData(data)]
        
        return data_array
        
    def _getXData(self, data):
        x = []
        for d in data:
            x+=[d[0]]
        return x
        
    def _getYData(self, data):
        y = []
        for d in data:
            y+=[d[1]]
        return y
    
    def _buildDict(self):
        """Construct a nested dictionary.
        
        The nested dictionary represents the native heirarchical data model 
        in a form that is easily exported to JSON.
        """
        def rotate(l):
            l = l[1:]+l[:1]
            return l
        group_count = 0
        spectrum_count = 0
        channel = 1
        spectra = []
        data = {}
        data_array = []
        data_labels = []
        
        x_label_info = []
        y_label_info = []
        for i in self.data:
            if 'Group' in i.keys():
                # add a new 'group' to the array of groups
                group_name = i['Group']
                group_id = group_count
                group_count += 1
            if 'Region' in i.keys():
                ''' Regions is a grouping of data, that is not used in Vamas.
                It is a form of normalization, but is not general purpose, so
                it is not used in the nested dictionary structure.'''
                spectrum_type = i['Region']
                settings = {key : i[key] for key in i.keys() if key != 'Region'}
                if 'Scan Mode' in settings.keys():
                    x_label_info += [settings['Scan Mode']]
                settings = self._replaceKeys(settings, self.settings_map)
                #settings['y_units'] = self.header['Count Rate']
                #settings['x_units'] = self.header['Energy Axis']

                if 'time_stamp' in settings.keys():
                     self._parseDatetime(settings['time_stamp'])
                
                n_scans = 1
                
            if 'Number of Scans' in i.keys():
                n_scans = int(i['Number of Scans'])
                
            if 'Acquisition Date' in i.keys():
                date = self._parseDatetime(i['Acquisition Date'])
                date = date.strftime('%Y-%m-%d %H:%M:%S')
                
            if 'ColumnLabels' in i.keys():
                x_label_info += [i['ColumnLabels'].split(' ',1)[0]]
                y_label_info += [i['ColumnLabels'].split(' ',1)[1]]
                
            if 'data' in i.keys():
                d = i['data']
                spectrum_id = spectrum_count
                
                if channel <= self.nr_channels:
                    if channel-1 == 0:
                        data['x'] = [j[0] for j in i['data']]
                        data_array += [self._getXData(d)]
                    data_array += [self._getYData(d)]
                    
                    if channel-1 == 0:
                        data['y'] = [j[1] for j in i['data']]
                    else:    
                        data['y'+str(channel-1)] = [j[1] for j in i['data']]
                        
                        
                    if channel == self.nr_channels:
                        
                        new_data = {'time_stamp': date,
                                        'group_name': group_name,
                                        'group_id':group_id,
                                        'spectrum_type': spectrum_type,
                                        'spectrum_id': spectrum_id,
                                        'scans': n_scans,
                                        }
                        new_spectrum = {}
                        new_spectrum.update(settings.copy())
                        new_spectrum.update(new_data.copy())
                        new_spectrum['data'] = data_array
                        
                        data_labels += self._getXLabel(x_label_info)
                        data_labels += self._getYLabel(y_label_info, channel)
                        
                        
                        new_spectrum['data_labels'] = data_labels
                        
                        new_spectrum['data_units'] = self._getUnits(data_labels)
                        self._dropUnusedKeys(new_spectrum)
                        
                        spectra += [new_spectrum.copy()]
                        self.data_array = data_array
                        data_array = []
                        x_label_info = []
                        y_label_info = []
                        data_labels = []
                        
                        channel = 1
                        spectrum_count += 1
                    else: 
                        channel += 1
        
   
        self.data_dict = spectra
        return self.data_dict
    
    def _getXLabel(self, x_label_info):
        if "constantfinalstate" in [s.lower() for s in x_label_info]:
            label = ["excitation energy"]
        elif "kinetic energy" in self.header['Energy Axis'].lower():
            label = ["kinetic energy"]
        elif "binding energy" in self.header['Energy Axis'].lower():
            label = ["binding energy"]
        else:
            label = ["unknown"]
        
        return label
    
    def _dropUnusedKeys(self, dictionary):
        for key in self.keysToDrop:
            if key in dictionary.keys():
                del dictionary[key]
        
    
    def _getYLabel(self, y_label_info, n_channels):
        labels = []
        
        if len(y_label_info) != n_channels:
            print('The number of channels is not equal to the number of channels.')
            print(y_label_info)
            
        for label in y_label_info:
            labels += [label]
        
        labels = self._remapLabelNames(labels)
        return labels
    
    def _remapLabelNames(self,labels):
        new_labels = []
        for label in labels:
            if label == 'counts':
                new_labels += ['total counts']
            elif label == 'counts/s':
                new_labels += ['count rate']
            elif 'Ring Current' in label:
                new_labels += ['ring current']
            elif 'I_mirror' in label:
                new_labels += ['mirror current']
            elif 'Excitation Energy' in label:
                new_labels += ['excitation energy']
            elif 'TEY' in label:
                new_labels += ['total electron yield']
        return new_labels
            
    def _getUnits(self, labels):
        units = []
        for label in labels:
            units += [self.unitsMap[label]]
        return units
                
        
        
    
    
    def _parseDatetime(self, date):
        #difference = 0
        if date.find('UTC'):
            #difference = int(date[date.find('UTC')+3:])
            date = date[:date.find('UTC')].strip()
        else:
            date = date.strip()
            
        date_object = datetime.strptime(date, '%m/%d/%y %H:%M:%S')
    
        return date_object
    
    def _replaceKeys(self, dictionary, key_map):
        for key in key_map.keys():
            if key in dictionary.keys():
                dictionary[key_map[key]] = dictionary[key]
                dictionary.pop(key, None)
        return dictionary
        

            
