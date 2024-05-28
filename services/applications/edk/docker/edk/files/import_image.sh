#!/bin/bash

tar_file=""

# parse filename argument
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --tar-file) tar_file="$2"; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
    shift
done

# check if tar_file is empty
if [ -z "$tar_file" ]; then
    echo "ERROR: Tar file name is required. Use --tar-file <file>.tar"
    exit 1
fi

curl -G "$KUBE_HELM_URL/import-container" --data-urlencode "filename=$tar_file"