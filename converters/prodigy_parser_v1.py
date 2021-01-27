# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 08:26:25 2020

@author: Mark
"""
import sqlite3
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
import xml.etree.ElementTree as xml
import struct
from copy import copy
import numpy as np
import sys

class ProdigyParserV1():   
    supported_versions = ['1.8', '1.9','1.10','1.11','1.12','1.13','1.2']
    
    def __init__(self):
        self.con = ''
        self.spectra = []
   
        self.keys_map = {'Udet':'detector_voltage',
                     'Comment':'comments',
                     'ElectronEnergy':'start_energy',
                     'SpectrumID':'spectrum_id',
                     'EpassOrRR':'pass_energy',
                     'EnergyType':'x_units',
                     'Samples':'n_values',
                     'Wf':'workfunction',
                     'Step':'step',
                     'Ubias':'electron_bias',
                     'DwellTime':'dwell_time',
                     'NumScans':'scans',
                     'LensMode':'lens_mode',
                     'Timestamp':'time_stamp',
                     'Entrance':'entrance_slit',
                     'Exit':'exit_slit',
                     'ScanMode':'scan_mode',
                     'VoltageRange':'voltage_range',
                     }
        
        self.spectrometer_setting_map = {'Coil Current [mA]':'coil_current',
                                         'Pre Defl Y [nU]':'y_deflector',
                                         'Pre Defl X [nU]':'x_deflector',
                                         'L1 [nU]':'lens1',
                                         'L2 [nU]':'lens2',
                                         'Focus Displacement 1 [nu]':'focus_displacement',
                                         'Detector Voltage [V]':'detector_voltage',
                                         'Bias Voltage Electrons [V]':'bias_voltage_elecrons'}
        
        self.source_setting_map = {'anode':'source_label',
                                   'uanode':'source_voltage',
                                   'iemission':'emission_current',
                                   'DeviceExcitationEnergy':'excitation_energy'}
        
        self.sql_metadata_map = {'EnergyType':'x_units',
                                 'EpassOrRR':'pass_energy',
                                 'Wf':'workfunction',
                                 'Timestamp':'time_stamp',
                                 'Samples':'n_values',
                                 'ElectronEnergy':'start_energy',
                                 'Step': 'step_size'}
        
        self.key_maps = [self.keys_map,
                         self.spectrometer_setting_map,
                         self.source_setting_map,
                         self.sql_metadata_map]
        
        self.value_map = {'x_units': self._changeEnergyType,
                          'time_stamp': self._convertDateTime}
        
        self.keys_to_drop = ['CHANNELS_X','CHANNELS_Y','Bias Voltage Ions [V]',
                             'operating_mode']
        
        self.encodings_map = {'double':['d',8],
                              'float':['f',4]}
        self.encoding = ['f',4]
        
        self.average_scans = True
        
        self.spectrometer_types = ['Phoibos1D']
        
        self.measurement_types = ['XPS','UPS', 'ElectronSpectroscopy']
        
    def setCurrentFile(self, filename):
        """Set the filename of the file to be opened."""
        self.sql_connection = filename
        self.spectrum_column_names = self._getColumnNames('Spectrum')
        
    def parseFile(self, filename, **kwargs):
        """Parse the file's data and metadata into a flat list of dictionaries."""
        if 'average_scans' in kwargs.keys():
            self.average_scans = kwargs['average_scans']
        else:
            self.average_scans = True
        self.setCurrentFile(filename)
        self._getXMLSchedule()
        self.spectra = self._flattenXML(self.xml)
        self._attachNodeIDs()
        self._removeEmptyNodes()        
        self._getSpectrumMetadataFromSQL()  
        self._checkEncoding()
        self._appendSignalData()
        
        if len(self.individual_scans) != 0:
            self._insertIndividualScans()
        
        self._convertToCommonFormat()
        self.con.close()
        
        if 'remove_align' in kwargs.keys():
            if kwargs['remove_align']:
                self._removeFixedEnergies()
                
        if 'remove_syntax' in kwargs.keys():
            if kwargs['remove_syntax']:
                self._removeSyntax()
            else:
                pass
        else:
            self._removeSyntax()
        
        self._removeSnapShot()
        self._reindexSpectra()
        self._reindexGroups()

        return self.spectra
    
    def _getXMLSchedule(self):
        """Parse the schedule into an XML object."""
        self.con=sqlite3.connect(self.sql_connection)
        cur=self.con.cursor()
        query = 'SELECT Value FROM Configuration WHERE Key="Schedule"'
        cur.execute(query)
        XML = xml.fromstring(cur.fetchall()[0][0])
        self.xml = XML
        
    def _appendSignalData(self):
        """Get the signal data and attach to each spectrum."""
        self.individual_scans = []
        for idx, spectrum in enumerate(self.spectra): 
            node_id = self._getSQLNodeID(spectrum['spectrum_id'])
            n_channels = self._checkEnergyChannels(node_id)
            raw_ids = self._getRawIDs(node_id)
            n_scans = len(raw_ids)
            if n_scans > 1:
                signal_data = []
                for raw_id in raw_ids:
                    signal_data += [self._getOneScan(raw_id)]
                if self.average_scans:
                    signal_data = [float(sum(col)/len(col)) for col in zip(*signal_data)]
                    if n_channels > 1:
                        signal_data = self._sumChannels(signal_data,n_channels)
                    spectrum['y'] = signal_data
                else:
                    for scan in signal_data:
                        if n_channels > 1:
                            scan = self._sumChannels(scan,n_channels)
                            spectrum['y'] = scan
                            spectrum['scans']=1
                        else:
                            spectrum['y'] = scan
                            spectrum['scans']=1
                        self.individual_scans += [[copy(spectrum),idx]]
            else:
                signal_data = self._getOneScan(raw_ids[0])
                if n_channels > 1:
                    signal_data = self._sumChannels(signal_data,n_channels)
                spectrum['y'] = signal_data
        
    def _insertIndividualScans(self):
        """Insert individual scans in the order they were measured.
        
        The number of items in self.spectra is first determined from the 
        number of spectrum nodes in the XML file. The number of spectrum
        nodes is not necessarily the same as the number of spectra in the
        sle file. If individual scans were saved separately, then each 
        spectrum node might have multiple scans. If 'average_scans' was not
        chosen to be true in the converter, then the user wants to keep each
        individual scan. In this case, we need to duplcate the metadata for
        each scan and append the individual scans at the correct indices 
        of the self.spectra list.
        """
        ids = list(set([i[1] for i in self.individual_scans]))
        for idx in reversed(ids):
            spectra = [i[0] for i in self.individual_scans if i[1] == idx]
            for spectrum in reversed(spectra):
                spectrum = copy(spectrum)
                spectrum['scans'] = 1
                insert_idx = idx+1
                self.spectra.insert(insert_idx, spectrum)
            self.spectra.pop(idx)
                                           
    def _checkEnergyChannels(self, node_id):
        """Get the number of separate energy channels for the spectrum.
        
        This checks to see if the spectrum was saved with separated energy 
        channels.
        """
        self.con=sqlite3.connect(self.sql_connection)
        cur=self.con.cursor()
        query = 'SELECT EnergyChns FROM Spectrum WHERE Node="{}"'.format(node_id)
        cur.execute(query)
        result = cur.fetchall()
        if len(result) != 0:
            n_channels = result[0][0]
        return n_channels
    
    def _getRawIDs(self, node_id):
        """Get the raw IDs from SQL.
        
        There is one raw_id for each individual scan when scans were not
        already averaged in the sle file.
        To know which rows in the detector data table belong to which scans, 
        one needs to first get the raw_id from the RawData table.
        """
        self.con=sqlite3.connect(self.sql_connection)
        cur=self.con.cursor()
        query = 'SELECT RawId FROM RawData WHERE Node="{}"'.format(node_id)
        cur.execute(query)
        return [i[0] for i in cur.fetchall()]
    
    def _checkNumberOfScans(self, node_id):
        """Get the number of separate scans for the spectrum."""
        self.con=sqlite3.connect(self.sql.connection)
        cur=self.con.cursor()
        query = 'SELECT RawId FROM RawData WHERE Node="{}"'.format(node_id)
        cur.execute(query)
        return len(cur.fetchall())
        
    def _getDetectorData(self, node_id):
        """Get the detector data from sle file.
        
        The detector data is stored in the SQLite database as a blob.
        To know which blobs belong to which scans, one needs to first get the
        raw_id from the RawData table.
        """
        self.con=sqlite3.connect(self.sql_connection)
        cur=self.con.cursor()
        query = 'SELECT RawID FROM RawData WHERE Node="{}"'.format(node_id)
        cur.execute(query)
        raw_ids = [i[0] for i in cur.fetchall()]
        detector_data = []
        if len(raw_ids)>1:
            for raw_id in raw_ids:
                detector_data += [self._getOneScan(raw_id)]
        else:
            raw_id = raw_ids[0]
            detector_data = self._getOneScan(raw_id)
        
        return detector_data

    def _getOneScan(self,raw_id):
        """Get the detector data for a single scan and convert it to float.
        
        The detector data is stored in the SQLite database as a blob.
        This function decodes the blob into python float. The blob can be
        enoded as float or double in the SQLite table.
        """
        self.con=sqlite3.connect(self.sql_connection)
        cur=self.con.cursor()
        query = 'SELECT Data, ChunkSize FROM CountRateData WHERE RawId="{}"'.format(raw_id)
        cur.execute(query)
        results = cur.fetchall()
        buffer = self.encoding[1]
        encoding = self.encoding[0]
        stream = []
        for result in results:        
            length = result[1] * buffer
            data = result[0]
            for i in range(0,length,buffer):
                stream.append(struct.unpack(encoding,data[i:i+buffer])[0])        
        return stream

    def _parseExternalChannels(self, channel):
        """Parse additional external channels."""
        if len(channel) != 0:
            pass      

    def _getSpectrumMetadataFromSQL(self):
        """Get the metadata stored in the SQLite Spectrum table."""
        for spectrum in self.spectra: 
            node_id = self._getSQLNodeID(spectrum['spectrum_id'])
            self.con=sqlite3.connect(self.sql_connection)
            cur=self.con.cursor()
            query = 'SELECT * FROM Spectrum WHERE Node="{}"'.format(node_id)
            cur.execute(query)
            results = cur.fetchall()
            if len(results) != 0:
                results = results[0]
            
            column_names = self.spectrum_column_names
            combined = {k:v for k,v in dict(zip(column_names, results)).items() 
                        if k in self.sql_metadata_map.keys()}
            combined = copy(combined)
            if 'EnergyType' not in combined.keys():
                combined['EnergyType'] = 'Binding'
            for k,v in combined.items():
                spectrum[k] = v
                
            query = 'SELECT Data FROM NodeData WHERE Node="{}"'.format(node_id)
            cur.execute(query)
            results = xml.fromstring(cur.fetchall()[0][0])
            for i in results.iter('AnalyzerSpectrumParameters'):
                spectrum['workfunction'] = i.attrib['Workfunction']
                spectrum['step_size'] = float(i.attrib['ScanDelta'])
            
    def _getSQLNodeID(self,xml_id):
        """Get the SQL internal ID for the NodeID taken from XML.
        
        Sometimes the NodeID used in XML does not eaxtly map to the IDs for
        Spectra in the SQL tables. To fix this, there is a node mapping.
        """
        self.con=sqlite3.connect(self.sql_connection)
        cur = self.con.cursor()
        query = 'SELECT Node FROM NodeMapping WHERE InternalID="{}"'.format(xml_id)
        cur.execute(query)
        node_id = cur.fetchall()[0][0]
        return node_id
    
    def _attachNodeIDs(self):
        """Attach the node_id to each spectrum in the spectra list."""
        for spectrum in self.spectra:
            xml_id = spectrum['spectrum_id']
            node_id = self._getSQLNodeID(xml_id)
            spectrum['node_id'] = node_id
            
    def _removeEmptyNodes(self):
        """Remove entries from spectra list that have no spectrum in SQLite."""
        for j in reversed([i for i in enumerate(self.spectra)]):
            idx = j[0]
            spectrum = j[1] 
            node_id = spectrum['node_id']
            self.con=sqlite3.connect(self.sql_connection)
            cur = self.con.cursor()
            query = 'SELECT Node FROM Spectrum WHERE Node="{}"'.format(node_id)
            cur.execute(query)
            result = cur.fetchall()
            if len(result) == 0:
                del self.spectra[idx]

    def _getXData(self, spectrum):
        """Create an array of x values."""
        if spectrum['x_units'] == 'binding energy':
            start = spectrum['start_energy']
            step = spectrum['step_size']
            points = spectrum['n_values']
            x = [start - i*step for i in range(points)]
        elif spectrum['x_units'] == 'kinetic energy':
            start = spectrum['start_energy']
            step = spectrum['step_size']
            points = spectrum['n_values']
            x = [start + i*step for i in range(points)]
        return x

    def _getTableNames(self):
        """Get a list of table names in the current database file."""
        self.con=sqlite3.connect(self.sql_connection)
        cur = self.con.cursor()
        cur.execute('SELECT name FROM sqlite_master WHERE type= "table"')
        data = [i[0] for i in cur.fetchall()]
        return data
   
    def _getColumnNames(self, table_name):
        """Get the names of the columns in the table."""
        self.con=sqlite3.connect(self.sql_connection)
        cur=self.con.cursor()
        cur.execute(('SELECT * FROM {}').format(table_name))
        names = [description[0] for description in cur.description]
        return names

    def _close(self):
        """Close the database connection."""
        self.con.close()
        
    def _convertDateTime(self, timestamp):
        """Convert the native time format to the one we decide to use."""
        date_time = datetime.strptime(timestamp, '%Y-%b-%d %H:%M:%S.%f')
        date_time = datetime.strftime(date_time, '%Y-%m-%d %H:%M:%S.%f')
        return date_time
    
    def _reMapKeys(self, dictionary, key_map):
        """Map the keys returned from the SQL table to the preferred keys."""
        keys = [k for k in key_map.keys()]
        for k in keys:
            if k in dictionary.keys():
                dictionary[key_map[k]] = dictionary.pop(k)
        return dictionary
    
    def _dropUnusedKeys(self, dictionary, keys_to_drop):
        """Remove any keys parsed from sle that are not needed."""
        for key in keys_to_drop:
            if key in dictionary.keys():
                dictionary.pop(key)
    
    def _changeEnergyType(self, energy):
        """Change the strings for energy type to the preferred format."""
        if energy == 'Binding':
            return 'binding energy'
        elif energy == 'Kinetic':
            return 'kinetic energy'
        
    def _reMapValues(self, dictionary):
        """Map the values returned from the SQL table to the preferred format."""
        for k,v in self.value_map.items():
            dictionary[k] = v(dictionary[k])
        return dictionary
    
    def _sumChannels(self, data, n):
        """Sum together energy channels."""
        n_points = int(len(data)/n)
        summed = np.sum(np.reshape(np.array(data),(n_points,n)),axis=1)
        return summed.tolist()
    
    def _checkEncoding(self):
        """Check whether the binary data should be decoded float or double."""
        self.con=sqlite3.connect(self.sql_connection)
        cur=self.con.cursor()
        query = 'SELECT LENGTH(Data),ChunkSize FROM CountRateData LIMIT 1'
        cur.execute(query)
        result =cur.fetchall()[0]
        chunksize = result[1] 
        data = result[0]
        #print(chunksize)
        #print(data)
        if data / chunksize == 4:
            #print('buffer = 4')
            self.encoding = self.encodings_map['float']
        elif data / chunksize == 8:
            #print('buffer = 8')
            self.encoding = self.encodings_map['double']
        else:
            print('This binary encoding is not supported.')
        #print(self.encoding)
      
    def _flattenXML(self, xml):
        """Flatten the nested XML structure, keeping only the needed metadata."""
        collect = []
        for measurement_type in self.measurement_types:
            for i in xml.iter(measurement_type):
                data = {}
                data['analysis_method'] = measurement_type
                data['devices']=[]
                
                for j in i.iter('DeviceCommand'):
                    settings = {}
                    for k in j.iter('Parameter'):
                        settings[k.attrib['name']] = k.text
                        data.update(copy(settings))
                        
                    data['devices'] += [j.attrib['DeviceType']]
                        
                    #data['devices'] += [{'device_type' : j.attrib['DeviceType'],
                    #                     'settings':settings}]
                for j in i.iter('SpectrumGroup'):
                    data['group_name']=j.attrib['Name']
                    data['group_id']=j.attrib['ID']
                    settings = {}
                    for k in j.iter('CommonSpectrumSettings'):
                        for l in k.iter():
                            if l.tag == 'ScanMode':
                                settings[l.tag] = l.attrib['Name']
                            elif l.tag == 'SlitInfo':
                                for key,val in l.attrib.items():
                                    settings[key] = val
                            elif l.tag == 'Lens':
                                settings.update(l.attrib)
                            elif l.tag == 'EnergyChannelCalibration':
                                settings['calibration_file'] = l.attrib['File']
                            elif l.tag == 'Transmission':
                                settings['transmission_function'] = l.attrib['File']
                            elif l.tag == 'Iris':
                                settings['iris_diameter'] = l.attrib['Diameter']
                    data.update(copy(settings))
                    for k in j.iter('Spectrum'):
                        data['spectrum_id'] = k.attrib['ID']
                        data['spectrum_type'] = k.attrib['Name']
                        settings = {}
                        for l in k.iter('FixedEnergiesSettings'):
                            settings['dwell_time'] = float(l.attrib['DwellTime'])
                            settings['start_energy'] = float(copy(l.attrib['Ebin']))
                            settings['pass_energy'] = float(l.attrib['Epass'])
                            settings['lens_mode'] = l.attrib['LensMode']
                            settings['scans'] = int(l.attrib['NumScans'])
                            settings['n_values'] = int(l.attrib['NumValues'])
                            settings['end_energy'] = float(l.attrib['End'])
                            settings['scans'] = int(l.attrib['NumScans'])
                            settings['excitation_energy'] = float(l.attrib['Eexc'])
                            settings['step_size'] = ((settings['start_energy'] 
                                                     - settings['end_energy'])
                                                     / (settings['n_values']-1))
                        for l in k.iter('FixedAnalyzerTransmissionSettings'):
                            settings['dwell_time'] = float(l.attrib['DwellTime'])
                            settings['start_energy'] = float(copy(l.attrib['Ebin']))
                            settings['pass_energy'] = float(l.attrib['Epass'])
                            settings['lens_mode'] = l.attrib['LensMode']
                            settings['scans'] = int(l.attrib['NumScans'])
                            settings['n_values'] = int(l.attrib['NumValues'])
                            settings['end_energy'] = float(l.attrib['End'])
                            settings['scans'] = int(l.attrib['NumScans'])
                            settings['excitation_energy'] = float(l.attrib['Eexc'])
                            settings['step_size'] = ((settings['start_energy'] 
                                                     - settings['end_energy'])
                                                     / (settings['n_values']-1))
                        data.update(copy(settings))
                        collect+=[copy(data)]
        return collect
    
    def _reindexSpectra(self):
        """Re-number the spectrum_id."""
        for idx, spectrum in enumerate(self.spectra):
            spectrum['spectrum_id'] = idx
            
    def _reindexGroups(self):
        """Re-number the group_id."""
        group_ids = list(set([spec['group_id'] for spec in self.spectra]))
        for idx, group_id in enumerate(group_ids):
            for spec in self.spectra:
                if int(spec['group_id']) == int(group_id):
                    spec['group_id'] = copy(idx)
        
    def _convertToCommonFormat(self):
        """Reformat spectra into the format needed for the Converter object."""
        maps = {}
        for m in self.key_maps:
            maps.update(m)        
        for spec in self.spectra:
            self._reMapKeys(spec, maps)
            self._reMapValues(spec)
            self._dropUnusedKeys(spec, self.keys_to_drop)
            spec['data'] = {}
            spec['data']['x'] = self._getXData(spec)
            spec['data']['y'] = spec.pop('y')
            spec['y_units'] = 'Counts per Second'
        
    def _removeFixedEnergies(self):
        """Remove spectra measured with the scan mode FixedEnergies."""
        self.spectra = [spec for spec in self.spectra 
                        if spec['scan_mode']!='FixedEnergies']
        
    def _removeSyntax(self):
        """Remove the extra syntax in the group name."""
        for spectrum in self.spectra:
            new_name = spectrum['group_name'].split('#',1)[0]
            new_name = new_name.rstrip(', ')
            spectrum['group_name'] = new_name     

    def _removeSnapShot(self):
        self.spectra = [spec for spec in self.spectra 
                        if 'Snapshot' not in spec['scan_mode']]
        
    def getSLEVersion(self):
        """Parse the schedule into an XML object."""
        self.con=sqlite3.connect(self.sql_connection)
        cur=self.con.cursor()
        query = 'SELECT Value FROM Configuration WHERE Key=="Version"'
        cur.execute(query)
        version = cur.fetchall()[0][0]
        return version

#%%
if __name__ == '__main__': 
    folder = r"C:\\Users\\Mark\\ownCloud\\Muelheim Group\\Projects\\sle_converter\\data\\"
    file ='20150424_Ag111_vac_ramp.sle'
    filelocation = folder + file
    sle = ProdigyParserV1()
    s = sle.parseFile(filelocation, average_scans=True, remove_align=True, remove_syntax = True) 
    
    for spec in s:
        if 'step_size' not in spec.keys():
            print('no step ' + str(spec['spectrum_id']))

    


#%%

    spectrum_id = 5
    spectra_to_plot = [spectrum for spectrum in s if int(spectrum['spectrum_id'])==spectrum_id]
    print(len(spectra_to_plot))
    for spec in spectra_to_plot:
        plt.plot(spec['x'], spec['y'])
