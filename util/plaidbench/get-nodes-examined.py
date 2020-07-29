#!/usr/bin/python3
# WIP, currently doesn't work as expected

import argparse
import csv
import logging
import re
from OptSched import *

regex = re.compile("Examined (\d+) nodes")


def parseStats(filePaths):
    # Get logger
    logger = logging.getLogger('parseStats')

    # Overall stats for the benchmark suite
    stats = {}

    for bench in filePaths:
        # First check if log file exists.
        if os.path.exists(filePaths[bench]):
            # Open log file if it exists.
            with open(filePaths[bench]) as file:
                curStats = {}
                log = file.read()
                blocks = log.split(regionSpliter)[1:]
                for block in blocks:
                    if RE_OPTIMAL.search(block) and 'Enumerating' in block:
                        getDagInfo = RE_DAG_INFO.search(block)
                        dagName = getDagInfo.group(1)
                        searchResult = regex.search(block)
                        print(block)
                        if (searchResult):
                            nodesExamined = int(searchResult.group(1))
                            curStats[dagName] = nodesExamined
                stats = curStats
        else:
            print('Cannot find log file {}.'.format(filePaths[bench]))
        break
    return stats


def processStats(stats1, stats2):
    stats = {}
    for bench in stats1:
        if bench not in stats2:
            print('Warning: Unable to find benchmark {} in input folder 2'.format(bench))
            continue

        curStats = {}
        curStats['total1'] = 0
        curStats['total2'] = 0
        curStats['maxDiff'] = -1
        curStats['maxDiffName'] = ''

        for dagName1 in stats1[bench]:
            if dagName1 in stats2[bench]:
                diff = abs(stats1[bench][dagName1] - stats2[bench][dagName1])
                if diff > curStats['maxDiff']:
                    curStats['maxDiff'] = diff
                    curStats['maxDiffName'] = dagName1
                curStats['total1'] += stats1[dagName1]
                curStats['total2'] += stats2[dagName1]

        stats[bench] = curStats

    return stats


def createSpreadsheets(stats, filename):
    pass


def main(args):

    # Get filepaths for the selected benchmark suite
    filePaths1 = getBenchmarkFilePaths(args.inputFolder1, args.benchmark)
    filePaths2 = getBenchmarkFilePaths(args.inputFolder2, args.benchmark)

    # Start stats collection
    stats1 = parseStats(filePaths1)
    stats2 = parseStats(filePaths2)

    difference = processStats(stats1, stats2)
    print(difference)

    # Print stats if enabled
    # if args.verbose:
    #    printStats(stats1)

    # Create spreadsheet
    if not args.disable:
        filename = ''
        if args.output is None:
            filename = os.path.dirname('examined-nodes-' + args.inputFolder2)
        else:
            filename = args.output

        createSpreadsheets(difference, filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script to extract OptSched nodes examined',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        dest='inputFolder1',
        help='The path to a benchmark directory')

    parser.add_argument(
        dest='inputFolder2',
        help='The path to a benchmark directory')

    parser.add_argument('--verbose', '-v',
                        action='store_true', default=False,
                        dest='verbose',
                        help='Print average occupancy to terminal')

    parser.add_argument(
        '--output', '-o',
        dest='output',
        help='Output spreadsheet filepath')

    parser.add_argument('--disable', '-d',
                        action='store_true', default=False,
                        dest='disable',
                        help='Disable spreadsheet output.')

    parser.add_argument(
        '--benchmark', '-b', default='plaid',
        choices=['plaid', 'shoc'],
        dest='benchmark',
        help='Select the benchmarking suite to parse for.')

    args = parser.parse_args()

    main(args)
