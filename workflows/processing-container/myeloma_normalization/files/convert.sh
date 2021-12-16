#!/bin/bash
case "$NORM_TYPE" in
    'z_score')
        echo "COMMAND: $DCMQI_COMMAND"
        python3 -u norm_z_score.py
    ;;
    'tissue_based')
        echo "COMMAND: $DCMQI_COMMAND"
        python3 -u norm_tissue_based.py
    ;;
    *)
        echo $"Usage: $0 {z_score|tissue_based}"
        exit 1
esac