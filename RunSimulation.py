'''
Created on 30.05.2018

@author: Mikhail Aristov
'''
import multiprocessing as mp
from numpy import sqrt
from simulation import SimSystem, SimGrid, SimController, SimParameters as PARAM

# Set parameters
#PARAM.DO_NOT_ENCRYPT = True

# Initialize the system, the sensor grid, and the controller
system = SimSystem(PARAM.SYSTEM_INITIAL_STATE, PARAM.SYSTEM_RANDOM_WALK_SIGMA)
grid = SimGrid(PARAM.SENSOR_GRID_DIMENSIONS)
controller = SimController(system, grid)

# Runs a simulation a specified number of times
def Simulation(runs, PID = None):
    EstimateCount, CumulativeError, CumulativeErrorNoFilter, CumulativeErrorEncrypted = 0, 0, 0, 0
    CumulativeErrorQ8, CumulativeErrorQ16, CumulativeErrorQ24 = 0, 0, 0
    for run in range(runs):
        if runs < 100 or run % (runs // 100) == 0:
            if PID is None:
                print("Running simulation #", run, "of", runs)
            else:
                print("Process #", PID, "is at", round(run/runs*100, 2), "%")
        
        system.Reset()
        # Update the system for N time steps
        TotalTimeSteps, ConsensusRoundCount = PARAM.TIME_STEPS_PER_RUN, PARAM.CONSENSUS_ROUND_COUNT
        for _ in range(TotalTimeSteps):
            # Evolve the system one step
            system.StepOnce()
            
            # Take all measurements
            grid.TakeAllMeasurements(system.CurrentPos)
            
            # Let the controller sample the unfiltered estimate error
            controller.FetchRandomEstimate()
            CumulativeErrorNoFilter += controller.GetSquaredError()
            
            # Perform K rounds of consensus filtering
            for _ in range(ConsensusRoundCount):
                grid.ExecuteConsensusRound()
            
            # Let the controller retrieve an estimate and return its SE
            controller.FetchEstimateFromSameSensor()
            CumulativeError += controller.GetSquaredError()
            E8, E16, E24 = controller.GetQuantizedSquaredErrors()
            CumulativeErrorQ8  += E8
            CumulativeErrorQ16 += E16
            CumulativeErrorQ24 += E24
            if not PARAM.DO_NOT_ENCRYPT:
                CumulativeErrorEncrypted += controller.GetDecryptedSquaredError()
            EstimateCount += 1

    return EstimateCount, CumulativeErrorNoFilter, CumulativeError, CumulativeErrorQ8, CumulativeErrorQ16, CumulativeErrorQ24, CumulativeErrorEncrypted

# A wrapper for the simulation function that lets it run in parallel
def ParallelSimulaton(PID, runs, globalEstCount, globalErrorNoFilter, globalErrorNoEnc, globalErrorQ8, globalErrorQ16, globalErrorQ24, globalErrorEnc):
    # Run the simulation
    EstimateCount, CumulativeErrorNoFilter, CumulativeError, CumulativeErrorQ8, CumulativeErrorQ16, CumulativeErrorQ24, CumulativeErrorEncrypted = Simulation(runs, PID=PID)
    # Synchronize the output
    with globalEstCount.get_lock():
        globalEstCount.value += EstimateCount
    with globalErrorNoFilter.get_lock():
        globalErrorNoFilter.value += CumulativeErrorNoFilter
    with globalErrorNoEnc.get_lock():
        globalErrorNoEnc.value += CumulativeError
    with globalErrorQ8.get_lock():
        globalErrorQ8.value += CumulativeErrorQ8
    with globalErrorQ16.get_lock():
        globalErrorQ16.value += CumulativeErrorQ16
    with globalErrorQ24.get_lock():
        globalErrorQ24.value += CumulativeErrorQ24
    with globalErrorEnc.get_lock():
        globalErrorEnc.value += CumulativeErrorEncrypted

if __name__ == '__main__':
    # Check for parallelization
    if PARAM.TRY_MULTIPROCESSING and mp.cpu_count() >= 4:
        # Leave a couple cores for the system
        parallelProcessCount = mp.cpu_count() - 2
        # Split the total number of experiments equally between processes
        experimentsPerProcess = PARAM.TOTAL_RUNS // parallelProcessCount
        # Prepare output structures for the processes
        syncEstimateCount, syncErrorNoFilter, syncErrorNoEnc, syncErrorEncrypted = mp.Value("i", 0), mp.Value("d", 0.0), mp.Value("d", 0.0), mp.Value("d", 0.0)
        syncErrorQ8, syncErrorQ16, syncErrorQ24 = mp.Value("d", 0.0), mp.Value("d", 0.0), mp.Value("d", 0.0)
        # Create the process objects
        processes = [mp.Process(target=ParallelSimulaton, args=(p, experimentsPerProcess, syncEstimateCount, syncErrorNoFilter, syncErrorNoEnc, syncErrorQ8, syncErrorQ16, syncErrorQ24, syncErrorEncrypted)) for p in range(parallelProcessCount)]
        
        # Run all processes in parallel
        [p.start() for p in processes]
        [p.join() for p in processes]
        
        # Finally, format the output
        EstimateCount = int(syncEstimateCount.value)
        RMSEwoFilter = sqrt(float(syncErrorNoFilter.value) / EstimateCount)
        RMSEwoEncrypt = sqrt(float(syncErrorNoEnc.value) / EstimateCount)
        RMSEwQuant8bit = sqrt(float(syncErrorQ8.value) / EstimateCount)
        RMSEwQuant16bit = sqrt(float(syncErrorQ16.value) / EstimateCount)
        RMSEwQuant24bit = sqrt(float(syncErrorQ24.value) / EstimateCount)
        RMSEwEncryption = sqrt(float(syncErrorEncrypted.value) / EstimateCount)
    else:
        EstimateCount, CumulativeErrorNoFilter, CumulativeError, CumulativeErrorQ8, CumulativeErrorQ16, CumulativeErrorQ24, CumulativeErrorEncrypted = Simulation(PARAM.TOTAL_RUNS)
        RMSEwoFilter = sqrt(CumulativeErrorNoFilter / EstimateCount)
        RMSEwoEncrypt = sqrt(CumulativeError / EstimateCount)
        RMSEwQuant8bit = sqrt(CumulativeErrorQ8 / EstimateCount)
        RMSEwQuant16bit = sqrt(CumulativeErrorQ16 / EstimateCount)
        RMSEwQuant24bit = sqrt(CumulativeErrorQ24 / EstimateCount)
        RMSEwEncryption = sqrt(CumulativeErrorEncrypted / EstimateCount)

    print("total estimates evaluated:", EstimateCount)
    print("gossip round count:", PARAM.CONSENSUS_ROUND_COUNT)
    print("RMSE w/o  encryption:        ", RMSEwoEncrypt)
    if not PARAM.DO_NOT_ENCRYPT:
        print("RMSE w/   encryption:        ", RMSEwEncryption)
    print("RMSE w/   8-bit quantization:", RMSEwQuant8bit)
    print("RMSE w/  16-bit quantization:", RMSEwQuant16bit)
    print("RMSE w/  24-bit quantization:", RMSEwQuant24bit)
    print("RMSE w/o filtering:          ", RMSEwoFilter)
    print("precision gain w/ reg. filtering:         ", RMSEwoFilter/RMSEwoEncrypt, "times")
    if PARAM.DO_NOT_ENCRYPT:
        print("precision gain w/ 16-bit quant. filtering:", RMSEwoFilter/RMSEwQuant16bit, "times")
        print("precision loss due to quantization:", RMSEwQuant16bit - RMSEwoEncrypt)
    else:
        print("precision gain w/ enc. filtering:         ", RMSEwoFilter/RMSEwEncryption, "times")
        print("precision loss due to encryption:", RMSEwEncryption - RMSEwoEncrypt)