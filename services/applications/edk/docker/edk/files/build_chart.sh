#!/bin/bash
set -euf -o pipefail

# default vals
chart_path=""
no_import=""

# help message
print_help() {
    echo "Usage: $0 --dir <chart-path> --chart-name <chartname> [--no-import]"
    echo
    echo "Arguments:"
    echo "  --dir             Path to the chart directory (required)"
    echo "  --no-import       Skip importing chart as an extension"
    echo "  --help            Display this help message"
    echo
}

# parse args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dir) chart_path="$2"; shift ;;
        --no-import) no_import="true"; shift ;;
        --help) print_help; exit 0 ;;
        *) echo "Unknown argument: $1"; print_help; exit 1 ;;
    esac
    shift
done

# check if chart_path is empty
if [ -z "$chart_path" ]; then
    echo "ERROR: Chart path is required. Use --dir <chart-path>"
    print_help
    exit 1
fi

# change version of Helm chart to Kaapana version
cd $chart_path
sed -i "s/^version: \".*\"/version: \"$KAAPANA_BUILD_VERSION\"/" "$chart_path/Chart.yaml"

# build helm chart
echo "building Helm chart $chart_path"

# Extract the file name from the output
helm dep up
output=$(helm package .)
chart_file=$(echo "$output" | awk '{print $NF}')

# check if --no-import is passed
if [ "$no_import" != "true" ]; then
    # send req to kube-helm /file endpoint for importing tgz as a chart
    echo "Importing chart tgz..."
    curl -X POST "$KUBE_HELM_URL/file" -F "file=@$chart_file;type=application/gzip"
else
    echo "Skipping import."
fi