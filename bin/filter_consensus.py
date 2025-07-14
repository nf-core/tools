#!/usr/bin/env python3
"""
Filter FASTA sequences by removing those with fewer than 100 A, T, C, or G bases.
Ignores N and other ambiguous bases in the count.
"""

import sys
import argparse
import gzip
from pathlib import Path

def count_atcg_bases(sequence):
    """Count only A, T, C, G bases in a sequence (case-insensitive)."""
    return sum(1 for base in sequence.upper() if base in 'ATCG')

def open_file(filename):
    """Open a file, handling both regular and gzipped files."""
    if filename.endswith('.gz'):
        return gzip.open(filename, 'rt')
    else:
        return open(filename, 'r')

def filter_fasta(input_file, output_file, min_bases=100):
    """
    Filter FASTA sequences based on ATCG base count.

    Args:
        input_file: Path to input FASTA file
        output_file: Path to output FASTA file
        min_bases: Minimum number of ATCG bases required (default: 100)
    """
    sequences_kept = 0
    sequences_removed = 0

    with open_file(input_file) as infile, open(output_file, 'w') as outfile:
        current_header = None
        current_sequence = []

        for line in infile:
            line = line.strip()

            if line.startswith('>'):
                # Process previous sequence if it exists
                if current_header is not None:
                    sequence = ''.join(current_sequence)
                    atcg_count = count_atcg_bases(sequence)

                    if atcg_count >= min_bases:
                        outfile.write(current_header + '\n')
                        outfile.write(sequence + '\n')
                        sequences_kept += 1
                    else:
                        sequences_removed += 1

                # Start new sequence
                current_header = line
                current_sequence = []
            else:
                # Add to current sequence
                current_sequence.append(line)

        # Process the last sequence
        if current_header is not None:
            sequence = ''.join(current_sequence)
            atcg_count = count_atcg_bases(sequence)

            if atcg_count >= min_bases:
                outfile.write(current_header + '\n')
                outfile.write(sequence + '\n')
                sequences_kept += 1
            else:
                sequences_removed += 1

    # Print summary
    if sequences_kept > 0:
        print(f"Filtering complete:")
        print(f"  Sequences kept: {sequences_kept}")
        print(f"  Sequences removed: {sequences_removed}")
        print(f"  Minimum ATCG bases required: {min_bases}")
    else:
        print(f"No sequences passed the filtering criteria (min {min_bases} ATCG bases).")
        print(f"  Total sequences processed: {sequences_removed}")
        # Remove the empty output file
        Path(output_file).unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(
        description="Filter FASTA sequences by ATCG base count",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fasta_filter.py input.fasta output.fasta
  python fasta_filter.py input.fasta output.fasta --min-bases 50
  python fasta_filter.py input.fasta output.fasta -m 50
        """
    )

    parser.add_argument('input_file', help='Input FASTA file')
    parser.add_argument('output_file', help='Output FASTA file')
    parser.add_argument('-m', '--min-bases', type=int, default=100,
                        help='Minimum number of ATCG bases required (default: 100)')

    args = parser.parse_args()

    # Check if input file exists
    if not Path(args.input_file).exists():
        print(f"Error: Input file '{args.input_file}' not found.", file=sys.stderr)
        sys.exit(1)

    # Check if output directory exists
    output_dir = Path(args.output_file).parent
    if not output_dir.exists():
        print(f"Error: Output directory '{output_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    try:
        filter_fasta(args.input_file, args.output_file, args.min_bases)
    except Exception as e:
        print(f"Error processing files: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
