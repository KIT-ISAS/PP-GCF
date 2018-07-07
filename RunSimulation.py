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
    EstimateCount, CumulativeError, CumulativeErrorNoFilter, CumulativeErrorQuantized, CumulativeErrorEncrypted = 0, 0, 0, 0, 0
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
            CumulativeErrorQuantized += controller.GetQuantizedSquaredError()
            if not PARAM.DO_NOT_ENCRYPT:
                CumulativeErrorEncrypted += controller.GetDecryptedSquaredError()
            EstimateCount += 1

    return EstimateCount, CumulativeErrorNoFilter, CumulativeError, CumulativeErrorQuantized, CumulativeErrorEncrypted

# A wrapper for the simulation function that lets it run in parallel
def ParallelSimulaton(PID, runs, globalEstCount, globalErrorNoFilter, globalErrorNoEnc, globalErrorQuant, globalErrorEnc):
    # Run the simulation
    EstimateCount, CumulativeErrorNoFilter, CumulativeError, CumulativeErrorQuantized, CumulativeErrorEncrypted = Simulation(runs, PID=PID)
    # Synchronize the output
    with globalEstCount.get_lock():
        globalEstCount.value += EstimateCount
    with globalErrorNoFilter.get_lock():
        globalErrorNoFilter.value += CumulativeErrorNoFilter
    with globalErrorNoEnc.get_lock():
        globalErrorNoEnc.value += CumulativeError
    with globalErrorQuant.get_lock():
        globalErrorQuant.value += CumulativeErrorQuantized
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
        syncEstimateCount, syncErrorNoFilter, syncErrorNoEnc, syncErrorQuantized, syncErrorEncrypted = mp.Value("i", 0), mp.Value("d", 0.0), mp.Value("d", 0.0), mp.Value("d", 0.0), mp.Value("d", 0.0)
        # Create the process objects
        processes = [mp.Process(target=ParallelSimulaton, args=(p, experimentsPerProcess, syncEstimateCount, syncErrorNoFilter, syncErrorNoEnc, syncErrorQuantized, syncErrorEncrypted)) for p in range(parallelProcessCount)]
        
        # Run all processes in parallel
        [p.start() for p in processes]
        [p.join() for p in processes]
        
        # Finally, format the output
        EstimateCount = int(syncEstimateCount.value)
        RMSEwoFilter = sqrt(float(syncErrorNoFilter.value) / EstimateCount)
        RMSEwoEncrypt = sqrt(float(syncErrorNoEnc.value) / EstimateCount)
        RMSEwQuantization = sqrt(float(syncErrorQuantized.value) / EstimateCount)
        RMSEwEncryption = sqrt(float(syncErrorEncrypted.value) / EstimateCount)
    else:
        EstimateCount, CumulativeErrorNoFilter, CumulativeError, CumulativeErrorQuantized, CumulativeErrorEncrypted = Simulation(PARAM.TOTAL_RUNS)
        RMSEwoFilter = sqrt(CumulativeErrorNoFilter / EstimateCount)
        RMSEwoEncrypt = sqrt(CumulativeError / EstimateCount)
        RMSEwQuantization = sqrt(CumulativeErrorQuantized / EstimateCount)
        RMSEwEncryption = sqrt(CumulativeErrorEncrypted / EstimateCount)

    print("total estimates evaluated:", EstimateCount)
    print("RMSE w/o  encryption:", RMSEwoEncrypt)
    if not PARAM.DO_NOT_ENCRYPT:
        print("RMSE w/   encryption:", RMSEwEncryption)
    print("RMSE w/ quantization:", RMSEwQuantization)
    print("RMSE w/o   filtering:", RMSEwoFilter)
    print("precision gain w/ reg. filtering:", RMSEwoFilter/RMSEwoEncrypt, "times")
    if PARAM.DO_NOT_ENCRYPT:
        print("precision gain w/ quant. filtering:", RMSEwoFilter/RMSEwQuantization, "times")
        print("precision loss due to quantization:", RMSEwQuantization - RMSEwoEncrypt)
    else:
        print("precision gain w/ enc. filtering:", RMSEwoFilter/RMSEwEncryption, "times")
        print("precision loss due to encryption:", RMSEwEncryption - RMSEwoEncrypt)