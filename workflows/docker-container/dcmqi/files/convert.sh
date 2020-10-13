#!/bin/bash
case "$DCMQI_COMMAND" in
    'itkimage2segimage')
        echo "COMMAND: $DCMQI_COMMAND"
        python3 -u itkimage2segimage.py
    ;;
    'segimage2itkimage')
        echo "COMMAND: $DCMQI_COMMAND"
        python3 -u segimage2itkimage.py
    ;;
    'tid1500writer')
        echo "COMMAND: $DCMQI_COMMAND"
        python3 -u tid1500writer.py
    ;;
    *)
        echo $"Usage: $0 {itkimage2segimage|segimage2itkimage|tid1500writer}"
        exit 1
esac