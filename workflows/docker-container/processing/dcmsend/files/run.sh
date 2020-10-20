#!/bin/bash

for dir in /$WORKFLOW_DIR/$BATCH_NAME/*
do
        ELEMENT_INPUT_DIR="$dir/$OPERATOR_IN_DIR"

        echo 'Sending potential images from single elements in'
        echo $ELEMENT_INPUT_DIR 
        dcmsend -v $HOST $PORT  --scan-directories --call $AETITLE --scan-pattern '*'  --recurse $ELEMENT_INPUT_DIR
done

BATCH_INPUT_DIR="/$WORKFLOW_DIR/$OPERATOR_IN_DIR"

echo 'Sending potential images from the batch in'
echo $BATCH_INPUT_DIR 
dcmsend -v $HOST $PORT  --scan-directories --call $AETITLE --scan-pattern '*'  --recurse $BATCH_INPUT_DIR

echo "DONE"
