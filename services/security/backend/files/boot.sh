#!/bin/bash

# Production
echo "Running at $APPLICATION_ROOT"
uvicorn main:app --app-dir ./app --proxy-headers --host 0.0.0.0 --port 5000
