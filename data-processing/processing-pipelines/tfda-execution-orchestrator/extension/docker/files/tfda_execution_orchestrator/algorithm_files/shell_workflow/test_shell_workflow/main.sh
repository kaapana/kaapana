#!/bin/bash
echo "Hello World"

### Parsing command line arguments:
usage="$(basename "$0")

_Argument: --input [Data directory on the isolated VM]
_Argument: --output [Results directory on the isolated VM]"


while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in

        -i|--input)
            dir="$2"
            echo -e "Path to data $dir";
            shift # past argument
            shift # past value
        ;;

        -p|--output)
            results_folder="$2"
            echo -e "Results path $results_folder";
            shift # past argument
            shift # past value
        ;;

    esac
done

# Check if the directory exists
if [ ! -d $dir ]; then
  echo "Directory does not exist."
  exit 1
fi

# Loop through all files in the directory
for file in $dir/*; do
  # Check if the file is a regular file
  if [ -f $file ]; then
    # Get the file name
    file_name=$(basename $file)
    # Get the file content
    file_content=$(cat $file)
    # Write the file content to a new file with the same name
    echo "$file_content" > "${results_folder}/out.txt"
  fi
done

echo "Done."
