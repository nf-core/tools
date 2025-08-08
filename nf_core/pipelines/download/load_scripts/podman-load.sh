#!/usr/bin/env bash
set -euo pipefail # Ensure that the script exits as early as possible

LOGFILE="podman-load.log"

# Clear log
> "$LOGFILE"

PODMAN_LOAD_SINGLE_IMAGE() {
    local TARFILE="$1"

    # Look for the full image name in the mainfest.json
    # inside the image tar archive. It is contained in
    # this RepoTags field
    REPO_TAG=$(tar -O -xf "$TARFILE" manifest.json \
        | jq -r '.[0].RepoTags[0]')

    if [[ -z "$REPO_TAG" || "$REPO_TAG" == "null" ]]; then
        echo "Error: Could not find RepoTags in $TARFILE" >&2
        exit 1
    fi

    # Load the tar archive into podman -- this will typically
    # save it as localhost/..., which won't work if we want to
    # use the images in the nf-core pipeline
    PODMAN_LOAD_OUTPUT=$(podman load -i "$TARFILE" 2>&1)

    # Extract the tag podman created for the image for later renaming
    LOCAL_TAG=$(echo "$PODMAN_LOAD_OUTPUT" | sed -n 's/^Loaded image(s): \(.*\)$/\1/p')

    if [[ -z "$LOCAL_TAG" ]]; then
        echo "Error: Could not parse loaded image name from podman load output" >&2
        exit 1
    fi

    # Tag the loaded image with the original remote name
    podman tag "$LOCAL_TAG" "$REPO_TAG"

    echo "Success, loaded and tagged: $REPO_TAG"
}

echo "Loading tar archives into podman"
for tarfile in $(ls -1 *.tar); do
    if output=$(PODMAN_LOAD_SINGLE_IMAGE $tarfile); then
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
