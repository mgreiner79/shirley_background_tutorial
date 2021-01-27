# -*- coding: utf-8 -*-
"""
Created on Wed Jan 13 14:15:11 2021

@author: Mark
"""
class Spectrum():
    
    def __init__(self):
        self.settings = Settings()
        self.meta = Meta()
        self.measurement_data = [MeasurementData()]
        
class MeasurementData():
    
    def __init__(self):
        self.name = ''
        self.units = ''
        self.shape = []
        self.values = []
        
class RegularMeasurementData(MeasurementData):
    
    def __init__(self):
        super().__init__()
        self.start = ''
        self.stop = ''
        self.step = []
        
    def generate_values(self):
        self.values = [self.start, self.stop, self.step]
        
class IrregularMeasurementData(MeasurementData):
    
    def __init__(self):
        super().__init__()
     
class MeasurementDataArray():
    
    def __init__(self):
        self.name = []
        self.units = []
        self.shape = []
        self.values = []

class Settings():
    
    def __init__(self):
        self.dwell_time = ''
        self.emission_current = ''
        self.excitation_energy = ''
        self.entrance_slit = ''
        self.exit_slit = ''
        self.pass_energy = ''
        self.source_voltage = ''
        self.voltage_range = ''
        self.workfunction = ''
        self.iris_diameter = ''
        self.lens_mode = ''
        self.calibration_file = ''
        self.scans = ''
        self.transmission_function
    
class Meta():
    
    def __init__(self):
        self.method = ''
        self.users = ''
        self.sample = ''
        self.group_name = ''
        self.group_id = ''
        self.spectrum_id = ''
        self.time_stamp = ''
        self.devices = ''
        self.spectrum_type = ''
        
reg = RegularMeasurementData()    
        
        