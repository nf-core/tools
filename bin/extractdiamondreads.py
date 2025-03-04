#!/usr/bin/env python

import argparse
import subprocess

def parse_args(args=None):
    Description = "Extract reads of specified taxonomic ID from the output of DIAMOND/blastx classification."
    parser = argparse.ArgumentParser(description=Description)
    parser.add_argument("--tsv", required=True, help="Path to the DIAMOND output TSV file.")
    parser.add_argument("--taxid", required=True, help="Taxonomic ID to extract the reads.")
    parser.add_argument("--evalue", required=True, type=float, help="E-value threshold to filter the DIAMOND classification result.")
    parser.add_argument("--prefix", required=True, help="Prefix for output files.")
    parser.add_argument("--single_end", action="store_true", help="Flag for single-end reads.")
    parser.add_argument("--fastq", required=True, nargs='+', help="Paths to input FASTQ files.")

    return parser.parse_args(args)

def extract_reads_by_taxid(tsv_path, taxid, evalue, fastq_paths, single_end, prefix):
    read_id_file = f"{prefix}_readID.txt"

    # Step 1: Filter the DIAMOND tsv file and collect read IDs by taxid and e-value threshold
    with open(tsv_path, 'r') as tsv, open(read_id_file, 'w') as out:
        for line in tsv:
            parts = line.strip().split('\t')
            current_taxid = parts[1]
            current_evalue = float(parts[2])
            if current_taxid == taxid and current_evalue < evalue:
                out.write(parts[0] + "\n")

    # Step 2: Extract reads using seqkit
    output_files = []

    if single_end:
        output_file = f"{prefix}_{taxid}.extracted_diamond_reads.fastq"
        subprocess.run(["seqkit", "grep", "-f", read_id_file, fastq_paths[0], "-o", output_file], check=True)
        output_files.append(output_file)
    else:
        output_file1 = f"{prefix}_{taxid}.extracted_diamond_read1.fastq"
        output_file2 = f"{prefix}_{taxid}.extracted_diamond_read2.fastq"
        subprocess.run(["seqkit", "grep", "-f", read_id_file, fastq_paths[0], "-o", output_file1], check=True)
        subprocess.run(["seqkit", "grep", "-f", read_id_file, fastq_paths[1], "-o", output_file2], check=True)
        output_files.extend([output_file1, output_file2])

    # Clean up temporary files (optional, uncomment if needed)
    # os.remove(read_id_file)

    return output_files

def main(args=None):
    args = parse_args(args)
    extract_reads_by_taxid(
        tsv_path=args.tsv,
        taxid=args.taxid,
        evalue=args.evalue,
        prefix=args.prefix,
        single_end=args.single_end,
        fastq_paths=args.fastq
    )

if __name__ == "__main__":
    main()
