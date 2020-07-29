# Contain common functionalies for most scripts.
# Not meant to be use as a standalone script.

import re
import os


##############################################################################
# Regular expressions
##############################################################################
# Each region output this log so use this to split each scheduling region
regionSpliter = '********** Opt Scheduling **********'
# Regular expression to get the DAG name, instructions, and max latency
RE_DAG_INFO = re.compile(
    'Processing DAG (.*) with (\d+) insts and max latency (\d+)')
# Get the pass number, usually 'first' or 'second'.
RE_PASS_NUM = re.compile(r'End of (.*) pass through')
# Get the amount of cost improvement.
RE_COST_IMPROV = re.compile(r'cost imp=(\d+).')
# Detect if a schedule is optimal
RE_OPTIMAL = re.compile(r'The schedule is optimal')
# Detect if the schedule was reverted
RE_REVERT_SCHED = re.compile(
    r'Reverting Scheduling because of a decrease in occupancy from')
# Get the lower bound cost
RE_DAG_COST_LOWER_BOUND = re.compile(
    r'Lower bound of cost before scheduling: (\d+)')
# Best cost for DAG
RE_DAG_COST = re.compile(
    r'INFO: Best schedule for DAG (.*) has cost (\d+) and length (\d+). The schedule is (.*) \(Time')
# RE for Occupancy. Must have print occupancy patch applied to LLVM.
RE_OCCUPANCY = re.compile('Final occupancy for function (.*):(\d+)')
RE_SCHED_LENGTH = re.compile(r'The list schedule is of length (\d+) and')
RE_CLUSTER = re.compile(r'Total clusterable instructions: (\d+) loads, (\d+) stores')
RE_CLUSTER_GROUPS = re.compile(r'Cluster (\d+) has total instructions (\d+)')
RE_CLUSTER_ENUM = re.compile(r'Printing cluster (\d+), start cycle \(.*\): (.*)')
CLUSTER_START = 'Printing clustered instructions:'
RE_ENUMERATING_LENGTH = re.compile(r'Enumerating at target length (\d+)')


shoc_benchmarks = [
    # 'BusSpeedDownload',
    # 'BusSpeedReadback',
    # 'MaxFlops',
    # 'DeviceMemory',
    # 'KernelCompile',
    # 'QueueDelay',
    # 'BFS',
    'FFT',
    'GEMM',
    'MD',
    # 'MD5Hash',
    # 'Reduction',
    # 'Scan',
    'Sort',
    'Spmv',
    'Stencil2D',
    # 'Triad',
    # 'S3D'
]

plaidbench = [
    'densenet121',
    'densenet169',
    'densenet201',
    'inception_resnet_v2',
    'inception_v3',
    'mobilenet',
    'nasnet_large',
    'nasnet_mobile',
    'resnet50',
    'vgg16',
    'vgg19',
    'xception',
    'imdb_lstm',
]

# Ignore these functions on the AMDGPU
# They are outputted before scheduling
ignore = [
    'copyBufferRect',
    'copyBufferRectAligned',
    'copyBuffer',
    'copyBufferAligned',
    'fillBuffer',
    'copyBufferToImage',
    'copyImageToBuffer',
    'copyImage',
    'copyImage1DA',
    'fillImage',
    'scheduler'
]


def getBenchmarkFilePaths(inputFolder, benchmark):
    """
    Returns a directionary mapping a benchmark to its corresponding file.

    Parameters:
    inputFolder -- A string containing the name of a directory with plaidbench or SHOC results.
    isShoc - Commandline argument indicating whether shoc was selected or not.

    Returns:
    dictionary: Keys: Benchmark names, Values: Paths to the OptSched logs for the corresponding benchmark
    """
    filepaths = {}

    # Do a lowercase string comparison to determine the benchmark set
    bench = benchmark.lower()

    # Paths for shoc benchmarks
    if bench == 'shoc':
        logDirectory = os.path.join(inputFolder, 'Logs')
        for bench in shoc_benchmarks:
            filename = 'dev0_{}.err'.format(bench)
            filepath = os.path.join(logDirectory, filename)
            filepaths[bench] = filepath

    # Paths for PlaidML benchmarks
    elif bench == 'plaid':
        for bench in plaidbench:
            benchmarkDirectory = os.path.join(inputFolder, bench)
            filename = '{}.log'.format(bench)
            filepath = os.path.join(benchmarkDirectory, filename)
            filepaths[bench] = filepath

    return filepaths


if __name__ == '__main__':
    print('Fatal Error: Not meant to be used as a standalone script!')
