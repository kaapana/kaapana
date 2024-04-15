#!/bin/bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --workers 1 --root-path $APPLICATION_ROOT
