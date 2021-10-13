#!/usr/bin/env python

# TODO nf-core: Update the script to check the samplesheet
# This script is based on the example at:
# https://raw.githubusercontent.com/nf-core/test-datasets/viralrecon/samplesheet/samplesheet_test_illumina_amplicon.csv


import argparse
import csv
import logging
import sys
from collections import Counter
from pathlib import Path


logger = logging.getLogger()


class RowChecker:

    VALID_FORMATS = (
        ".fq.gz",
        ".fastq.gz",
    )

    def __init__(
        self,
        sample_col="sample",
        first_col="fastq_1",
        second_col="fastq_2",
        single_col="single_end",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.sample_col = sample_col
        self.first_col = first_col
        self.second_col = second_col
        self.single_col = single_col
        self.seen = set()
        self.modified = []

    def validate(self, row):
        self._validate_sample(row)
        self._validate_first(row)
        self._validate_second(row)
        self._validate_pair(row)
        self.seen.add((row[self.sample_col], row[self.first_col]))
        self.modified.append(row)

    def _validate_sample(self, row):
        assert len(row[self.sample_col]) > 0, "Sample input is required."
        # Sanitize samples slightly.
        row[self.sample_col] = row[self.sample_col].replace(" ", "_")

    def _validate_first(self, row):
        assert len(row[self.first_col]) > 0, "At least the first FASTQ file is required."
        self._validate_fastq_format(row[self.first_col])

    def _validate_second(self, row):
        if len(row[self.second_col]) > 0:
            self._validate_fastq_format(row[self.second_col])

    def _validate_pair(self, row):
        if row[self.first_col] and row[self.second_col]:
            row[self.single_col] = False
            assert (
                Path(row[self.first_col]).suffixes == Path(row[self.second_col]).suffixes
            ), "FASTQ pairs must have the same file extensions."
        else:
            row[self.single_col] = True

    def _validate_fastq_format(self, filename):
        assert any(filename.endswith(extension) for extension in self.VALID_FORMATS), (
            f"The FASTQ file has an unrecognized extension: {filename}\n"
            f"It should be one of: {', '.join(self.VALID_FORMATS)}"
        )

    def validate_unique_samples(self):
        assert len(self.seen) == len(self.modified), "The pair of sample name and FASTQ must be unique."
        if len({pair[0] for pair in self.seen}) < len(self.seen):
            counts = Counter(pair[0] for pair in self.seen)
            seen = Counter()
            for row in self.modified:
                sample = row[self.sample_col]
                seen[sample] += 1
                if counts[sample] > 1:
                    row[self.sample_col] = f"{sample}_T{seen[sample]}"


# TODO nf-core: Update the check_samplesheet function
def check_samplesheet(file_in, file_out):
    """
    This function checks that the samplesheet follows the following structure:

    sample,fastq_1,fastq_2
    SAMPLE_PE,SAMPLE_PE_RUN1_1.fastq.gz,SAMPLE_PE_RUN1_2.fastq.gz
    SAMPLE_PE,SAMPLE_PE_RUN2_1.fastq.gz,SAMPLE_PE_RUN2_2.fastq.gz
    SAMPLE_SE,SAMPLE_SE_RUN1_1.fastq.gz,

    For an example see:
    https://raw.githubusercontent.com/nf-core/test-datasets/viralrecon/samplesheet/samplesheet_test_illumina_amplicon.csv
    """
    required_columns = {"sample", "fastq_1", "fastq_2"}
    with file_in.open() as in_handle:
        # Validate the existence of the expected header columns.
        peek = in_handle.read(2048)
        sniffer = csv.Sniffer()
        if not sniffer.has_header(peek):
            logger.critical(f"The given sample sheet does not appear to contain a header.")
            sys.exit(1)
        dialect = sniffer.sniff(peek)
        in_handle.seek(0)
        reader = csv.DictReader(in_handle, dialect=dialect)
        if not required_columns.issubset(reader.fieldnames):
            logger.critical(f"The sample sheet **must** contain the column headers: {', '.join(required_columns)}.")
            sys.exit(1)
        # Validate each row.
        checker = RowChecker()
        for i, row in enumerate(reader):
            try:
                checker.validate(row)
            except AssertionError as error:
                logger.critical(f"{str(error)} On line {i + 2}.")
                sys.exit(1)
        checker.validate_unique_samples()
    header = list(reader.fieldnames)
    header.insert(1, "single_end")
    with file_out.open("w") as out_handle:
        writer = csv.DictWriter(out_handle, header, delimiter=",")
        writer.writeheader()
        for row in checker.modified:
            writer.writerow(row)


def parse_args(args=None):
    """Define and immediately parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Reformat {{ name }} samplesheet file and check its contents.",
        epilog="Example usage: python check_samplesheet.py samplesheet.csv samplesheet.valid.csv",
    )
    parser.add_argument("file_in", metavar="FILE_IN", type=Path, help="Input sample sheet.")
    parser.add_argument("file_out", metavar="FILE_OUT", type=Path, help="Output file.")
    parser.add_argument(
        "-l",
        "--log-level",
        help="The desired log level (default WARNING).",
        choices=("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"),
        default="WARNING",
    )
    return parser.parse_args(args)


def main(args=None):
    """Coordinate argument parsing and program execution."""
    args = parse_args(args)
    logging.basicConfig(level=args.log_level, format="[%(levelname)s] %(message)s")
    if not args.file_in.is_file():
        logger.error(f"The given input file {args.file_in} was not found!")
        sys.exit(2)
    args.file_out.parent.mkdir(parents=True, exist_ok=True)
    check_samplesheet(args.file_in, args.file_out)


if __name__ == "__main__":
    sys.exit(main())
