# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 11:39:22 2020

@author: Mark
"""
    
class VamasHeader():
    """An object to store the Vamas header information."""
    
    def __init__(self):
        """Construct vamas header object."""
        self.formatID = 'VAMAS Surface Chemical Analysis Standard Data Transfer Format 1988 May 4'
        self.instituteID = 'Not Specified'
        self.instriumentModelID = 'Not Specified'
        self.operatorID = 'Not Specified'
        self.experimentID = 'Not Specified'
        self.noCommentLines = '2'
        self.commentLines = 'Casa Info Follows CasaXPS Version 2.3.22PR1.0\n0'
        self.expMode = 'NORM'
        self.scanMode = 'REGULAR'
        self.nrRegions = '0'
        self.nrExpVar = '1'
        self.expVarLabel = 'Exp Variable'
        self.expVarUnit = 'd'
        self.unknown3 = '0'
        self.unknown4 = '0'
        self.unknown5 = '0'
        self.unknown6 = '0'
        self.noBlocks = '1'
        
class Block():
    """An object to store a block of spectrum data and meta-data."""
    
    def __init__(self):
        """Construct a Block object.
        
        The values provided here are default values.
        The order in which the attributes are defined here is important for 
        the VamasWriter. Changing the order can result in a Vamas file that
        is un-readable.
        """
        self.blockID = ''
        self.sampleID = ''
        self.year = ''
        self.month = ''
        self.day = ''
        self.hour = ''
        self.minute = ''
        self.second = ''
        self.noHrsInAdvanceOfGMT = '0'
        self.noCommentLines = ''
        self.commentLines = '' #This list should contain one element per for each line in the comment block
        self.technique = ''
        self.expVarValue = ''
        self.sourceLabel = ''
        self.sourceEnergy = ''
        self.unknown1 = '0'
        self.unknown2 = '0'
        self.unknown3 = '0'
        self.sourceAnalyzerAngle = ''
        self.unknown4 = '180'
        self.analyzerMode = ''
        self.resolution = ''
        self.magnification = '1'
        self.workFunction = ''
        self.targetBias = '0'
        self.analyzerWidthX = '0'
        self.analyzerWidthY = '0'
        self.analyzerTakeOffPolarAngle = '0'
        self.analyzerAzimuth = '0'
        self.speciesLabel = ''
        self.transitionLabel = ''
        self.particleCharge = '-1'
        self.abscissaLabel = 'kinetic energy'
        self.abscissaUnits = 'eV'
        self.abscissaStart = ''
        self.abscissaStep = ''
        self.noVariables = '2'
        self.variableLabel1 = 'counts'
        self.variableUnits1 = 'd'
        self.variableLabel2 = 'Transmission'
        self.variableUnits2 = 'd'
        self.signalMode = 'pulse counting'
        self.dwellTime = ''
        self.noScans = ''
        self.timeCorrection = '0'
        self.sampleAngleTilt = '0'
        self.sampleTiltAzimuth = '0'
        self.sampleRotation = '0'
        self.noAdditionalParams = '2'
        self.paramLabel1 = 'ESCAPE DEPTH TYPE'
        self.paramUnit1 = 'd'
        self.paramValue1 = '0'
        self.paramLabel2 = 'MFP Exponent'
        self.paramUnit2 = 'd'
        self.paramValue2 = '0'
        self.numOrdValues = ''
        self.minOrdValue1 = ''
        self.maxOrdValue1 = ''
        self.minOrdValue2 = ''
        self.maxOrdValue2 = ''
        self.dataString = ''       