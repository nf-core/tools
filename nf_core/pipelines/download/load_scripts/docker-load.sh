#!/usr/bin/env bash
set -euo pipefail # Ensure that the script exits as early as possible

LOGFILE="podman-load.log"

# Clear log
> "$LOGFILE"

if ! command -v docker &> /dev/null
then
    echo "Error: Docker is not installed. Please install it to continue." >&2
    exit 1
fi

if ! docker info &> /dev/null; then
  echo "Error: Docker daemon is not running." >&2
  exit 1
fi

echo "Loading tar archives into docker"
for tarfile in $(ls -1 *.tar); do
    if output=$(docker load -i $tarfile); then
        echo "SUCCESS: $tarfile"
        echo "SUCCESS: $tarfile"                                                >> "$LOGFILE"
        echo $output                                                            >> "$LOGFILE"
        echo "----------------------------------------------------------------" >> "$LOGFILE"
    else
        echo "ERROR:   $tarfile"
        echo "ERROR:   $tarfile"                                                >> "$LOGFILE"
        echo $output                                                            >> "$LOGFILE"
        echo "----------------------------------------------------------------" >> "$LOGFILE"
    fi
done
