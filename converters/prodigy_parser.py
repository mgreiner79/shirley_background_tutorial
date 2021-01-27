# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 11:48:26 2020

@author: Mark
"""
from converters.prodigy_parser_v1 import ProdigyParserV1
from converters.prodigy_parser_v4 import ProdigyParserV4

import sqlite3

class ProdigyParser():
    def __init__(self):
        self.parsers = [ProdigyParserV1,ProdigyParserV4]
         
        self.versions_map ={}
        for parser in self.parsers:
            supported_versions = parser.supported_versions
            for version in supported_versions:
                self.versions_map[version] = parser
                
    def _getSLEVersion(self):
        """Parse the schedule into an XML object."""
        self.con=sqlite3.connect(self.sql_connection)
        cur=self.con.cursor()
        query = 'SELECT Value FROM Configuration WHERE Key=="Version"'
        cur.execute(query)
        version = cur.fetchall()[0][0]
        version = version.split('.')
        version = version[0] + "." + version[1].split('-')[0]
        return version
    
    def parseFile(self, filename, **kwargs):
        self.sql_connection = filename
        version = self._getSLEVersion()
        parser = self.versions_map[version]()
        return parser.parseFile(filename, **kwargs)
        
