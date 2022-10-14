#!/bin/bash
# run server via ../../boot.sh first
echo "Running test_server.py"
python -m pytest -s tests/test_server.py
echo "Running test_install_delete.py"
python -m pytest -s tests/test_install_delete.py