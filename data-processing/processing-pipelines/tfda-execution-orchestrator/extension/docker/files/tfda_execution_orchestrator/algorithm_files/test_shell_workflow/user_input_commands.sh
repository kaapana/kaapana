#!/bin/bash
echo "Hello World"
results_folder='/home/ubuntu/results'
dir='/home/ubuntu/test-site-data'

if [ -z "$(ls -A $dir)" ]; then
  echo "Data bucket is empty" >> "$results_folder"/out.txt
else
  for entry in $dir/*
  do
   echo "$entry" >> "$results_folder"/out.txt
  done
fi
