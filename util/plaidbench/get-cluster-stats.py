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
import os
import logging
import sys
# Import common functionalities
from OptSched import *

# List of stats that can be initialized to 0
statsProcessed = [
    'TotalProcessed',
    'ClustersRegionCount',
    'ClusterEnumCnt',
    'ClusterOptImpr',
    'ClusterOptNotImpr',
    'ClusterTimeoutImpr',
    'ClusterTimeoutNotImpr',
    'ClusterTimeoutCnt',
    'ClusterTotalGroups',
    'ClusterTotalInstr',
    'ClusterTimeoutTotalGroups',
    'ClusterTimeoutTotalInstr',
    'ClusterTimeoutInstrToEnum',
    'ClusterBlocksCnt',
    'ClusterBlocksSizeCnt',
    'ClusterTotalInstrToEnum',
    'ClusterImprovedTotalInstrToEnum',
    'ClusterImprovedCnt',
]


def getPercentageString(num, dem):
    if dem == 0:
        return '0 (0.00%)'

    formattedPcnt = num / dem * 100
    return '{} ({:.2f}%)'.format(num, formattedPcnt)


def getNewStatsDict():
    stats = {}
    for stat in statsProcessed:
        stats[stat] = 0
    stats['LargestOptimalRegion'] = -1
    stats['LargestImprovedRegion'] = -1
    stats['ClusterGroupAverage'] = -1.0
    stats['LargestCluster'] = -1
    stats['LargestClusterOptimal'] = -1
    stats['ClusterAverageTimeoutSize'] = -1
    stats['ClusterAverageInstrSizeToEnum'] = -1
    stats['ClusterOverallAverageSize'] = -1
    stats['ClusterTimeoutAverageInstrSizeToEnum'] = -1
    stats['ClusterImprovedAverageInstrSizeToEnum'] = -1
    return stats


def parseStats(filePaths):
    # Get logger
    logger = logging.getLogger('parseStats')

    stats = {}
    # Begin stats collection for this run
    for bench in filePaths:
        # first check if log file exists.
        if os.path.exists(filePaths[bench]):
            stats[bench] = {}
            # Open log file if it exists.
            with open(filePaths[bench]) as file:
                # Contain the stats for this benchmark
                curStats = getNewStatsDict()

                # Read the whole log file
                # and split the scheduling
                # regions into a list
                log = file.read()
                blocks = log.split(regionSpliter)[1:]
                for block in blocks:
                    clusterFound = False
                    # Get pass num, if none is found
                    # use third as default.
                    getPass = RE_PASS_NUM.search(block)
                    if getPass:
                        passNum = getPass.group(1)
                        if passNum != 'second':
                            continue
                    else:
                        print('Fatal Error: Could not detect pass number.')
                        sys.exit()

                    curStats['TotalProcessed'] += 1

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
                        clusterFound = True
                        curStats['ClustersRegionCount'] += 1
                        curStats['ClusterTotalGroups'] += totalClusterGroups
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
                    else:
                        continue

                    dagName = ''
                    # If our enumerator was called then
                    # record stats for it.
                    if 'Enumerating' in block:
                        curStats['ClusterEnumCnt'] += 1
                        searchCost = RE_COST_IMPROV.search(block)
                        cost = int(searchCost.group(1))

                        # Get DAG stats
                        dagInfo = RE_DAG_INFO.search(block)
                        dagName = dagInfo.group(1)
                        numOfInstr = int(dagInfo.group(2))
                        curStats['ClusterTotalInstrToEnum'] += numOfInstr

                        if RE_OPTIMAL.search(block):
                            # Optimal and improved
                            if cost > 0:
                                curStats['ClusterImprovedCnt'] += 1
                                curStats['ClusterImprovedTotalInstrToEnum'] += numOfInstr
                                curStats['ClusterOptImpr'] += 1
                                if numOfInstr > curStats['LargestImprovedRegion']:
                                    curStats['LargestImprovedRegion'] = numOfInstr

                            # Optimal but not improved
                            elif cost == 0:
                                curStats['ClusterOptNotImpr'] += 1

                            if largestClusterGroup > curStats['LargestClusterOptimal']:
                                curStats['LargestClusterOptimal'] = largestClusterGroup
                            if numOfInstr > curStats['LargestOptimalRegion']:
                                curStats['LargestOptimalRegion'] = numOfInstr
                        elif 'timedout' in block:
                            # Timeout and improved
                            if cost > 0:
                                curStats['ClusterImprovedCnt'] += 1
                                curStats['ClusterImprovedTotalInstrToEnum'] += numOfInstr
                                curStats['ClusterTimeoutImpr'] += 1
                                if numOfInstr > curStats['LargestImprovedRegion']:
                                    curStats['LargestImprovedRegion'] = numOfInstr

                            # Timeout but not improved
                            elif cost == 0:
                                curStats['ClusterTimeoutNotImpr'] += 1
                            curStats['ClusterTimeoutCnt'] += 1
                            curStats['ClusterTimeoutTotalGroups'] += totalClusterGroups
                            curStats['ClusterTimeoutTotalInstr'] += totalInstrsInClusterInRegion
                            curStats['ClusterTimeoutInstrToEnum'] += numOfInstr

                # Calculate curStats for individual benchmarks
                if curStats['ClusterTotalGroups'] > 0:
                    curStats['ClusterGroupAverage'] = curStats['ClusterTotalInstr'] / \
                        curStats['ClusterTotalGroups']
                if curStats['ClusterTimeoutTotalGroups'] > 0:
                    curStats['ClusterAverageTimeoutSize'] = curStats['ClusterTimeoutTotalInstr'] / \
                        curStats['ClusterTimeoutTotalGroups']
                if curStats['ClusterTimeoutCnt'] > 0:
                    curStats['ClusterTimeoutAverageInstrSizeToEnum'] = curStats['ClusterTimeoutInstrToEnum'] / \
                        curStats['ClusterTimeoutCnt']
                if curStats['ClusterBlocksCnt'] > 0:
                    curStats['ClusterOverallAverageSize'] = curStats['ClusterBlocksSizeCnt'] / \
                        curStats['ClusterBlocksCnt']
                if curStats['ClusterEnumCnt'] > 0:
                    curStats['ClusterAverageInstrSizeToEnum'] = curStats['ClusterTotalInstrToEnum'] / \
                        curStats['ClusterEnumCnt']
                if curStats['ClusterImprovedCnt'] > 0:
                    curStats['ClusterImprovedAverageInstrSizeToEnum'] = curStats['ClusterImprovedTotalInstrToEnum'] / \
                        curStats['ClusterImprovedCnt']

                stats[bench] = curStats
        # If the file doesn't exist, output error log.
        else:
            print('Cannot find log file for benchmark {}.'.format(bench))

    return stats


def printStats(stats):
    for bench in stats:
        print(bench)
        for stat in stats[bench]:
            print('  {}: {}'.format(stat, stats[bench][stat]))


def createSpreadsheets(stats, output):
    if 'csv' not in output[-3:]:
        output += '.csv'

    with open(output, 'w', newline='') as file:
        fieldnames = [
            'Benchmarks',
            'Regions Processed',
            'Regions w/ Clusters',
            'Passed to B&B',
            'Opt. and Impr.',
            'Opt. and not Impr.',
            'Timeout and Impr.',
            'Timeout and not Impr.',
            'Avg. Size of Cluster Groups',
            'Largest Cluster Group',
            'Largest Optimal Cluster Group',
            'Total Cluster Blocks',
            'Overall Avg. Cluster Size',
            'Avg. Size to B&B',
            'Avg. Size of Timeouts',
            'Avg. Size of Improved Regions',
            'Largest Optimal Region',
            'Largest Improved Region'
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for bench in stats:
            rgnsWithClusters = getPercentageString(
                stats[bench]['ClustersRegionCount'], stats[bench]['TotalProcessed'])
            passedToBB = getPercentageString(
                stats[bench]['ClusterEnumCnt'], stats[bench]['ClustersRegionCount'])
            optImpr = getPercentageString(
                stats[bench]['ClusterOptImpr'], stats[bench]['ClusterEnumCnt'])
            optNotImpr = getPercentageString(
                stats[bench]['ClusterOptNotImpr'], stats[bench]['ClusterEnumCnt'])
            timeoutImpr = getPercentageString(
                stats[bench]['ClusterTimeoutImpr'], stats[bench]['ClusterEnumCnt'])
            timeoutNotImpr = getPercentageString(
                stats[bench]['ClusterTimeoutNotImpr'], stats[bench]['ClusterEnumCnt'])

            writer.writerow({
                'Benchmarks': bench,
                'Regions Processed': stats[bench]['TotalProcessed'],
                'Regions w/ Clusters': rgnsWithClusters,
                'Passed to B&B': passedToBB,
                'Opt. and Impr.': optImpr,
                'Opt. and not Impr.': optNotImpr,
                'Timeout and Impr.': timeoutImpr,
                'Timeout and not Impr.': timeoutNotImpr,
                'Avg. Size of Cluster Groups': stats[bench]['ClusterGroupAverage'],
                'Largest Cluster Group': stats[bench]['LargestCluster'],
                'Largest Optimal Cluster Group': stats[bench]['LargestClusterOptimal'],
                'Total Cluster Blocks': stats[bench]['ClusterBlocksCnt'],
                'Overall Avg. Cluster Size': stats[bench]['ClusterOverallAverageSize'],
                'Avg. Size to B&B': stats[bench]['ClusterAverageInstrSizeToEnum'],
                'Avg. Size of Timeouts': stats[bench]['ClusterTimeoutAverageInstrSizeToEnum'],
                'Avg. Size of Improved Regions': stats[bench]['ClusterImprovedAverageInstrSizeToEnum'],
                'Largest Optimal Region': stats[bench]['LargestOptimalRegion'],
                'Largest Improved Region': stats[bench]['LargestImprovedRegion']
            })

        total = getNewStatsDict()
        for bench in stats:
            for stat in statsProcessed:
                total[stat] += stats[bench][stat]
            if total['LargestOptimalRegion'] < stats[bench]['LargestOptimalRegion']:
                total['LargestOptimalRegion'] = stats[bench]['LargestOptimalRegion']
            if total['LargestImprovedRegion'] < stats[bench]['LargestImprovedRegion']:
                total['LargestImprovedRegion'] = stats[bench]['LargestImprovedRegion']
            if total['LargestCluster'] < stats[bench]['LargestCluster']:
                total['LargestCluster'] = stats[bench]['LargestCluster']
            if total['LargestClusterOptimal'] < stats[bench]['LargestClusterOptimal']:
                total['LargestClusterOptimal'] = stats[bench]['LargestClusterOptimal']

        if total['ClusterTotalGroups'] > 0:
            total['ClusterGroupAverage'] = total['ClusterTotalInstr'] / \
                total['ClusterTotalGroups']
        if total['ClusterTimeoutTotalGroups'] > 0:
            total['ClusterAverageTimeoutSize'] = total['ClusterTimeoutTotalInstr'] / \
                total['ClusterTimeoutTotalGroups']
        if total['ClusterTimeoutCnt'] > 0:
            total['ClusterTimeoutAverageInstrSizeToEnum'] = total['ClusterTimeoutInstrToEnum'] / \
                total['ClusterTimeoutCnt']
        if total['ClusterBlocksCnt'] > 0:
            total['ClusterOverallAverageSize'] = total['ClusterBlocksSizeCnt'] / \
                total['ClusterBlocksCnt']
        if total['ClusterEnumCnt'] > 0:
            total['ClusterAverageInstrSizeToEnum'] = total['ClusterTotalInstrToEnum'] / \
                total['ClusterEnumCnt']
        if total['ClusterImprovedCnt'] > 0:
            total['ClusterImprovedAverageInstrSizeToEnum'] = total['ClusterImprovedTotalInstrToEnum'] / \
                total['ClusterImprovedCnt']

        rgnsWithClusters = getPercentageString(
            total['ClustersRegionCount'], total['TotalProcessed'])
        passedToBB = getPercentageString(
            total['ClusterEnumCnt'], total['ClustersRegionCount'])
        optImpr = getPercentageString(
            total['ClusterOptImpr'], total['ClusterEnumCnt'])
        optNotImpr = getPercentageString(
            total['ClusterOptNotImpr'], total['ClusterEnumCnt'])
        timeoutImpr = getPercentageString(
            total['ClusterTimeoutImpr'], total['ClusterEnumCnt'])
        timeoutNotImpr = getPercentageString(
            total['ClusterTimeoutNotImpr'], total['ClusterEnumCnt'])

        writer.writerow({
            'Benchmarks': 'Total',
            'Regions Processed': total['TotalProcessed'],
            'Regions w/ Clusters': rgnsWithClusters,
            'Passed to B&B': passedToBB,
            'Opt. and Impr.': optImpr,
            'Opt. and not Impr.': optNotImpr,
            'Timeout and Impr.': timeoutImpr,
            'Timeout and not Impr.': timeoutNotImpr,
            'Avg. Size of Cluster Groups': total['ClusterGroupAverage'],
            'Largest Cluster Group': total['LargestCluster'],
            'Largest Optimal Cluster Group': total['LargestClusterOptimal'],
            'Total Cluster Blocks': total['ClusterBlocksCnt'],
            'Overall Avg. Cluster Size': total['ClusterOverallAverageSize'],
            'Avg. Size to B&B': total['ClusterAverageInstrSizeToEnum'],
            'Avg. Size of Timeouts': total['ClusterTimeoutAverageInstrSizeToEnum'],
            'Avg. Size of Improved Regions': total['ClusterImprovedAverageInstrSizeToEnum'],
            'Largest Optimal Region': total['LargestOptimalRegion'],
            'Largest Improved Region': total['LargestImprovedRegion']
        })


def main(args):
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Get filepaths for the selected benchmark suite
    filePaths = getBenchmarkFilePaths(args.inputFolder, args.benchmark)

    # Start stats collection
    stats = parseStats(filePaths)

    if args.verbose:
        printStats(stats)

    if not args.disable:
        filename = ''
        if args.output is None:
            filename = os.path.dirname('cluster-stats-' + args.inputFolder)
        else:
            filename = args.output

        createSpreadsheets(stats, filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script to extract OptSched clustering stats',
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

    parser.add_argument('--benchmark', '-b',
                        default='plaid',
                        choices=['plaid', 'shoc'],
                        dest='benchmark',
                        help='Select the benchmarking suite to parse for.')

    args = parser.parse_args()

    main(args)
