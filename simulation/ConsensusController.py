'''
Created on 30.05.2018

@author: Mikhail Aristov
'''
from encryption import Paillier
from simulation import SimParameters as PARAM

class ConsensusController(object):
    '''
    classdocs
    '''

    def __init__(self, System, SensorGrid):
        '''
        Constructor
        '''
        self.MySystem = System
        self.MyGrid = SensorGrid
        
        self.MostRecentPosition = 0
        self.MostRecentEstimate = 0
        self.QuantizedEstimate = 0
        self.UnquantizedEstimate = 0
        self.EncryptedEstimate = 0
        self.DecryptedEstimate = 0
        self.LastSensorQueried = None
        
        # From the security standpoint, the server must generate its own key pair, but for this simulation,
        # we hard-wire a simple 192-bit key (not secure in any form or shape!) for performance reasons
        self.pk, self.sk = Paillier.KeyGenFromPrimes(282174488599599500573849980909, 362736035870515331128527330659)
        self.MyGrid.DistributePublicKey(self.pk)
    
    def FetchEstimate(self, FromSensor):
        self.LastSensorQueried = FromSensor
        self.MostRecentPosition = self.MySystem.CurrentPos
        self.MostRecentEstimate = FromSensor.MostRecentEstimate
        self.QuantizedEstimate = FromSensor.QuantMostRecentEstimate
        self.UnquantizedEstimate = self.Unquantize(self.QuantizedEstimate)
        if not PARAM.DO_NOT_ENCRYPT:
            self.EncryptedEstimate = FromSensor.EncMostRecentEstimate
            self.DecryptedEstimate = self.DecryptAndUnquantize(self.EncryptedEstimate)
        return self.MostRecentEstimate, self.DecryptedEstimate
    
    def FetchEstimateFromCenter(self):
        return self.FetchEstimate(self.MyGrid.GetRandomSensor())
    
    def FetchRandomEstimate(self):
        return self.FetchEstimate(self.MyGrid.GetCentralSensor())
    
    def FetchEstimateFromSameSensor(self):
        return self.FetchEstimate(self.LastSensorQueried)
    
    def Unquantize(self, QuantizedEstimate):
        return float(QuantizedEstimate / PARAM.MEAS_QUANTIZATION_FACTOR / pow(PARAM.WEIGHT_QUANTIZATION_FACTOR, PARAM.CONSENSUS_ROUND_COUNT))
    
    def DecryptAndUnquantize(self, ciphertext):
        assert(not PARAM.DO_NOT_ENCRYPT)
        plaintext = Paillier.Decrypt(self.sk, ciphertext)
        return self.Unquantize(plaintext)

    def GetSquaredError(self):
        return (self.MostRecentEstimate - self.MostRecentPosition) * (self.MostRecentEstimate - self.MostRecentPosition)
    
    def GetQuantizedSquaredError(self):
        return (self.UnquantizedEstimate - self.MostRecentPosition) * (self.UnquantizedEstimate - self.MostRecentPosition)
    
    def GetDecryptedSquaredError(self):
        assert(not PARAM.DO_NOT_ENCRYPT)
        return (self.DecryptedEstimate - self.MostRecentPosition) * (self.DecryptedEstimate - self.MostRecentPosition)