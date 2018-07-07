'''
Created on 30.05.2018

@author: Mikhail Aristov
'''
from numpy.random import normal as Gauss

class SimSystem(object):
    '''
    classdocs
    '''

    def __init__(self, InitPos, RandomWalkStepSigma):
        '''
        Constructor
        '''
        self.InitPos = InitPos
        self.PosChangeSigma = RandomWalkStepSigma
        self.Reset()
    
    def StepOnce(self):
        self.CurrentPos += Gauss(0, self.PosChangeSigma)
    
    def Reset(self):
        self.CurrentPos = self.InitPos