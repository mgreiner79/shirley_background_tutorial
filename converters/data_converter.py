# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 11:32:48 2020

@author: Mark
"""

from converters.vamas_parser import VamasParser

class DataConverter():
    """Converter for reading and writing several XPS files types.
    
    Supported input formats: 'Vamas',
    """
    
    def __init__(self):
        """Construct Converter.
        
        Map the keywords to the supported parsers and writers.
        All parsers should expose method parseFile(filename).
        All writers should expose the method write(filename).
        """
        self._parser_methods = {'Vamas': VamasParser,}
        self._write_methods = {'JSON':JSONWriter,
                               'Vamas':VamasWriter,
                               'Excel':ExcelWriter}
        self._extensions = {'vms': 'Vamas',}
        
    def load(self, filename, **kwargs):
        """Parse an input file an place it into a nested dictionary.

        Parameters
        ----------
        filename: STRING
            The location and name of the file you wish to parse.
        **kwargs: 
            in_format: The file format of the loaded file.
        """
        if 'in_format' not in kwargs.keys():
            in_format = self._extensions[filename.rsplit('.',1)[-1].lower()]
            print(in_format)
        else:
            in_format = kwargs['in_format']
        
        self.parser = self._parser_methods[in_format]()
        self.data = self.parser.parseFile(filename, **kwargs)
        '''try:
            self.parser = self._parser_methods[in_format]()
            self.data = self.parser.parseFile(filename)
            
        except:
            print("input file format not supported")'''
           
