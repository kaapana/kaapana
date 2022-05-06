#!/bin/sh
echo "Running at $APPLICATION_ROOT"
uvicorn app.main:app --reload --host 0.0.0.0 --port 5000 --workers 4 --root-path $APPLICATION_ROOT