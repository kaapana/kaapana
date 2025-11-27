#!/bin/bash
# Local runner for workflow_api_tests CI job
# Usage: ./run_workflow_api_tests.sh

set -e  # Exit on error

# Simulate CI variables
export UNIT_DIR=$(pwd)

echo "==> Creating virtual environment..."
python3 -m venv $UNIT_DIR/.venv

echo "==> Activating virtual environment..."
source $UNIT_DIR/.venv/bin/activate

echo "==> Installing pytest..."
python3 -m pip install pytest

echo "==> Installing test requirements..."
pip install -r $UNIT_DIR/requirements.txt

echo "==> Running tests..."
pytest $UNIT_DIR --junitxml=workflow_api_report.xml

echo "==> Tests completed!"
echo "Report saved to: workflow_api_report.xml"
