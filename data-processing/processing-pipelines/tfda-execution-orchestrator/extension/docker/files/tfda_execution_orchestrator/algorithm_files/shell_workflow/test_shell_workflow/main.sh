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


if [ -z "$(ls -A $dir)" ]; then
  echo "Data bucket is empty" >> "$results_folder"/out.txt
else
  for entry in $dir/*
  do
   echo "$entry" >> "$results_folder"/out.txt
  done
fi
