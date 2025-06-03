#!/bin/bash
set -aeuf -o pipefail

export REPO_DIR="" ### Path to the kaapana repository
export ARTIFACTS_DIR="" ### Path to the directory, where log files are saved
export ip_address="" ### ip_address of the instance, where kaapana is deployed
export http_proxy=""
export https_proxy=""

ansible-playbook -vvv "${REPO_DIR}/ci/ci-code/test/ui_tests/first_login.yaml"
ansible-playbook "${REPO_DIR}/ci/ci-code/test/testdata/prepare_data.yaml"
ansible-playbook -vvv "${REPO_DIR}/ci/ci-code/test/extensions/install_extensions.yaml"
ansible-playbook "${REPO_DIR}/ci/ci-code/test/integration_tests/integration_tests.yaml"