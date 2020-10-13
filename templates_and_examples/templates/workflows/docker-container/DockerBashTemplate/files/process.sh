#!/bin/bash

for dir in /$WORKFLOW_DIR/$BATCH_NAME/*    
do
        ELEMENT_INPUT_DIR="$dir/$OPERATOR_IN_DIR"
        echo 'Here you find the files you want to work with on a batch element level'
        echo ${ELEMENT_INPUT_DIR}
        ELEMENT_OUTPUT_DIR="$dir/$OPERATOR_OUT_DIR"
        echo 'Here you should write the files that you generate on a batch element level'
        echo ${ELEMENT_OUTPUT_DIR}
done

BATCH_INPUT_DIR="/$WORKFLOW_DIR/$OPERATOR_IN_DIR"
echo 'Here you find the files you want to work with on a batch level'
echo ${BATCH_INPUT_DIR}
BATCH_OUTPUT_DIR="/$WORKFLOW_DIR/$OPERATOR_OUT_DIR"
echo 'Here you should write the files that you generate on a batch level'
echo ${BATCH_OUTPUT_DIR}