#!/usr/bin/env python
# TODO nf-core: Update the script to check the samplesheet

import os
import sys
import errno
import argparse

def parse_args(args=None):
    Description = 'Reformat {{ cookiecutter.name }} samplesheet file and check its contents.'
    Epilog = """Example usage: python check_samplesheet.py <FILE_IN> <FILE_OUT>"""

    parser = argparse.ArgumentParser(description=Description, epilog=Epilog)
    parser.add_argument('FILE_IN', help="Input samplesheet file.")
    parser.add_argument('FILE_OUT', help="Output file.")
    return parser.parse_args(args)


def make_dir(path):
    if len(path) > 0:
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise exception


def print_error(error,line):
    print("ERROR: Please check samplesheet -> {}\nLine: '{}'".format(error,line.strip()))
    sys.exit(1)

# TODO nf-core: Update the check_samplesheet function
def check_samplesheet(file_in,file_out):
    """This check shampleseet function checks that the sample sheet follows the following structure:
    sample, fastq_1, fastq_2
    sample1, Sample1.fastq.gz, Sample2.fastq.gz
    """

    sample_run_dict = {}
    with open(file_in, 'r') as fin:

        # TODO nf-core: Update the column names for the input samplesheet
        ## Check header
        HEADER = ['sample', 'fastq_1', 'fastq_2']
        header = fin.readline().strip().split(',')
        if header != HEADER:
            print("ERROR: Please check samplesheet header -> {} != {}".format(','.join(header),','.join(HEADER)))
            sys.exit(1)

        ## Check sample entries
        for line in fin:
            lspl = [x.strip() for x in line.strip().split(',')]

            ## Check valid number of columns per row
            if len(lspl) != len(header):
                print_error("Invalid number of columns (minimum = {})!".format(len(header)),line)

            num_cols = len([x for x in lspl if x])
            if num_cols < 2:
                print_error("Invalid number of populated columns (minimum = 2)!".format(line))

            ## Check sample name entries
            sample,fastq_files = lspl[0],lspl[1:]
            if sample:
                if sample.find(' ') != -1:
                    print_error("Sample entry contains spaces!",line)
            else:
                print_error("Sample entry has not been specified!",line)

            ## Check FastQ file extension
            for fastq in fastq_files:
                if fastq:
                    if fastq.find(' ') != -1:
                        print_error("FastQ file contains spaces!",line)
                    if not fastq.endswith('.fastq.gz') and not fastq.endswith('.fq.gz'):
                        print_error("FastQ file does not have extension '.fastq.gz' or '.fq.gz'!",line)

            ## Auto-detect paired-end/single-end
            sample_info = []                             ## [single_end, fastq_1, fastq_2]
            fastq_1,fastq_2 = fastq_files
            if sample and fastq_1 and fastq_2:           ## Paired-end short reads
                sample_info = ['0', fastq_1, fastq_2]
            elif sample and fastq_1 and not fastq_2:     ## Single-end short reads
                sample_info = ['1', fastq_1, fastq_2]
            else:
                print_error("Invalid combination of columns provided!",line)

            if sample not in sample_run_dict:
                sample_run_dict[sample] = [sample_info]
            else:
                if sample_info in sample_run_dict[sample]:
                    print_error("Samplesheet contains duplicate rows!",line)
                else:
                    sample_run_dict[sample].append(sample_info)

    ## Write validated samplesheet with appropriate columns
    if len(sample_run_dict) > 0:
        out_dir = os.path.dirname(file_out)
        make_dir(out_dir)
        fout = open(file_out,'w')
        fout.write(','.join(['sample', 'single_end', 'fastq_1', 'fastq_2']) + '\n')
        for sample in sorted(sample_run_dict.keys()):

            ## Check that multiple runs of the same sample are of the same datatype
            if not all(x[0] == sample_run_dict[sample][0][0] for x in sample_run_dict[sample]):
                print_error("Multiple runs of a sample must be of the same datatype","Sample: {}".format(sample))

            for idx,val in enumerate(sample_run_dict[sample]):
                fout.write(','.join(["{}_T{}".format(sample,idx+1)] + val) + '\n')
        fout.close()


def main(args=None):
    args = parse_args(args)
    check_samplesheet(args.FILE_IN,args.FILE_OUT)


if __name__ == '__main__':
    sys.exit(main())
