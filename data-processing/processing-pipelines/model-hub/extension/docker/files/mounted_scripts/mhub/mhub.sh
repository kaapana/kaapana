#!/bin/bash

for dir in $WORKFLOW_DIR/$BATCH_NAME/*
do
        ELEMENT_INPUT_DIR="$dir/$OPERATOR_IN_DIR"
        echo 'Reading from:'
        echo ${ELEMENT_INPUT_DIR}

        ELEMENT_OUTPUT_DIR="$dir/$OPERATOR_OUT_DIR"
        echo 'Writing to:'
        echo ${ELEMENT_OUTPUT_DIR}

        mv $ELEMENT_INPUT_DIR/* /app/data/input_data
        { # try

            python3 /app/mhub/$MHUB_MODEL/scripts/run.py &&
            mv /app/data/output_data/* $ELEMENT_OUTPUT_DIR
            mv /app/data/input_data/* $ELEMENT_INPUT_DIR
        } || { # catch
            mv /app/data/input_data/* $ELEMENT_INPUT_DIR
            exit 1
        }
done