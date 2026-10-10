#!/usr/bin/env bash
set -euo pipefail # Ensure that the script exits as early as possible

LOGFILE="appleContainer-load.log"

# Clear log
> "$LOGFILE"

if ! command -v container &> /dev/null
then
    echo "Error: Apple Container CLI ('container') is not installed. Please install it to continue." >&2
    echo "See: https://github.com/apple/container" >&2
    exit 1
fi

echo "Loading tar archives into Apple Container"
for tarfile in $(ls -1 *.tar); do
    if output=$(container load < "$tarfile" 2>&1); then
        echo "SUCCESS: $tarfile"
        echo "SUCCESS: $tarfile"                                                >> "$LOGFILE"
        echo "$output"                                                          >> "$LOGFILE"
        echo "----------------------------------------------------------------" >> "$LOGFILE"
    else
        echo "ERROR:   $tarfile"
        echo "ERROR:   $tarfile"                                                >> "$LOGFILE"
        echo "$output"                                                          >> "$LOGFILE"
        echo "----------------------------------------------------------------" >> "$LOGFILE"
    fi
done
