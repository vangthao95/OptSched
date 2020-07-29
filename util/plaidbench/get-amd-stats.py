#!/usr/bin/python3
'''
**********************************************************************************
Description:    This script is meant to be used with the OptSched scheduler and
                the run-plaidbench.sh script or with test results from shoc.
                This script will extract stats about how our OptSched scheduler
                is doing from the log files generated from the run-plaidbench.sh
                script.
Author:	        Vang Thao
Last Update:	April 13, 2019
**********************************************************************************

OUTPUT:
    This script takes in data from plaidbench or shoc runs and output a single 
    spreadsheet.
        Spreadsheet 1: optsched-stats.xlsx

Requirements:
    - python3
    - pip3
    - openpyxl (sreadsheet module, installed using pip3)

HOW TO USE:
    1.) Run a plaidbench benchmarks with run-plaidbench.sh to generate a
        directory containing the results for the run.
    2.) Pass the path to the directory as an input to this script with
        the -i option.

Example:
    ./get-optsched-stats.py -i /home/tom/plaidbench-optsched-01/

    where plaidbench-optsched-01/ contains
        densenet121
        densenet169
        ...
        ...
'''
import argparse
import csv
import logging
import os
import sys
# Import common functionalities
from OptSched import *


# List of stats that can be initialized to 0
statsProcessed = [
    'TotalProcessed',
    'SchedRevert',
    'TotalInstr',
    'RegionsWithCluster',
    'ClusterTotalGroups',
    'ClusterTotalInstr',
    'ClusterBlocksCnt',
    'ClusterBlocksSizeCnt',
]


def getNewStatsDict():
    stats = {}
    for stat in statsProcessed:
        stats[stat] = 0
    stats['ClusterGroupAverage'] = -1.0
    stats['LargestCluster'] = -1
    stats['ClusterOverallAverageSize'] = -1

    return stats

def parseStats(filePaths):
    # Get logger
    logger = logging.getLogger('parseStats')

    stats = {}
    # Begin stats collection for this run
    for bench in filePaths:
        # First check if log file exists.
        if os.path.exists(filePaths[bench]):
            # Open log file if it exists.
            with open(filePaths[bench]) as file:
                # Contain the stats for this benchmark
                curStats = getNewStatsDict()

                log = file.read()
                blocks = log.split(regionSpliter)[1:]
                for block in blocks:
                    curStats['TotalProcessed'] += 1

                    if RE_REVERT_SCHED.search(block):
                        curStats['SchedRevert'] += 1
                        continue

                    DAGInfo = RE_DAG_INFO.search(block)
                    dagName = DAGInfo.group(1)

                    totalClusterGroups = 0
                    totalInstrsInClusterInRegion = 0
                    largestClusterGroup = -1
                    for clusterNum, instrInCluster in RE_CLUSTER_GROUPS.findall(block):
                        if totalClusterGroups < int(clusterNum):
                            totalClusterGroups = int(clusterNum)
                        if largestClusterGroup < int(instrInCluster):
                            largestClusterGroup = int(instrInCluster)
                        totalInstrsInClusterInRegion += int(instrInCluster)
                        if curStats['LargestCluster'] < int(instrInCluster):
                            curStats['LargestCluster'] = int(
                                instrInCluster)

                    if totalClusterGroups > 0:
                        curStats['ClusterTotalGroups'] += totalClusterGroups
                        curStats['RegionsWithCluster'] += 1
                        curStats['ClusterTotalInstr'] += totalInstrsInClusterInRegion
                        # Get all clusters in a list format
                        cluster = block.split(CLUSTER_START)[1]
                        clusterBlocksInSched = 0
                        clusterSizeInSched = 0
                        for clusterNum, clusterInstrList in RE_CLUSTER_ENUM.findall(cluster):
                            clusterBlocksInSched += 1
                            clusterSizeInSched += len(clusterInstrList.split())
                        curStats['ClusterBlocksCnt'] += clusterBlocksInSched
                        curStats['ClusterBlocksSizeCnt'] += clusterSizeInSched
                stats[bench] = curStats

        # If the file doesn't exist, output error log.
        else:
            print('Cannot find log file for benchmark {}.'.format(bench))
    
    return stats

def printStats():
    pass


def createSpreadsheets(output, stats):
    if 'csv' not in output[-3:]:
        output += '.csv'
        
    with open(output, 'w', newline='') as file:
        fieldnames = [
            'Benchmark',
            'Regions processed',
            'Regions with clusters',
            'Average size of cluster groups',
            'Total cluster blocks',
            'Overall Avg. Cluster Size',
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        overallTotalProcessed = 0
        overallTotalRegionsWithClusters = 0
        overallTotalGroupsCnt = 0
        overallTotalInstr = 0
        overallBlocksCnt = 0
        overallBlocksSizeCnt = 0
        for bench in stats:
            avgSizeOfClusterGroups = 0
            avgClusterSize = 0
            if stats[bench]['RegionsWithCluster'] != 0:
                avgSizeOfClusterGroups = stats[bench]['ClusterTotalInstr'] / \
                    stats[bench]['ClusterTotalGroups']
                overallTotalGroupsCnt += stats[bench]['ClusterTotalGroups']
                overallTotalInstr += stats[bench]['ClusterTotalInstr']
                avgClusterSize = stats[bench]['ClusterBlocksSizeCnt'] / \
                    stats[bench]['ClusterBlocksCnt']
                overallBlocksCnt += stats[bench]['ClusterBlocksCnt']
                overallBlocksSizeCnt += stats[bench]['ClusterBlocksSizeCnt']
            
            writer.writerow({
                'Benchmark': bench,
                'Regions processed': stats[bench]['TotalProcessed'],
                'Regions with clusters': stats[bench]['RegionsWithCluster'],
                'Average size of cluster groups': avgSizeOfClusterGroups,
                'Total cluster blocks': stats[bench]['ClusterBlocksCnt'],
                'Overall Avg. Cluster Size': avgClusterSize})
            overallTotalProcessed += stats[bench]['TotalProcessed']
            overallTotalRegionsWithClusters += stats[bench]['RegionsWithCluster']

        if overallTotalRegionsWithClusters != 0:
            overallAvgSizeOfClusterGroups = overallTotalInstr / overallTotalGroupsCnt
            overallAvgClusterSize = overallBlocksSizeCnt / overallBlocksCnt

        writer.writerow({
            'Benchmark': 'Total',
            'Regions processed': overallTotalProcessed,
            'Regions with clusters': overallTotalRegionsWithClusters,
            'Average size of cluster groups': overallAvgSizeOfClusterGroups,
            'Total cluster blocks': overallBlocksCnt,
            'Overall Avg. Cluster Size': overallAvgClusterSize})
        

    '''
    if 'xls' not in output[-4:]:
        output += '.xlsx'

    # Create new excel worksheet
    wb = Workbook()

    # Grab the active worksheet
    ws = wb.active

    # Insert column titles
    ws['A1'] = 'Benchmarks'
    ws['A1'].font = Font(bold=True)
    col = 'B'
    row = 1
    ws[col + str(row)] = 'Benchmark Stats'
    row = 2
    ws[col+str(row)] = 'Regions processed'
    ws[chr(ord(col)+1)+str(row)] = 'Regions With Clusters'
    ws[chr(ord(col)+2)+str(row)] = 'Passed to B&B'
    ws[chr(ord(col)+3)+str(row)] = 'Optimal and improved'
    ws[chr(ord(col)+4)+str(row)] = 'Optimal and not improved'
    ws[chr(ord(col)+5)+str(row)] = 'Timeout and improved'
    ws[chr(ord(col)+6)+str(row)] = 'Timeout and not improved'
    ws[chr(ord(col)+7)+str(row)] = 'Average size of cluster groups'
    ws[chr(ord(col)+8)+str(row)] = 'Largest Cluster Group'
    ws[chr(ord(col)+9)+str(row)] = 'Largest Optimal Cluster Group'
    ws[chr(ord(col)+10)+str(row)] = 'Total Cluster Blocks'
    ws[chr(ord(col)+11)+str(row)] = 'Overall Avg. Cluster Size'
    ws[chr(ord(col)+12)+str(row)] = 'Avg. Size to B&B'
    ws[chr(ord(col)+13)+str(row)] = 'Avg. Size of Timeouts'
    ws[chr(ord(col)+14)+str(row)] = 'Avg. Size of Improved Regions'
    ws[chr(ord(col)+15)+str(row)] = 'Largest Optimal Region'
    ws[chr(ord(col)+16)+str(row)] = 'Largest Improved Region'

   pass
'''


def main(args):
    if args.verbose:
        # if True:
        logging.basicConfig(level=logging.DEBUG)

    # Get filepaths for the selected benchmark suite
    filePaths = getBenchmarkFilePaths(args.inputFolder, args.benchmark)

    # Start stats collection
    stats = parseStats(filePaths)

    # if args.verbose:
    if True:
        printStats()

    if not args.disable:
        filename = ''
        if args.output is None:
            filename = os.path.dirname('cluster-stats-' + args.inputFolder)
        else:
            filename = args.output

        createSpreadsheets(filename, stats)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script to extract OptSched stats',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        dest='inputFolder',
        help='The path to a benchmark directory')

    parser.add_argument('--verbose', '-v',
                        action='store_true', default=False,
                        dest='verbose',
                        help='Print the stats to terminal')

    parser.add_argument('--output', '-o',
                        dest='output',
                        help='Output spreadsheet filepath')

    parser.add_argument('--disable', '-d',
                        action='store_true', default=False,
                        dest='disable',
                        help='Disable spreadsheet output.')

    parser.add_argument('--benchmark', '-b', default='plaid', choices=[
                        'plaid', 'shoc'], dest='benchmark', help='Select the benchmarking suite to parse for.')

    args = parser.parse_args()

    main(args)
