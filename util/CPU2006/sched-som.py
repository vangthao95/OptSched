#!/usr/bin/env python3
"""
Find the SOM (Sum of minimums) from the spilling stats generated
from multiple input scheduling algorithms.
The test results should be generated with the 'runspec-wrapper' script.
The test directory name is taken as the name of the test run, and a spills.dat
file must exist in each of those directories.
Options:
-o: The output directory for the results generated by this script.
-i: The input directory where the test run directoires are located.
"""

from __future__ import division
import os
import sys
import statistics
import collections
import optparse

# Constants
SPILLS_FILENAME = 'spills.dat'
SPILLS_MIN_FILE_SUFFIX = '_spills_min.dat'
SPILLS_STATS_FILE_SUFFIX = '_som_summary.dat'

# Track metrics for each benchmark.
class BenchStats:
    totalFuncs = 0
    totalSpills = 0
    # Number of functions where every test did NOT find a schedule will zero spills.
    funcsWithSpills = 0

    def __init__(self, benchName, testNames):
        self.testNames = testNames
        # The output string for the min_spills file.
        self.benchDataStr = benchName + ':\n'
        # Dict with test names as keys which tracks the number of functions at the
        # minimum.
        self.funcsAtMin = {}
        # The number of spills in this benchmark for each test.
        self.testSpills = {}
        # The maximum number of spills above the minimum for this test (spillsAboveMin, spillsInMin)
        self.maxExtraFunc = {}
        # The number of functions where this test is the algoirthm that found the best schedule.
        self.funcsWithBestRes = {}
        for testName in testNames:
            self.funcsWithBestRes[testName] = 0
            self.funcsAtMin[testName] = 0
            self.testSpills[testName] = 0
            self.maxExtraFunc[testName] = (0, 0)

# Stats for each test that include all benchmarks.
class TestTotals:
    totalSom = 0
    totalFuncs = 0
    totalFuncsWithSpills = 0

    def __init__(self, testNames):
        self.totalFuncsAtMin = {}
        self.totalTestSpills = {}
        self.totalMaxExtraFunc = {}
        self.totalFuncsWithBestRes = {}
        for testName in testNames:
            self.totalFuncsWithBestRes[testName] = 0
            self.totalFuncsAtMin[testName] = 0
            self.totalTestSpills[testName] = 0
            self.totalMaxExtraFunc[testName] = (0, 0)

# Process all benchmarks for one test run.
def processSpillsFile(spillsFile):
    spillsResult = collections.OrderedDict()
    data = spillsFile.readlines()
    dataItr = iter(data)

    done = False
    while not done:
        line = next(dataItr).strip()

        # End of file
        if line == '------------':
            done = True

        else:
            benchName = line.split(':')[0]
            spillsResult[benchName] = processBenchmark(dataItr)

    return spillsResult

# Process spill stats for one benchmark.
def processBenchmark(dataItr):
    benchResult = {}
    done = False
    while not done:
        line = next(dataItr).strip()

        # End of benchmark
        if line == "---------":
            # seek 2 forward from the current position
            for i in range(2):
                next(dataItr)
            done = True

        else:
            spills, funcName = line.split(' ')
            benchResult[funcName] = spills;

    return benchResult

# Collect SOM stats and generate output files.
def generateSOMFiles(somData, outDir, inDir):
    try:
        inputDirectoryBase = os.path.basename(os.path.abspath(inDir))
        spillsStatsFileName = inputDirectoryBase + SPILLS_STATS_FILE_SUFFIX
        spillsMinFileName = inputDirectoryBase + SPILLS_MIN_FILE_SUFFIX
        with open(os.path.join(outDir, spillsMinFileName), 'w') as minSpillsFile, \
        open(os.path.join(outDir, spillsStatsFileName), 'w') as spillsStatsFile:
            # Iterate through benchmarks using a random entry in somData,
            # all tests must have the same benchmarks.
            testName = next(iter(somData))
            totals = TestTotals(iter(somData))
            # Collect stats for each benchmark, add totals for all tests
            for bench in somData[testName]:
                benchData = generateBenchStats(bench, somData)
                # Wrtie minimums for each function to min spills file.
                minSpillsFile.write(benchData.benchDataStr)

                # Update global totals for all benchmarks
                totals.totalSom += benchData.totalSpills
                totals.totalFuncs += benchData.totalFuncs
                totals.totalFuncsWithSpills += benchData.funcsWithSpills

                # Calculate aggregate stats for each benchmarks.
                for testName in iter(somData):
                    totals.totalFuncsAtMin[testName] += benchData.funcsAtMin[testName]
                    totals.totalTestSpills[testName] += benchData.testSpills[testName]
                    totals.totalFuncsWithBestRes[testName] += benchData.funcsWithBestRes[testName]
                    if benchData.maxExtraFunc[testName][0] > totals.totalMaxExtraFunc[testName][0]:
                        totals.totalMaxExtraFunc[testName] = (benchData.maxExtraFunc[testName][0], benchData.maxExtraFunc[testName][1])


            # Wrtie SOM total spills to per-function min spills file
            somString = '-'*12 + '\n' + 'Total:'  + str(totals.totalSom)
            minSpillsFile.write(somString)

            # Write details for each test to stats file
            testStr = 'Spilling Statistics:\n\n'
            testStr += "\n{:<25}{:>40}{:>25}{:>25}{:>28}\n".format('Heuristic', 'Extra Spills', '%Funcs at min', 'Innovativeness', 'Max extra per func')
            testStr += '--------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n'


            for testName in sorted(totals.totalTestSpills, key=totals.totalTestSpills.__getitem__):
                extraSpills = totals.totalTestSpills[testName] - totals.totalSom
                extraSpillsP = "{:.2%}".format(extraSpills / totals.totalSom)
                funcAtMinP = "{:.2%}".format(totals.totalFuncsAtMin[testName] / totals.totalFuncsWithSpills)
                funcsWithBestResP = "{:.2%}".format(totals.totalFuncsWithBestRes[testName] / totals.totalFuncsWithSpills)

                maxExtraSpills = totals.totalMaxExtraFunc[testName][0]
                minSpillsInFuncWithMaxExtra = totals.totalMaxExtraFunc[testName][1]
                try:
                    maxExtraSpillsP = maxExtraSpills / minSpillsInFuncWithMaxExtra
                except ZeroDivisionError:
                    maxExtraSpillsP = -1

                maxExtraPerFuncStr = 'inf' if maxExtraSpillsP == -1 else "{:.2%}".format(maxExtraSpillsP)

                #stdev = findStdev(somData[testName])
                testStr += "{:<40}{:>17}{:>9}{:>20}{:>18}{:>9}{:>30}\n\n".format(testName, \
                                                         "{:,}".format(extraSpills), \
                                                         "({})".format(extraSpillsP), \
                                                         funcAtMinP, \
                                                         "{:,}".format(totals.totalFuncsWithBestRes[testName]), \
                                                         "({})".format(funcsWithBestResP), \
                                                         "{:>7} {:>7} {:>7}".format(maxExtraSpills, "({})".format(minSpillsInFuncWithMaxExtra), \
                                                         maxExtraPerFuncStr))

            testStr += '--------------------------------------------------------------------------------------------------------------------------------------------------------------------\n\n'

            spillsStatsFile.write(testStr)

            # Write SOM and other metrics to stats file
            statsStr = '-------------------------------------------------------\n'
            statsStr += "{:<30}{:>25}\n".format('Total Functions:', "{:,}".format(totals.totalFuncs))
            statsStr += "{:<30}{:>25}\n".format('Functions with spills:', "{:,}".format(totals.totalFuncsWithSpills))
            statsStr += "{:<30}{:>25}\n".format('Sum of minima (SOM):', "{:,}".format(totals.totalSom))
            statsStr += '-------------------------------------------------------\n'
            spillsStatsFile.write(statsStr)


    except IOError as error:
        print ('Fatal: Could not create function min spills file.')
        raise

def findStdev(data):
    spillsList = []
    for bench in data:
        for func in data[bench]:
            # Get spills for this function
            spillsList.append(int(data[bench][func]))
    return statistics.stdev(spillsList)

# Find min spills for this benchmarks across all tests.
def generateBenchStats(benchName, somData):
    # Verify that this benchmark exists in all tests, and that the benchmark
    # has the same number of functions in each test.
    testName = next(iter(somData))
    numberOfFunctions = len(somData[testName][benchName])
    for test in somData:
        if somData[test][benchName] is None:
            print ('Error: Benchmark ' + benchName + ' does not exist in test ' + testName)
        if len(somData[test][benchName]) != numberOfFunctions:
            print ('Error: Benchmark ' + benchName + ' does not have the same number of functions in ' + test + ' as in ' + testName)

    benchData = BenchStats(benchName, iter(somData))
    benchData.totalFuncs = numberOfFunctions
    for func in somData[testName][benchName]:
        # Tests which generated the minimum number of spills.
        minTests = []
        # The minimum number of spills for this function.
        minSpills = sys.maxsize
        for test in somData:
            spills = int(somData[test][benchName][func])
            benchData.testSpills[test]+=spills
            # Is this the minimum number of spills for this function
            if spills == minSpills:
                minTests.append(test)
            elif spills < minSpills:
                minTests = []
                minTests.append(test)
                minSpills = spills

        # Check for Max extra spills above min in a function
        for test in somData:
            spills = int(somData[test][benchName][func])
            diff = spills - minSpills
            if (diff > benchData.maxExtraFunc[test][0]):
                benchData.maxExtraFunc[test] = (diff, minSpills)

        # Format output data for this function
        bestTests = '[All]' if len(minTests) == len(somData) else str(minTests)

        if len(minTests) == 1:
            benchData.funcsWithBestRes[minTests[0]] += 1

        # Is this a function with spills.
        if not (bestTests == '[All]' and minSpills == 0):
            benchData.funcsWithSpills+=1

            # Track every test that is at the minimum for this fucntion.
            for test in minTests:
                benchData.funcsAtMin[test]+=1

        benchData.benchDataStr += ' '*10 + str(minSpills) + ' ' + func + ' ' + bestTests + '\n'
        # Add function spills to total.
        benchData.totalSpills += minSpills

    benchData.benchDataStr += '  ---------\n' + 'Sum: ' + str(benchData.totalSpills) + '\n\n'
    return benchData

def main(args):
    somData = {}
    # Find all test run direcotires.
    testRunsDirectory = os.path.abspath(args.indir)
    dirNames = os.listdir(testRunsDirectory)
    # Gather spill data for each test run.
    for dirName in dirNames:
        # Verify this is a directory.
        if not os.path.isdir(os.path.join(testRunsDirectory, dirName)):
            continue

        try:
            with open(os.path.join(testRunsDirectory, dirName, SPILLS_FILENAME)) as spillsFile:
                somData[dirName] = processSpillsFile(spillsFile)

        except IOError as error:
            print ('Error: Could not open spills file.')
            print (error)

    # Find SOM stats and generate SOM spills and stats files.
    generateSOMFiles(somData, args.outdir, args.indir)


if __name__ == '__main__':
    # Parse command-line arguments
    parser = optparse.OptionParser(description='Find the SOM (Sum of minimums) from the spilling stats generated from multiple input scheduling algorithms.')
    parser.add_option('-o', '--outdir',
                      metavar='filepath',
                      default='./',
                      help='Where to write the SOM results (%default).')
    parser.add_option('-i', '--indir',
                      metavar='filepath',
                      default='./',
                      help='Where to find the test run direcotires (%default).')

    main(parser.parse_args()[0])
