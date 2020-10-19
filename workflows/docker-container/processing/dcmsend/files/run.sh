#!/bin/bash

for dir in /$WORKFLOW_DIR/$BATCH_NAME/*    
do
        ELEMENT_INPUT_DIR="$dir/$OPERATOR_IN_DIR"

        echo 'Sending images in $ELEMENT_INPUT_DIR'
        dcmsend -v $HOST $PORT  --scan-directories --call $AETITLE --scan-pattern '*'  --recurse $ELEMENT_INPUT_DIR
done

echo "DONE"
