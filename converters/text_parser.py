# -*- coding: utf-8 -*-
"""
Created on Mon Aug 10 10:15:57 2020

@author: Mark
"""
import numpy as np

class TextParser():
    """Parser for ASCI files exported from CasaXPS."""
    
    def __init__(self, **kwargs):
        if 'n_headerlines' in kwargs.keys():
            self.n_headerlines = kwargs['n_headerlines']
        else:
            self.n_headerlines = 4
        self.data_dict = []
            
    def parseFile(self, filepath):
        """Parse the file into a list of dictionaries.
        
        Parsed data stored in the attribute 'self.data'.
        """
        self._readLines(filepath)
        self._parseHeader()
        return self._buildDict()
    
    def _readLines(self, filepath):
        self.data = []
        self.filepath = filepath
        with open(filepath) as fp:
            for line in fp:
               self.data += [line]
   
    def _parseHeader(self):
        self.header = self.data[:self.n_headerlines]
        self.data = self.data[self.n_headerlines:]
        
    def _buildDict(self):
        lines = np.array([[float(i) for i in d.split()] for d in self.data])
        x = lines[:,0]
        y = lines[:,2]
        x,y = self._checkStepWidth(x,y)
        spect = {'data':{'x':list(x), 'y':list(y)}}
        self.data_dict += [spect]
        return self.data_dict
            
    def _checkStepWidth(self, x, y):
        """Check to see if a non-uniform step width is used in the spectrum."""
        start = x[0]
        stop = x[-1]
        x1 = np.roll(x,-1)
        diff = np.abs(np.subtract(x,x1))
        step = round(np.min(diff[diff!=0]),2)
        if (stop-start)/step > len(x):
            x, y = self._interpolate(x, y, step)
        return x, y
    
    def _interpolate(self, x, y, step):
        """Interpolate data points in case a non-uniform step width was used."""
        new_x = []
        new_y = []
        for i in range(len(x)-1):
            diff = np.abs(np.around(x[i+1]-x[i],2))
            if (diff > step) & (diff < 10):
                for j in range(int(np.round(diff/step))):
                    new_x += [x[i] + j*step]
                    k = j / int(diff/step)
                    new_y += [y[i]*(1-k) + y[i+1]*k]
            else:
                new_x += [x[i]]
                new_y += [y[i]]
                
        new_x += [x[-1]]
        new_y += [y[-1]]
        x = new_x
        y = np.array(new_y)
        return x, y