'''
Created on 30.05.2018

@author: Mikhail Aristov
'''
from math import log2
from numpy.random import normal as Gauss
from encryption import Paillier
from simulation import SimParameters as PARAM

class ConSensor(object):
    '''
    classdocs
    '''

    def __init__(self, Grid, SensorID, MeasurementNoise):
        '''
        Constructor
        '''
        # Grid details
        self.MyGrid = Grid
        self.MyID = SensorID
        self.MyNeighbors = []
        # Internal sensor parameters
        self.MeasurementNoiseSigma = MeasurementNoise
        self.NeighborWeights = {}
        self.QuantizedNeighborWeights = {}
        # Round-specific data
        self.MostRecentMeasurement = 0.0
        self.MostRecentEstimate = 0.0
        
        self.Q08MostRecentEstimate = 0
        self.Q16MostRecentEstimate = 0
        self.Q24MostRecentEstimate = 0
        self.EncMostRecentEstimate = 0
        
        self.CurrentNeighborEstimates = {}
        self.Q08NeighborEstimates = {}
        self.Q16NeighborEstimates = {}
        self.Q24NeighborEstimates = {}
        self.EncryptedNeighborEstimates = {}
        
    def AddNeighborID(self, NeighborID):
        if NeighborID not in self.MyNeighbors:
            self.MyNeighbors.append(NeighborID)
            
    def UpdateNeighborEstimateWeights(self):
        '''
        Sets the weight of own estimate to a fixed value and all other weights equal to each other.
        '''
        self.NeighborWeights.clear()
        for nID in self.MyNeighbors:
            self.NeighborWeights[nID] = PARAM.OWN_ESTIMATE_WEIGHT if nID == self.MyID else ((1.0 - PARAM.OWN_ESTIMATE_WEIGHT) / (len(self.MyNeighbors) - 1))
            self.QuantizedNeighborWeights[nID] = self.Quantize(self.NeighborWeights[nID], PARAM.WEIGHT_QUANTIZATION_FACTOR, PARAM.WEIGHT_BIT_SIZE)
        # Ensure all quantized weights add up to a single quantization factor
        self.QuantizedNeighborWeights[self.MyID] += PARAM.WEIGHT_QUANTIZATION_FACTOR - sum(self.QuantizedNeighborWeights.values())
        assert(PARAM.WEIGHT_QUANTIZATION_FACTOR == sum(self.QuantizedNeighborWeights.values()))
            
    def SetEncryptionKey(self, pk):
        self.pk = pk
            
    def GetMeasurement(self, RealState):
        return Gauss(RealState, self.MeasurementNoiseSigma)
    
    def Quantize(self, FloatingPointValue, QuantizationFactor, MaxBitLength):
        result = int(round(FloatingPointValue * QuantizationFactor, 0))
        assert(log2(result) <= MaxBitLength)
        return result
    
    def QuantizeMeasurement(self, MeasuredState, QuantizationFactor):
        return self.Quantize(MeasuredState, QuantizationFactor, PARAM.MEAS_BIT_SIZE)
    
    def EncryptQuantizedMeasurement(self, QuantizedState):
        return Paillier.Encrypt(self.pk, QuantizedState)
    
    def TakeMeasurement(self, RealState):#PARAM.MEAS_QUANTIZATION_FACTOR
        self.MostRecentMeasurement = self.GetMeasurement(RealState)
        self.MostRecentEstimate = self.MostRecentMeasurement
        # Quantize and encrypt it, too
        self.Q08MostRecentEstimate = self.QuantizeMeasurement(self.MostRecentEstimate, PARAM.MEAS_QUANTIZATION_FACTOR_8)
        self.Q16MostRecentEstimate = self.QuantizeMeasurement(self.MostRecentEstimate, PARAM.MEAS_QUANTIZATION_FACTOR_16)
        self.Q24MostRecentEstimate = self.QuantizeMeasurement(self.MostRecentEstimate, PARAM.MEAS_QUANTIZATION_FACTOR_24)
        if not PARAM.DO_NOT_ENCRYPT:
            self.EncMostRecentEstimate = self.EncryptQuantizedMeasurement(self.Q16MostRecentEstimate)
    
    def SendCurrentEstimateToNeighbors(self):
        for nID in self.MyNeighbors:
            n = self.MyGrid.GetSensorByID(nID)
            n.ReceiveNeighborEstimate(self.MyID, self.MostRecentEstimate)
            n.ReceiveQuantizedEstimate(self.MyID, self.Q08MostRecentEstimate, self.Q16MostRecentEstimate, self.Q24MostRecentEstimate)
            if not PARAM.DO_NOT_ENCRYPT:
                n.ReceiveEncryptedEstimate(self.MyID, self.EncMostRecentEstimate)
    
    def ReceiveNeighborEstimate(self, NeighborID, NeighborEstimate):
        assert(NeighborID in self.NeighborWeights)
        self.CurrentNeighborEstimates[NeighborID] = NeighborEstimate

    def ReceiveQuantizedEstimate(self, NeighborID, Q8Estimate, Q16Estimate, Q24Estimate):
        assert(NeighborID in self.NeighborWeights)
        self.Q08NeighborEstimates[NeighborID] = Q8Estimate
        self.Q16NeighborEstimates[NeighborID] = Q16Estimate
        self.Q24NeighborEstimates[NeighborID] = Q24Estimate

    def ReceiveEncryptedEstimate(self, NeighborID, EncryptedEstimate):
        assert(not PARAM.DO_NOT_ENCRYPT)
        assert(NeighborID in self.NeighborWeights)
        self.EncryptedNeighborEstimates[NeighborID] = EncryptedEstimate
        
    def FuseNeighborEstimates(self):
        self.MostRecentEstimate *= self.NeighborWeights[self.MyID]
        for nID in self.MyNeighbors:
            if nID == self.MyID:
                continue # It's already been add to the result before...
            assert(nID in self.CurrentNeighborEstimates)
            self.MostRecentEstimate += self.NeighborWeights[nID] * self.CurrentNeighborEstimates[nID]
        
    def FuseQuantizedNeighborEstimates(self):
        self.Q08MostRecentEstimate *= self.QuantizedNeighborWeights[self.MyID]
        self.Q16MostRecentEstimate *= self.QuantizedNeighborWeights[self.MyID]
        self.Q24MostRecentEstimate *= self.QuantizedNeighborWeights[self.MyID]
        for nID in self.MyNeighbors:
            if nID == self.MyID:
                continue # It's already been add to the result before...
            assert(nID in self.CurrentNeighborEstimates)
            self.Q08MostRecentEstimate += self.QuantizedNeighborWeights[nID] * self.Q08NeighborEstimates[nID]
            self.Q16MostRecentEstimate += self.QuantizedNeighborWeights[nID] * self.Q16NeighborEstimates[nID]
            self.Q24MostRecentEstimate += self.QuantizedNeighborWeights[nID] * self.Q24NeighborEstimates[nID]
        
    def FuseEncryptedNeighborEstimates(self):
        assert(not PARAM.DO_NOT_ENCRYPT)
        self.EncMostRecentEstimate = Paillier.Mult(self.pk, self.EncMostRecentEstimate, self.QuantizedNeighborWeights[self.MyID])
        for nID in self.MyNeighbors:
            if nID == self.MyID:
                continue # It's already been add to the result before...
            assert(nID in self.CurrentNeighborEstimates)
            weightedEstimate = Paillier.Mult(self.pk, self.EncryptedNeighborEstimates[nID], self.QuantizedNeighborWeights[nID])
            self.EncMostRecentEstimate = Paillier.Add(self.pk, self.EncMostRecentEstimate, weightedEstimate)