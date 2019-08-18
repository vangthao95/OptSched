#!/usr/bin/python3

# Wrapper for the runspec tool. Use with the OptSched scheduler
# and LLVM to collect compile-time or execution-time data
# for SPEC CPU2006 benchmarks.

#  Functionality of this wrapper:
#  - Create a config file where you are able to:
#     - Edit the sched.ini file without navigating to the
#        OptSched directory every time.
#     - Decide which benchmarks to run
#  - Create a copy of the sched.ini file used
#  - Run execution-time tests
#     - Automatically run all specified benchmarks and put
#        their scores in a spreadsheet with the random variance
#  - Run compile-time tests
#     - Automatically run all specified benchmarks and put
#        the data in their own directory if multiple benchmarks
#        were specified
#  - Run multiple tests, one after another
#     - To do so you must edit your .ini file and add in a new TEST2 section,
#       to run a third test, add in a TEST3 section and so on.
#     - Example: Running a compile time test after TEST1 has ran
#       [TEST2]
#       mode = c
#       use_opt_sched = YES
#       print_spill_counts = YES
#       latency_precision = UNIT
#       benchmark_selection = FP
#     - Any settings not specified will use the previous run's values.
#
#  Requirements:
#    - python3
#    - pip3
#    - configparser (installed with pip3)
#    - xlwt (installed with pip3)

import configparser # Used to parse .ini config file
import xlwt # Python-excel used to generate output file
import getpass # Get username of current user with getpass.getuser()
import os # For system paths and verifying dir/files exist
import collections # For ordered dictionary
import datetime # Append datetime to output files
import shutil # Copying files
import subprocess # Running shell commands
import re # Searching for score filename
from pathlib import Path # Getting the file name from an absolute path

# Get the current user's name
USERNAME = getpass.getuser()

### GLOBAL VARIABLES ###
SCRIPT_VERSION = 1.3
# Each user gets their own .ini file
INI_FILENAME = USERNAME + "-wrapper-settings.ini"
# Get a config file parser
config = configparser.ConfigParser()
# Regular expression to get CPU2006's output file for the benchmark scores
SCORE_FILE_NAME = re.compile(r'format: ASCII -> (.*)\n')
#LOG_FILE_NAME = re.compile(r'The log for this run is in (.*)\n') TODO
# Validate command to build and run the benchmarks
VALIDATE_COMMAND = "runspec --loose -size=ref -iterations=%s -config=%s --tune=base -r 1 -I -a validate %s"
# Scrub command to scrub the benchmarks first before running
SCRUB_COMMAND = "runspec --loose -size=ref -iterations=1 -config=%s --tune=base -r 1 -I -a scrub %s"

# Mode to run. Defaults to execution-time test
# Will be used for each run. Unless a test changes it,
# the mode will be the same for the next test also.
# c for compile-time test
# e for execution-time test
RunMode = "e"

# Copy sched.ini file to output directory.
# Will be "y" unless a test changes it. Next tests will keep
# the changed value unless another test changes it.
CopySchedIni = "y"

# Settings and their default values.
SCRIPT_SETTINGS = collections.OrderedDict((
  ("script_version", SCRIPT_VERSION),
  ("copy_scores_txt", "y"),
  ("output_spreadsheet", "y")
))

GLOBAL_SETTINGS = collections.OrderedDict((
  ("sched_ini_path", "/home/vang/research/OptSched/example/optsched-cfg/sched.ini"),
  ("cpu2006_path", "/home/vang/research/CPU2006/"),
  ("flang_install_dircetory", "/home/vang/research/flang/flang-install/"),
  ("scores_output_directory", os.getcwd() + "/score_results/"),
  ("runspec-wrapper-optsched_path", os.getcwd() + "/runspec-wrapper-optsched.py")
))
	
SCHED_INI_SETTINGS = collections.OrderedDict((
  ("USE_OPT_SCHED", "YES"),
  ("PRINT_SPILL_COUNTS", "YES"),
  ("REGION_TIMEOUT", "10"),
  ("LENGTH_TIMEOUT", "10"),
  ("HEURISTIC", "LLVM_LUC_NID"),
  ("SECOND_PASS_ENUM_HEURISTIC", "CP"),
  ("ENUM_HEURISTIC", "LUC_NID"),
  ("SPILL_COST_FUNCTION", "SLIL"),
  ("SPILL_COST_WEIGHT", "10"),
  ("LATENCY_PRECISION", "LLVM"),
  ("USE_TWO_PASS", "NO"),
  ("FIRST_PASS_REGION_TIMEOUT", "5"),
  ("FIRST_PASS_LENGTH_TIMEOUT", "5"),
  ("SECOND_PASS_REGION_TIMEOUT", "5"),
  ("SECOND_PASS_LENGTH_TIMEOUT", "5")
))

CPU2006_RUNSPEC_SETTINGS = collections.OrderedDict((
  ("config_file", "Intel_llvm_6.cfg"),
  ("benchmark_selection", "bwaves"),
  ("iteration_num", "1"),
))

# Initialize first test settings
TEST1_SETTINGS = collections.OrderedDict()
# Test to run (compile or execution)
TEST1_SETTINGS["mode"] = "e"
# Copy sched.ini file to output directory?
TEST1_SETTINGS["copy_sched_ini"] = "y"
# Name for output directory
# Default is TEST1, TEST2, etc...
TEST1_SETTINGS["test_name"] = "TEST1"
# Add in options for sched.ini settings and runspec settings
for option in SCHED_INI_SETTINGS:
  TEST1_SETTINGS[option] = SCHED_INI_SETTINGS[option]
for option in CPU2006_RUNSPEC_SETTINGS:
  TEST1_SETTINGS[option] = CPU2006_RUNSPEC_SETTINGS[option]

# List of all the benchmark names.
# Will be used to check if a line
# read from the input file is going 
# to be processed, else it is skipped.
# Will also be used in stats dictionary.
benchName = [
	"400.perlbench",
	"401.bzip2",
	"403.gcc",
	"429.mcf",
	"445.gobmk",
	"456.hmmer",
	"458.sjeng",
	"462.libquantum",
	"464.h264ref",
	"471.omnetpp",
	"473.astar",
	"483.xalancbmk",
	"410.bwaves",
	"416.gamess",
	"433.milc",
	"434.zeusmp",
	"435.gromacs",
	"436.cactusADM",
	"437.leslie3d",
	"444.namd",
	"447.dealII",
	"450.soplex",
	"453.povray",
	"454.calculix",
	"459.GemsFDTD",
	"465.tonto",
	"470.lbm",
	"481.wrf",
	"482.sphinx3"
]

# Empty dictionary containing stats
# Will have an entry for each benchmark
benchStats = collections.OrderedDict()

# Check if the ini file already exist.
# If it does not exist then create an
# ini file with the default settings.
def check_ini_exist():
  if not os.path.exists(INI_FILENAME):
    print("Wrapper.ini file not found. Created new ini file with default values.")
    write_file(get_default_config(), INI_FILENAME)
    return False
  else:
    return True


# Return a config parser with default settings
# as defined in this script.
def get_default_config():
    # Get a config file parser
    configDefault = configparser.ConfigParser()

    # Default settings for script settings
    configDefault["SCRIPT_SETTINGS"] = SCRIPT_SETTINGS

    # Default settings for global paths
    configDefault["GLOBAL"] = GLOBAL_SETTINGS

    # Default settings for first test
    configDefault["TEST1"] = TEST1_SETTINGS

    return configDefault


# Check script version and return
# the version number or -1 if the
# section is not detected.
def get_version():
  if (config.has_option("SCRIPT_SETTINGS", "script_version")):
    return config.get("SCRIPT_SETTINGS", "script_version")
  else:
    return -1


# Write the config settings to file
def write_file(config_, ini_file):
  config_.write(open(ini_file, "w"))


# Update internal variable settings
def update_settings(test_settings):
  print("----------Updating settings----------")
  for x in test_settings:
    # SCHED_INI keys are in upper case
    y = x.upper()
    # Check if the current setting is for SCHED_INI or CPU2006_RUNSPEC
    # and change them accordingly.
    if (y in SCHED_INI_SETTINGS):
      SCHED_INI_SETTINGS[y] = test_settings[x]
      print("Setting " + y + " to " + SCHED_INI_SETTINGS[y])
    elif (x in CPU2006_RUNSPEC_SETTINGS):
      CPU2006_RUNSPEC_SETTINGS[x] = test_settings[x]
      print("Setting " + x + " to " + CPU2006_RUNSPEC_SETTINGS[x])
    elif (x == "mode"):
      global RunMode
      RunMode = test_settings[x]
      print("Setting " + x + " to " + RunMode)
    elif (x == "copy_sched_ini"):
      global CopySchedIni
      CopySchedIni = test_settings[x]
      print("Setting " + x + " to " + CopySchedIni)
  print("-----Finished updating settings------")


# Update wrapper.ini if old version was detected
# Not recommended for use at the moment.
# # FIXME: Properly update ini files with new changes
def update_wrapper_ini():
  # New config
  newConfig = configparser.ConfigParser()
  # Default config to compare to
  defaultConfig = get_default_config()

  # Iterate over section and options
  for section in defaultConfig:
    for option in defaultConfig[section]:
      # Add all sections to new config
      if (not newConfig.has_section(section)):
        newConfig.add_section(section)
      # If the old config has this option then 
      # take the value of the old config
      if (config.has_option(section, option)):
        value = config.get(section, option)
      # Else if the old config doesn't have this
      # option then take the value of the default
      else:
        value = defaultConfig.get(section, option)

      # Set the value in the new config
      newConfig.set(section, option, value)

  # Update script version number
  newConfig.set("SCRIPT_SETTINGS", "script_version", str(SCRIPT_VERSION))
  # Write to file
  write_file(newConfig, "wrapper.ini")   


# Update sched.ini file
def update_sched_ini():
  sched_ini_path = config.get("GLOBAL", "sched_ini_path")

  # Open old sched.ini file in read mode
  # while creating a new file in write mode.
  # Read in all lines of old sched.ini and 
  # write in any changes to new file if necessary.
  with open(sched_ini_path, "r+", encoding="utf-8") as input_file, open("new_sched.ini", "w", encoding="utf-8") as output_file:
    # Read line by line
    for line in input_file:
      # Split line into a list
      originalLine = line.split(" ")
      # Check if this line is the one we"re looking for
      if originalLine[0] in SCHED_INI_SETTINGS:
        newLine = []
        newLine.append(originalLine[0])
        newLine.append(SCHED_INI_SETTINGS[originalLine[0]])

        output_file.write(" ".join(newLine))
        output_file.write("\n")
        
      else:
        output_file.write(line)

  # Replace old sched.ini with new sched.ini
  shutil.move("new_sched.ini", sched_ini_path)


# Create a copy of sched.ini and append to the name
# the current date and time.
def copySchedIni(outputFileDir, time):
  SchedIniSrcPath = config.get("GLOBAL", "sched_ini_path")
 
  # Create directory if it doesn't exist
  if (not os.path.exists(outputFileDir)):
    os.makedirs(outputFileDir)

  FileName = time + "-sched.ini"
  SchedIniDestPath = os.path.join(outputFileDir, FileName)
  shutil.copy(SchedIniSrcPath, SchedIniDestPath)


# Copy the configuration file for SPEC CPU2006 into the output directory
def copyCPU2006Cfg(outputFileDir):
  CPU2006Path = config["GLOBAL"]["cpu2006_path"]
  CfgFileName = CPU2006_RUNSPEC_SETTINGS["config_file"]
  CPU2006ConfigDirectory = os.path.join(CPU2006Path, "config")
  DirectPathToSrcCfg = os.path.join(CPU2006ConfigDirectory, CfgFileName)
  DirectPathToDestCfg = os.path.join(outputFileDir, CfgFileName)
  shutil.copy(DirectPathToSrcCfg, DirectPathToDestCfg)

# Run the benchmark that was passed in as an argument
def run_benchmarks(benchmark):
  # Get runspec variables from config file
  config_file = CPU2006_RUNSPEC_SETTINGS["config_file"]
  iterations = CPU2006_RUNSPEC_SETTINGS["iteration_num"]
  flang_directory = config.get("GLOBAL", "flang_install_dircetory")

  # Generate the command and concatenate it into one variable
  # runspec requires to source shrc first before running
  source_cmd = "source shrc"
  # Get the path to the flang lib directory
  flang_lib = os.path.join(flang_directory, "lib")
  # Exporting LD_LIBRARY_PATH needed for execution-time runs for fortran benchmarks
  export_LD_LIB_cmd = "export LD_LIBRARY_PATH=" + flang_lib
  # Scrub benchmark before running
  scrub_cmd = SCRUB_COMMAND % (config_file, benchmark)
  # Build and run benchmark using the iteration, config, and benchmark inputs
  validate_cmd = VALIDATE_COMMAND % (iterations, config_file, benchmark)
  # Actual command that will be ran
  command = source_cmd + " && " + export_LD_LIB_cmd + " && " + scrub_cmd + " && " + validate_cmd

  # Create a subprocess with
  p = subprocess.Popen("/bin/bash", stdin=subprocess.PIPE, stdout=subprocess.PIPE)
  
  # Tell subprocess to use the command and save the output in stdout
  stdout,stderr = p.communicate(input=command.encode())

  # Decode the output
  output = stdout.decode("unicode_escape")

  # Return output for further processing
  return(output)


# Get the name of the .txt result file using regular expressions
# Return value will be the absolute path to the file
def get_score_filename(output):
  for filename in SCORE_FILE_NAME.findall(output):
    return filename


# Clear the global variable used to store stats for each
# execution-time run
def clearStats():
  # Clear the variable
  global benchStats
  benchStats = collections.OrderedDict()

  # Initialize the benchStats dictionary
  for bench in benchName:
  # Create an entry in the benchStats dictionary,
  # The key will be the benchmark name and
  # the value will be an empty dictionary
  # that will contain stats information about
  # each benchmark
    benchStats[bench] = {}

  # Inside the empty dictionary for each benchmark,
  # insert in entries for stats.
  # Stats will be added as the file is read
    benchStats[bench]["scores"] = [] # Runtime scores, empty list because there may be multiple scores
    benchStats[bench]["median"] = -1 # Median score of runtimes
    benchStats[bench]["randomVariance"] = -1 # Random Variance of benchmark


# Create the xls excel spreadsheet to write the 
# stats to.
def createFile(outputFile):
	# Create a new excel file
	file = xlwt.Workbook()
	# Create a new sheet in the excel file
	sh = file.add_sheet("Sheet 1")
	
	# Write the titles to the respective row
	# Use the function write(row, column, value)
	# to write to sheet 1
	# Note: 0,0 is row 1,1 in the spreadsheet
	sh.write(0,0, "Benchmarks")
	sh.write(1,1, "SCORE")
	sh.write(1,2, "Random Variance")
	
	# Row to start writing the processed stats to
	row = 2
	
	# Write the stats to sheet 1
	for bench in benchStats:
		# Get the variance to check if we gathered stats from
		# this benchmark. Default was -1 so if it is unchanged
		# Then we did not add any stats to this benchmark.
		getVariance = benchStats[bench]["randomVariance"]
		if (getVariance == -1):
			# Skip to next benchmark
			continue
		
		# Write the name to the 0th column (Note: the 0th column
		# here is the 1st column in the sheet)
		sh.write(row, 0, bench)
		
		# Write the median of the scores to the 1st column
		sh.write(row, 1, benchStats[bench]["median"])
		
		# Write the variance of the scores to the 2nd column
		sh.write(row, 2, getVariance)
		
		# Go to the next row for the next benchmark
		row += 1
	
	# Save the excel file
	file.save(outputFile)
	print("File saved as: " + outputFile)


# Test function to print the processed stats.
# This function will output the stats to the console
# or terminal.
def printScores():
	for bench in benchStats:
		print(bench, "median: ", benchStats[bench]["median"], "random variance: ", benchStats[bench]["randomVariance"])
		print("		scores:", end =" ")
		for scores in benchStats[bench]["scores"]:
			print(scores, end =" ")
		print("")


# Calculate the random variance of each benchmark
def calculateVariance():
	for bench in benchStats:
		# Set the initial values to be something
		# that isn't possible.
		max = -9999.0
		min = 9999.0

		# Find the max and min scores
		for scores in benchStats[bench]["scores"]:
			if (scores):
				if scores > max:
					max = scores
				if scores < min:
					min = scores
					
		# If the max and min score wasn"t changed
		# from the initial values then there were
		# no scores processed for this benchmark 
		if (max == -9999 or min == 9999):
			# Skip to next benchmark
			continue
			
		# Calculate the random variance 
		# and round it to the 4th decimal place
		variance = (max - min) / min
		variance = round(variance, 4)
		benchStats[bench]["randomVariance"] = variance


#TODO: Error processing for input reading.
# Script will break if a number is not 
# where it is expected to be.
def readInput(file):
	# Keep track of the section that we are currently reading.
	# If this is set to true then that means we are passed
	# the execution runtime scores and are currently in the
	# seciton for the median of the scores.
	median = False
	
	# Open the file and iterate over each line
	for line in file:
		# Split the lines and put each word or value into a list
		values = line.split()
		
		if "NR" in values:
			continue

		# Empty lines gives an empty list so check if it is a non-empty list
		if (values):
			# If passed both the runtime scores and median scores then break out of file
			# reading loop. (The hardware section is after the runtime scores and median scores
			# section. So use the string HARDWARE to check if we are passed.)
			if values[0] == "HARDWARE":
				break
			# Pass the runtime scores. The median section is next, 
			# so set the median value to True
			if (values[0] == "=============================================================================="):
				median = True
			# Check if the current line is about a valid benchmark
			# The benchmark name will most often be in the 0th 
			# index. The runtime scores will usually be in the 
			# 3rd index. If the format changes then this 
			# line of code will also have to be changed accordingly.
			elif (values[0] in benchName):
				benchmarkName = values[0]


				# If not yet in the median section then we are 
				# still in the runtime scores section
				if median == False:	
					# Append the results to the scores list
					# created earlier.
					benchStats[benchmarkName]["scores"].append(float(values[3]))
				# Else we are in the median scores section
				else:
					benchStats[benchmarkName]["median"] = float(values[3])
			# Else the line does not matter and we skip to the next line
			else:
				continue


# Handle calling the functions to process the 
# execution-time scores file.
def processScores(inputFilePath):
	file = None

	# Check if file exist	
	if os.path.exists(inputFilePath):
		try:
			file = open(inputFilePath, "r")
		except:
			print("Error with reading file: ", inputFilePath)
	else:
		print(inputFilePath, "file does not exist")
	
	# Read and process the input file
	readInput(file)
	
	# Close the input file since we are done
	# processing the necessary information.
	file.close()
	
	# Calculate the variance
	calculateVariance()

# TODO: Use only important settings instead of all settings
# ATM, name is way too long to be useful.
# Return a string that contains the most important settings
# used in the sched.ini file
def getNameWithSettingsUsed():
  # Generate prefix for the output using the benchmark
  # selected and sched.ini settings
  counter = 0
  settingsUsed = CPU2006_RUNSPEC_SETTINGS["benchmark_selection"] + "_"
  for setting in SCHED_INI_SETTINGS:
    settingsUsed += SCHED_INI_SETTINGS[setting]
    counter += 1
    if (counter < len(SCHED_INI_SETTINGS)):
      settingsUsed += "-"

  # Num of iterations
  iterNum = CPU2006_RUNSPEC_SETTINGS["iteration_num"]
  # Generate string with settings used
  outPath = settingsUsed + "_" + iterNum + "iter"
  return outPath
	

# This function handle creating the filename for the spreadsheet
# and passing it to the actual function that will create
# the spreadsheet.
def writeScores(outputFileDir, time):
  # Get a name for the file
  outPath = os.path.join(outputFileDir, "execution-scores.xls") 

  # Get the absolute path
  outputFile = os.path.abspath(outPath)

  # Create the .xls (spreadsheet) file
  createFile(outputFile)


# Run the compile-time script for each benchmark listed
def runCompileTimeTest(outputFileDir, time, benchmarksListToRun):
  # Get the path to the compile time script
  compile_time_wrapper = config.get("GLOBAL", "runspec-wrapper-optsched_path")
  # Check if it exists
  if os.path.exists(compile_time_wrapper):
    # Get the config file
    config_file = CPU2006_RUNSPEC_SETTINGS["config_file"]
  
    for bench in benchmarksListToRun:
      # Each individual run will have their own dir in the base dir
      outputPath = os.path.join(outputFileDir, bench)
      # Run the compile time script and pass in the necessary variables
      # Note: Will block until it is done
      subprocess.call(["./runspec-wrapper-optsched.py", "-o", outputPath, "-c", config_file, "-b", bench])
      
  else:
    # Can't find script
    print("Fatal error: runspec-wrapper-optsched.py not detected")
  return

# Return a file path with the parameter fileDir joined with
# name and a counter
def addCounterToName(fileDir, name):
  while (True):
    count = 2;
    directory = os.path.join(fileDir, name + str(count))
    if (not os.path.exists(directory)):
      return directory
    count = count + 1


# This function will handle most of the work for each
# individual tests specified.
def runIndividualTests(settings, time, testNameStr):
  # Initialize and clear statistics
  clearStats()

  # Record test start time
  now = datetime.datetime.now()
  start_time = now.strftime("%Y-%m-%d %H-%M-%S")

  # Update and store settings internally in memory
  update_settings(settings)

  # Update the sched.ini file
  update_sched_ini()
  
  # Parse the benchmarks to run
  benchmarksListToRun = CPU2006_RUNSPEC_SETTINGS["benchmark_selection"]
  benchmarksListToRun = benchmarksListToRun.split(",")

  # Get the output directory
  outputFileDir = config.get("GLOBAL", "scores_output_directory") 

  # Get the run mode.
  # It will be the same as the last test that 
  # changed it if not specified. Default to
  # execution-time on first test.
  global RunMode

  print("Benchmark test started at: " + start_time)

  # Execution-time test
  if (RunMode == "e"):
    # Generate directory path
    outputFileDir = os.path.join(outputFileDir, time)
    outputFileDir = os.path.join(outputFileDir, "execution-time")
    tempOutputFileDir = os.path.join(outputFileDir, testNameStr)
    
    # If directory with the same name already exist then
    # add a counter to the name.
    if (os.path.exists(tempOutputFileDir)):
      outputFileDir = addCounterToName(outputFileDir, testNameStr)
    else: 
      outputFileDir = tempOutputFileDir
    
    os.makedirs(outputFileDir)
    
    # Run all of the specified benchmarks and process their results
    for bench in benchmarksListToRun:
      print("Running benchmark: " + bench)

      # Run the benchmark
      output = run_benchmarks(bench)

      # Get the filename of the execution-time score file
      # from the command line output that was returned
      # from the execution.
      inputFilePath = get_score_filename(output)
    
      if (inputFilePath):
        filename = Path(inputFilePath).name
        print("Processing file: " + filename)
        # Process the scores
        processScores(inputFilePath)
        # Copy .txt file into output dir
        if (config.get("SCRIPT_SETTINGS", "copy_scores_txt") == "y"):
          copyDestPath = os.path.join(outputFileDir, bench + filename)
          shutil.copy(inputFilePath, copyDestPath)
      else:
        print(output)
        print("Fatal error: Unable to process the scores for " + bench)
        return

    # Optional to test what the program was able
    # to process. Uncomment to print the stats
    # to the console. (Execution-time only)
    #printScores()

    # Write the scores to a spreadsheet
    if (config.get("SCRIPT_SETTINGS", "output_spreadsheet") == "y"):
      writeScores(outputFileDir, time)

  # Compile-time test
  elif (RunMode == "c"):
    # Generate directory path
    outputFileDir = os.path.join(outputFileDir, time)
    outputFileDir = os.path.join(outputFileDir, "compile-time")
    outputFileDir = os.path.join(outputFileDir, testNameStr)
    
    # If directory with the same name already exist then
    # add a counter to the name.
    if (os.path.exists(tempOutputFileDir)):
      outputFileDir = addCounterToName(outputFileDir, testNameStr)
    else: 
      outputFileDir = tempOutputFileDir
    
    os.makedirs(outputFileDir)
    
    # Run compile time script
    runCompileTimeTest(outputFileDir, time, benchmarksListToRun)
    # Store a copy of the sched.ini file

  else: 
    print("Fatal error: Invalid run mode.")
    return

  # Store a copy of the sched.ini file
  if (CopySchedIni == "y"):
    copySchedIni(outputFileDir, time)
  
  # Store a copy of the cfg file for CPU2006
  copyCPU2006Cfg(outputFileDir)
  
  # Benchmark end time
  now_2 = datetime.datetime.now()
  end_time = now_2.strftime("%Y-%m-%d %H-%M-%S")
  print("Benchmark test ended at: " + end_time)


def main():
  # Prevent running this script as root user to prevent
  # sharing same copy of config file.
  if (USERNAME == "root"):
    print("This script cannot be run as root user.")
    return

  # First check for ini file
  if (check_ini_exist() == False):
    print("Please input your desired settings into wrapper.ini then run this script again.")
    return 

  # Read from ini file
  config.read(INI_FILENAME)

  # Check version
  version = get_version()
  if (float(version) < float(SCRIPT_VERSION)):
    print("Old wrapper.ini version detected, please delect your wrapper.ini file.")
    print("A new and updated one will be created with the default values.")
    # FIXME: Properly update ini files with new changes
    #update_wrapper_ini()
    return

  # Get the time
  now = datetime.datetime.now()
  time = now.strftime("%Y-%m-%d_%H-%M-%S")
  print(time)
  return

  # Process TEST1
  if (config.has_section("TEST1")):
    print("**********STARTING TEST1************")
    current_test_settings = config["TEST1"]
    testNameStr = "TEST1"
    if (config.has_option("TEST1", "test_name")):
      testNameStr = current_test_settings["test_name"]
    runIndividualTests(current_test_settings, time, testNameStr)
    print("**********TEST1 FINISHED************\n")
  else:
    print("Fatal error: Settings for TEST1 not found")
    return

  # Check if there are any more tests
  for i in range(2,11):
    current_test = "TEST" + str(i)
    if (config.has_section(current_test)):
      print("**********STARTING " + current_test + "************")
      current_test_settings = config[current_test]
      testNameStr = current_test
      if (config.has_option(current_test, "test_name")):
        testNameStr = current_test_settings["test_name"]
      runIndividualTests(current_test_settings, time, testNameStr)
      print("**********" + current_test + " FINISHED************\n")
  

if __name__ == "__main__":
  main()
