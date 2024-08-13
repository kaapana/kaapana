#!/bin/bash

# default vals
extension_path=""
no_import=""

# help message
print_help() {
    echo "Usage: $0 --dir <chart-path> --chart-name <chartname> [--no-import]"
    echo
    echo "Arguments:"
    echo "  --dir             Path to the extension dir, should contain /extension and /processing-containers folders (required)"
    #TODO echo "  --version         Version of the extension (optional, defaults to KAAPANA_BUILD_VERSION)" 
    echo "  --no-import       Skip importing chart and image files into the platform (optional)"
    echo "  --help            Display help message"
    echo
}

# parse args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dir) extension_path="$2"; shift ;;
        --no-import) no_import="--no-import"; shift ;;
        --help) print_help; exit 0 ;;
        *) echo "Unknown argument: $1"; print_help; exit 1 ;;
    esac
    shift
done

# check if extension_path is empty
if [ -z "$extension_path" ]; then
    echo "ERROR: Extension path is required. Use --dir <extension-path>"
    print_help
    exit 1
fi

# get all Dockerfiles, build and push them to the registry
image_paths=$(find $extension_path -type f \( -name "Dockerfile" -o -name "*.Dockerfile" \) -exec dirname {} \;)
if [ -z "$image_paths" ]; then
    echo "ERROR: No dockerfiles found"
    exit 1
else
    echo "Found Dockerfiles:"
    echo "$image_paths"
fi

for image_path in $image_paths; do
    echo "Building image using Dockerfile in $image_path"
    /usr/bin/bash /kaapana/app/build_image.sh --dir $image_path
done

# TODO: add `custom_registry_url: "localhost:32000"` to values.yaml if not there

# get the Chart.yaml file and build, save, import it into the platform
chart_path=$(find $extension_path -type f \( -name "Chart.yaml" \) -exec dirname {} \;)
chart_count=$(echo "$chart_path" | wc -l)

# if there is no Chart.yaml or there are multiple, exit
if [ "$chart_count" -eq 0 ]; then
    echo "ERROR: No Chart.yaml file found."
    exit 1
elif [ "$chart_count" -gt 1 ]; then
    echo "ERROR: Multiple Chart.yaml files found:"
    echo "$chart_path"
    exit 1
else
    echo "Found Chart.yaml:"
    echo "$chart_path"
fi

echo "Building chart $chart_path"
/usr/bin/bash /kaapana/app/build_chart.sh --dir $chart_path
