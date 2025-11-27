#!/usr/bin/env bash
# This hook is used to block commits if they include staged files inside a directory
# which also contains a subdirectory called `pipeline_info`. The purpose of this is to
# prevent users from inadvertently committing output from pipeline test runs inside the
# development directory.

set -e

# list staged files
staged_files="$(git diff --cached --name-only)"

status=0

for file in $staged_files; do
    file_dir=$(dirname "$file")

    # Walk up the directory tree and check if the current directory contains a subdirectory called `pipeline_info`
    # or the staged file is itself inside a directory called `pipeline_info`.
    while [ "$file_dir" != "." ] && [ "$file_dir" != "/" ]; do
        if [ $(basename "$file_dir") == "pipeline_info" ] || [ -d "$file_dir/pipeline_info" ]; then
        echo "❌ Commit blocked: Please do not commit output from pipeline test runs to the pipeline code itself."
        echo "Use 'git restore --staged <file>...' to remove the output files from the staging area before proceeding."
        status=1
        break
        fi
        file_dir=$(dirname "$file_dir")
    done
done

exit "$status"
