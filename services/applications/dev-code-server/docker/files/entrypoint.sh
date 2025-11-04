#!/bin/bash
set -e

# Check if it's an offline environment
if ! ping -c1 -W1 pypi.org >/dev/null 2>&1; then
  echo "WARNING: Offline mode detected — pip and CRAN installs will not work."
fi
