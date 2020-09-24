#!/bin/bash

if [ -z $DICOM_DIR ]; then DICOM_DIR=$WORKFLOW_DIR/$OPERATOR_IN_DIR; fi

echo 'Sending images in $DICOM_DIR' 

dcmsend -v $HOST $PORT  --scan-directories --call $AETITLE --scan-pattern '*'  --recurse $DICOM_DIR