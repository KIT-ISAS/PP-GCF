'''
Created on 30.05.2018

@author: Mikhail Aristov
'''
from random import choice
from numpy import array, ndarray
from simulation import SimSensor, SimParameters as PARAM
        
class ConSensorGrid(object):
    '''
    classdocs
    '''

    def __init__(self, GridSize):
        '''
        Constructor
        '''
        self.SensorCount, self.MySizeX, self.MySizeY = GridSize[0] * GridSize[1], GridSize[0], GridSize[1]
        # Instatiate all sensors first
        self.MySensors = []
        for i in range(self.SensorCount):
            newSensor = SimSensor(self, i, PARAM.SENSOR_GOOD_VARIANCE if i % 2 == 1 else PARAM.SENSOR_BAD_VARIANCE)
            self.MySensors.append(newSensor)
        # Connect sensors with their neighbors
        for s in self.MySensors:
            for nID in self.GetNeighborIDs(s.MyID):
                s.AddNeighborID(nID)
            s.UpdateNeighborEstimateWeights()
            
    def DistributePublicKey(self, pk):
        for s in self.MySensors:
            s.SetEncryptionKey(pk)
    
    def GetSensorByID(self, SensorID):
        return self.MySensors[SensorID]
    
    def GetRandomSensor(self):
        return choice(self.MySensors)
    
    def GetCentralSensor(self):
        middleSensorID = self.SensorCount // 2
        return self.MySensors[middleSensorID if self.SensorCount % 2 == 1 else middleSensorID - self.MySizeX // 2]
    
    def GetNeighborIDs(self, SensorID):
        '''
        Returns the (linear) IDs of the sensor node's direct neighbors (including its own) in the specified grid
        '''
        return [j for i in range(SensorID - self.MySizeX, SensorID + self.MySizeX + 1, self.MySizeX) 
                  for j in range(i - 1, i + 2)
                  if j >= 0 and j < self.SensorCount and abs(i % self.MySizeX - j % self.MySizeX) <= 1]
        
    def TakeAllMeasurements(self, RealPos):
        for s in self.MySensors:
            s.TakeMeasurement(RealPos)
            
    def ExecuteConsensusRound(self):
        # Make all sensors send their current estimates to their neighbors
        for s in self.MySensors:
            s.SendCurrentEstimateToNeighbors()
        # Then make all sensors fuse the estimates they received into their estimates
        for s in self.MySensors:
            s.FuseNeighborEstimates()
            s.FuseQuantizedNeighborEstimates()
            if not PARAM.DO_NOT_ENCRYPT:
                s.FuseEncryptedNeighborEstimates()
            
    def GetAllCurrentEstimates(self):
        buffer = array([s.MostRecentEstimate for s in self.MySensors], dtype=float)
        return ndarray(shape = (self.MySizeX, self.MySizeY), buffer = buffer)
            
    def GetCurrentErrors(self, RealPos):
        buffer = array([s.MostRecentEstimate - RealPos for s in self.MySensors], dtype=float)
        return ndarray(shape = (self.MySizeX, self.MySizeY), buffer = buffer)
            
    def GetCurrentEstimateDeviations(self):
        estimates = self.GetAllCurrentEstimates()
        meanEstimate = estimates.mean()
        return estimates - meanEstimate