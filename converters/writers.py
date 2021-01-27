# -*- coding: utf-8 -*-
"""
Created on Thu Jul 23 17:44:57 2020

@author: Mark
"""
from converters.vamas import VamasHeader, Block
import json
import xlsxwriter
import re
from copy import copy

class ExcelWriter():
    """A writer for outputing data in Excel.
    
    This object should be instantiated inside a Converter object.
    """   
    
    def __init__(self):
        pass
    
    def write(self, data, filename, **kwargs):
        """Write the parsed data to an Excel file.
        
        Parameters
        ----------
        data: LIST of DICTIONARIES
            The parsed data to be written.
        filename: STRING
            The name of the output file.
        """
        filename = filename + '.xlsx'
        workbook = xlsxwriter.Workbook(filename)
        temp_gid = ''
        for d in data:        
            if d['group_id'] != temp_gid:
                temp_gid = d['group_id']
                sheetname = str(d['group_id']) + ' - ' + str(d['group_name'])
                worksheet = workbook.add_worksheet(sheetname[:31])
                start_col = 0
            for j in d['data']:
                if j =='x':
                    worksheet.write(0,start_col, d['spectrum_id'])
                    worksheet.write(1, start_col, d['spectrum_type'])
                worksheet.write(2,start_col, j)
                vals = [v for v in d['data'][j]]
                for i, val in enumerate(vals):
                    worksheet.write(3+i,start_col, val)
                start_col += 1 
            start_col += 1
        workbook.close()
        
class JSONWriter():
    """A writer for outputing JSON.
    
    This object should be instantiated inside a Converter object.
    """
    
    def __init__(self):
        pass
    
    def write(self, data, filename):
        """Write the parsed data to a JSON file.
        
        Parameters
        ----------
        data: LIST of DICTIONARIES
            The parsed data to be written.
        filename: STRING
            The name of the output file.
        """
        with open(filename+'.json', 'w') as json_file:
            json.dump(data, json_file, indent=4)
               
class VamasWriter():
    """A writer for outputing Vamas.
    
    This object should be instantiated inside a Converter object.
    """
    
    def __init__(self):
        self.normalize = 0
       
    def write(self, data, filename):
        """Write the parsed data to a Vamas file.
        
        Parameters
        ----------
            data: LIST of DICTIONARIES
            The parsed data to be written.
            filename: STRING
            The name of the output file.
        """
        self.filename = filename
        self.num_spectra = 0
        self.file_path = ''
        self.millenium = 2000
        self.header_lines = 15
        self.spectra = []
        self.blocks = []
        self.sourceAnalyzerAngle = '56.5'
        self.vamas_header = VamasHeader()
        self.scans_averaged = 0
        self.loops_averaged = 0
        self.count_type = 'Counts per Second'
        self.blocks_counter = 0
        self.blocks = []
        for spec in data:                
            block = Block()
            block.sampleID = spec['group_name']                    
            
            block.blockID = spec['spectrum_type']
            block.noCommentLines = 10
            block.commentLines = ('Casa Info Follows\n0\n0\n0\n0\n' 
                  + 'none' + '\nGroup: ' + 'none' 
                  +'\nAnalyzer Lens: ' + 'none' 
                  + '\nAnalyzer Slit: ' + 'none' 
                  + '\nScan Mode: ' + 'none')
            block.expVarValue = 0
            split_string = re.split(r'(\d)', spec['spectrum_type'])
            species = split_string[0]
            transition = ''
            for i in split_string[1:]:
                transition += i
            block.speciesLabel = species
            block.transitionLabel = transition
            block.noScans = spec['scans']
            if len(spec['time_stamp'].split(' ')) == 3:
                date, time, zone = spec['time_stamp'].split(' ')
            elif len(spec['time_stamp'].split(' ')) == 2:
                date, time = spec['time_stamp'].split(' ')
            if len(date.split('/')) == 3:
                block.month, block.day, block.year = date.split('/')
            elif len(date.split('-')) == 3:
                block.month, block.day, block.year = date.split('-')
            if len(block.year) == 2:
                block.year = int(block.year) + self.millenium
            block.hour, block.minute, block.second = time.split(':')
            block.noHrsInAdvanceOfGMT = '0' #zone.strip('UTC')

            block.technique = spec['analysis_method']
            if 'source_label' in spec.keys():
                block.sourceLabel = spec['source_label']
            else: 
                block.sourceLabel = 'unknown'
            block.sourceEnergy = spec['excitation_energy']
            block.sourceAnalyzerAngle = self.sourceAnalyzerAngle
            block.analyzerMode = 'FAT'
            block.resolution = spec['pass_energy']
            block.workFunction = spec['workfunction']
            block.dwellTime = spec['dwell_time']
            
            y_units = spec['y_units']
            if y_units == 'Counts per Second':
                y = [i * float(block.dwellTime) * float(block.noScans) 
                for i in spec['data']['y']]
            else:
                y = [i for i in spec['data']['y']]
            if self.normalize != 0:
                norm = self.normalize
                y = [spec['data']['y'][i] / spec['data']['y'+str(norm)][i]
                    for i in range(len(spec['data']['y']))]                                               
            x_units = spec['x_units']
            if ((x_units == 'binding energy') & (spec['scan_mode'] != 'FixedEnergies')):
                block.abscissaStart = str(float(block.sourceEnergy) - float(spec['start_energy']))
            else:
                block.abscissaStart = spec['data']['x'][0]
            block.abscissaStep = abs(spec['data']['x'][1]-spec['data']['x'][0])
            
            if 'n_values' not in spec.keys():
                nr_values = len(spec['data']['y'])
                block.numOrdValues = str(int(nr_values * int(block.noAdditionalParams)))
            else:
                block.numOrdValues = str(int(spec['n_values']) * int(block.noAdditionalParams))
            block.minOrdValue1 = min(spec['data']['y'])
            block.maxOrdValue1 = max(spec['data']['y'])
            block.minOrdValue2 = 1
            block.maxOrdValue2 = 1
            for i in y:
                block.dataString += str(i) + '\n1\n'
            block.dataString = block.dataString[:-1]
            self.blocks += [copy(block)]
            block.dataString=''
        self.num_spectra = len(self.blocks)
        self.vamas_header.noBlocks = self.num_spectra
        
        with open(str(filename) + '.vms', 'w') as file:
            for item in self.vamas_header.__dict__:    
                file.writelines(str(self.vamas_header.__dict__[item]) + '\n')
            for block in self.blocks:
                for item in block.__dict__:
                    file.writelines(str(block.__dict__[item]) + '\n')
            file.writelines('end of experiment')
            file.close()
