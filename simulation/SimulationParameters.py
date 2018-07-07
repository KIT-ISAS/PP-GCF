'''
Created on 30.05.2018

@author: Mikhail Aristov
'''

class SimParameters(object):
    '''
    A convenience class for bundling all simulation settings.
    '''
    
    # Whether parallel processing should be attempted
    TRY_MULTIPROCESSING = True
    
    # Whether to actually encrypt communications (or to just evaluate the quantization, for performance reasons)
    DO_NOT_ENCRYPT = False
    
    # How many runs in total the simulation should include
    TOTAL_RUNS = 1000
    
    # How many agent runs in total the simulation should include
    TIME_STEPS_PER_RUN = 50
    
    # Fractional precision of pre-encryption quantization of measurements
    MEAS_QUANTIZATION_FACTOR_8  = 2**8
    MEAS_QUANTIZATION_FACTOR_16 = 2**16
    MEAS_QUANTIZATION_FACTOR_24 = 2**24
    MEAS_BIT_SIZE = 32
    
    # Fractional precision of pre-encryption quantization of weights
    WEIGHT_BIT_PRECISION = 7 # bits
    WEIGHT_QUANTIZATION_FACTOR = 2 ** WEIGHT_BIT_PRECISION
    WEIGHT_BIT_SIZE = 8
    
    # The length of the encryption key (for test purposes only, no real security guarantee!)
    PLAINTEXT_MODULUS_BIT_SIZE = 192 # bits
    
    # How many rounds the consensus filter runs for (dependent on the bit sizes of the plaintext modulus, measurements, and weights)
    CONSENSUS_ROUND_COUNT = int((PLAINTEXT_MODULUS_BIT_SIZE - MEAS_BIT_SIZE) / WEIGHT_BIT_SIZE)
    
    # Where the simulated system is placed at time step zero
    SYSTEM_INITIAL_STATE = 100.0
    
    # The variance of the Guassian noise that is applied to simulate the system's random walk
    SYSTEM_RANDOM_WALK_SIGMA = 2.5
    
    # A tuple definining how many sensors are placed along the X and Y axes of the sensor grid
    SENSOR_GRID_DIMENSIONS = (8, 8)
    
    # The variance of "good" vs. "bad" sensors, just to mix it up a little
    SENSOR_MEASUREMENT_VARIANCE = 5.0
    
    # The relative weight of the sensor's own estimate during estimate fusion
    OWN_ESTIMATE_WEIGHT = 0.2 # interval: [0.0, 1.0]