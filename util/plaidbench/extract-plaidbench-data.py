'''*******************************************************************************
Description:  Extract data from plaidbench runs.
Author:       Vang Thao
Created:      November 26, 2019
Last Update:  November 27, 2019
*******************************************************************************'''

'''
This script takes in data from plaidbench runs and output 3 spreadsheets.
    Spreadsheet 1: Compile times
    Spreadsheet 2: Examples-per-second
    Spreadsheet 3: Tiles-per-second (FPS)

Requirements:
    - python3
    - pip3
    - xlwt (spreadsheet module, installed using pip3)

This script must be run from the directory that contain one or more
directories containing runs from plaidbench. This directory should not
include anything else.
Ex:
/home/michael/plaidbench-results $ ls
    --- script.py
    --- plaidbench-run-withRPOnly-01/
    --- plaidbench-run-withRPOnly-02/
    --- plaidbench-run-withRPOnly-03/
    --- plaidbench-run-withoutRPOnly-01/
    --- plaidbench-run-withoutRPOnly-02/
    --- plaidbench-run-withoutRPOnly-03/
/home/michael/plaidbench-results $ python3 script.py
    
Expected folder names for the runs:
x-01
x-02
x-03
y-01
y-02
...

In this example, x should be a run with the same setting and is ran 3 times.
y may be a run with different settings and is run 2 times.


Expected folder structure inside a directory for a run:
/home/michael/plaidbench-results/plaidbench-run-withRPOnly-01 $ ls
    --- densenet121/
    --- densenet169/
    --- densenet201/
    --- imdb_lstm/
    and so on.

Inside each benchmark directory should be a log file with the network
name concatenated with the extension ".log".
Ex:
/home/michael/plaidbench-results/plaidbench-run-withRPOnly-01/vgg19 $ ls
    --- vgg19.log

This file should be output redirected from the terminal when running plaidbench.
Ex:
$ plaidbench --examples 4096 --batch-size 16 keras --no-fp16 --no-train > vgg19.log

Output:
Running 4096 examples with vgg19, batch size 16, on backend plaid
Model loaded.
Compiling network... Warming up... Running...
Example finished, elapsed: 9.645s (compile), 20.750s (execution)

keras opencl_amd_gfx906+sram-ecc.0
-----------------------------------------------------------------------------------------
Network Name         Inference Latency         Time / FPS          
-----------------------------------------------------------------------------------------
vgg19                5.07 ms                   4.49 ms / 222.52 fps
Correctness: untested. Could not find golden data to compare against.
'''
#!/usr/bin/python3

import os       # Used for scanning directories, getting paths, and checking files.
import xlwt     # Used to create excel spreadsheets.

# Contains all of the stats
benchStats = {}

# List of benchmark names
benchmarks = [
    "densenet121",
    "densenet169",
    "densenet201",
    "inception_resnet_v2",
    "inception_v3",
    "mobilenet",
    "nasnet_large",
    "nasnet_mobile",
    "resnet50",
    "vgg16",
    "vgg19",
    "xception",
    "imdb_lstm",
]

# Get name of all directories in current folder
subfolders = [f.name for f in os.scandir(".") if f.is_dir() ]

# For each folder
for folderName in subfolders:
    # Get the run number from the end
    # of the folder name
    runNumber = folderName[-2:]

    # Get the name of the run
    # and exclude the run number
    nameOfRun = folderName[:-3]
        
    # Create an entry in the stats for the
    # name of the run
    if (nameOfRun not in benchStats):
        benchStats[nameOfRun] = {}

    # Begin stats collection for this run
    statsForRun = {}
    total_compile_time = 0.00
    for bench in benchmarks:
        currentPath = os.path.join(folderName, bench)
        currentLogFile = os.path.join(currentPath, bench + ".log")
        stats = {}
        # Set default values
        stats["compile_time"] = "Not Found"
        stats["inference_lat"] = "Not Found"
        stats["fps"] = "Not Found"

        # First check if log file exists.
        if (os.path.exists(currentLogFile)):
            # Open log file if it exists.
            with open(currentLogFile) as file:
                for line in file:
                    test = line.split()
                    if (test):
                        if (test[0] == "Example"):
                            # Remove the s character from string and convert the compile time
                            # to a floating point number
                            compile_time = float(test[3][:-1])
                            # Accumulate total compile time for this run
                            total_compile_time += compile_time
                            stats["compile_time"] = compile_time
                        elif (test[0] in benchmarks):
                            inference_lat = float(test[1])
                            fps = float(test[6])
                            stats["inference_lat"] = inference_lat
                            stats["fps"] = fps
        # If the file doesn't exist, output error log.
        else:
            print("Cannot find log file for {} run {} benchmark {}.".format(nameOfRun, runNumber, bench))

        # Save stats for this benchmark
        statsForRun[bench] = stats

    # Save stats for this run
    benchStats[nameOfRun][runNumber] = statsForRun
    benchStats[nameOfRun][runNumber]["total_compile_time"] = total_compile_time

# Print stats gathered by script to terminal.
def printStats():
    for nameOfRun in benchStats:
        print(nameOfRun)
        for runNumber in benchStats[nameOfRun]:
            print("    {}".format(runNumber))
            for bench in benchStats[nameOfRun][runNumber]:
                if (bench == "total_compile_time"):
                    print("        Total compile time: {:0.3f}".format(benchStats[nameOfRun][runNumber][bench]))
                else: 
                    print("        {}".format(bench))
                    print("            Compile Time: {:0.3f}".format(benchStats[nameOfRun][runNumber][bench]["compile_time"]))
                    print("            Inference Latency: {:0.2f}".format(benchStats[nameOfRun][runNumber][bench]["inference_lat"]))
                    print("            FPS: {:0.2f}".format(benchStats[nameOfRun][runNumber][bench]["fps"]))
            
# Create compile time excel spreadsheet
def CreateCompileTimeSpreadsheet():
    # Create a new excel file
    file = xlwt.Workbook()
    # Create a new sheet in the excel file
    sh = file.add_sheet("Sheet 1")

    # Write the titles to the respective row
    # Use the function write(row, col, val)
    # to write to sheet 1
    # Note: 0,0 is row 1,1 in the spreadsheet
    sh.write(0,0, "Benchmarks")
    # Set width for benchmark col
    # 36.5714285 is about equal to 1 pixel
    # Width of 18 is 131 pixels
    sh.col(0).width = 4790

    # Write benchmark names
    row = 2
    for bench in benchmarks:
        sh.write(row, 0, bench)
        row += 1
    sh.write(row, 0, "Total")

    # Begin writing stats for compile times
    col = 1
    for nameOfRun in benchStats:
        # Write run name
        row = 0
        sh.write(row, col, nameOfRun)

        for runNumber in benchStats[nameOfRun]:
            # Write run number
            row = 1
            sh.write(row, col, "Run {}".format(runNumber))
            row += 1

            # Write compile time stats
            for bench in benchStats[nameOfRun][runNumber]:
                if (bench == "total_compile_time"):
                    sh.write(row, col, benchStats[nameOfRun][runNumber][bench])
                else:
                    sh.write(row, col, benchStats[nameOfRun][runNumber][bench]["compile_time"])
                row += 1

            # Go to next column for the next run.
            col += 1

    # Save file to current directory.
    file.save("compile_time.xls")

# Create examples per second excel spreadsheet
def CreateEPSSpreadsheet():
    # Create a new excel file
    file = xlwt.Workbook()
    # Create a new sheet in the excel file
    sh = file.add_sheet("Sheet 1")

    # Write the titles to the respective row
    # Use the function write(row, col, val)
    # to write to sheet 1
    # Note: 0,0 is row 1,1 in the spreadsheet
    sh.write(0,0, "Benchmarks")
    # Set width for benchmark col
    # 36.5714285 is about equal to 1 pixel
    # Width of 18 is 131 pixels
    sh.col(0).width = 4790

    # Write benchmark names
    row = 2
    for bench in benchmarks:
        sh.write(row, 0, bench)
        row += 1

    # Begin writing stats for compile times
    col = 1
    for nameOfRun in benchStats:
        # Write run name
        row = 0
        sh.write(row, col, nameOfRun)

        # Begin writing stats for examples per second
        for runNumber in benchStats[nameOfRun]:
            # Write run number
            row = 1
            sh.write(row, col, "Run {}".format(runNumber))
            row += 1

            for bench in benchStats[nameOfRun][runNumber]:
                if (bench == "total_compile_time"):
                    continue
                else:
                    # Calculate examples per second stat then write to spreadsheet
                    examplesPerSecond = 1000.00 / benchStats[nameOfRun][runNumber][bench]["inference_lat"]
                    sh.write(row, col, examplesPerSecond)
                row += 1

            # Go to next column for the next run.
            col += 1

    # Save file to current directory.
    file.save("examples-per-second.xls")

# Create examples per second excel spreadsheet
def CreateTPSSpreadsheet():
    # Create a new excel file
    file = xlwt.Workbook()
    # Create a new sheet in the excel file
    sh = file.add_sheet("Sheet 1")

    # Write the titles to the respective row
    # Use the function write(row, col, val)
    # to write to sheet 1
    # Note: 0,0 is row 1,1 in the spreadsheet
    sh.write(0,0, "Benchmarks")
    # Set width for benchmark col
    # 36.5714285 is about equal to 1 pixel
    # Width of 18 is 131 pixels
    sh.col(0).width = 4790

    # Write benchmark names
    row = 2
    for bench in benchmarks:
        sh.write(row, 0, bench)
        row += 1

    col = 1
    for nameOfRun in benchStats:
        # Write run name
        row = 0
        sh.write(row, col, nameOfRun)
        
        for runNumber in benchStats[nameOfRun]:
            # Write run number
            row = 1
            sh.write(row, col, "Run {}".format(runNumber))
            row += 1

            for bench in benchStats[nameOfRun][runNumber]:
                if (bench == "total_compile_time"):
                    continue
                else:
                    # Get the tiles per second (FPS) from benchStats and write it to
                    # the spreadsheet.
                    fps = benchStats[nameOfRun][runNumber][bench]["fps"]
                    sh.write(row, col, fps)
                row += 1

            # Go to next column for the next run.
            col += 1

    # Save file to current directory.
    file.save("tiles-per-second.xls")

# Call the respective functions to create the spreadsheets
CreateCompileTimeSpreadsheet()
CreateEPSSpreadsheet()
CreateTPSSpreadsheet()
