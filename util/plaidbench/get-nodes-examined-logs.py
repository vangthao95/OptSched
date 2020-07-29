#!/usr/bin/python3
import argparse
from OptSched import *
import re

regex = re.compile("Examined (\d+) nodes")


def parseStats(filePath):
    stats = {}
    with open(filePath) as file:
        log = file.read()
        blocks = log.split(regionSpliter)[1:]
        for block in blocks:
            if RE_OPTIMAL.search(block) and 'Enumerating' in block:
                getDagInfo = RE_DAG_INFO.search(block)
                dagName = getDagInfo.group(1)
                searchResult = regex.search(block)
                if (searchResult):
                    nodesExamined = int(searchResult.group(1))
                    stats[dagName] = nodesExamined
    print(len(stats.keys()))
    return stats


def processStats(stats1, stats2):
    total1 = 0
    total2 = 0
    maxDiff = -1
    maxDiffName = ''
    for dagName1 in stats1:
        if dagName1 in stats2:
            diff = abs(stats1[dagName1] - stats2[dagName1])
            if diff > maxDiff:
                maxDiff = diff
                maxDiffName = dagName1
            total1 += stats1[dagName1]
            total2 += stats2[dagName1]

    print('File 1 nodes examined: {}'.format(total1))
    print('File 2 nodes examined: {}'.format(total2))
    diff = total1 - total2
    pcnt = diff / total1 * 100
    print('Difference in nodes examined: {} ({:.2f}%)'.format(diff, pcnt))
    print('Most difference in dag: {} with a difference of {}'.format(
        maxDiffName, maxDiff))


def main(args):
    # Start stats collection
    stats1 = parseStats(args.inputFile1)
    stats2 = parseStats(args.inputFile2)
    processStats(stats1, stats2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script to extract OptSched nodes examined',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        dest='inputFile1',
        help='The path to a OptSched log')

    parser.add_argument(
        dest='inputFile2',
        help='The path to a OptSched log')

    args = parser.parse_args()

    main(args)
