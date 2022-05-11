#!/bin/sh
echo "Running at datamodel"
uvicorn app.main:app --host 0.0.0.0 --port 5000 --workers 4 --root-path datamodel