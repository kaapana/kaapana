#!/bin/bash
set -euf -o pipefail
export HELM_EXPERIMENTAL_OCI=1
# if unusual home dir of user: sudo dpkg-reconfigure apparmor

PROJECT_NAME="starter-platform-chart" # name of the platform Helm chart
DEFAULT_VERSION="0.1.0-vdev"    # version of the platform Helm chart

