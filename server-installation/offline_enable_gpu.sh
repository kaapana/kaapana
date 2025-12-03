install_gpu_operator() {
  local script_dir="$1"

  if [[ -z "${script_dir}" ]]; then
    echo "install_gpu_operator: missing required argument: script_dir" >&2
    return 1
  fi

  # Constants
  local chart_name="gpu-operator"
  local chart_version="v25.3.0"
  local helm="/snap/bin/helm"
  local containerd_socket="/var/snap/microk8s/common/run/containerd.sock"
  local containerd_toml="/var/snap/microk8s/current/args/containerd-template.toml"

  local chart_path="${script_dir%/}/gpu-operator.tgz"

  if [[ ! -f "${chart_path}" ]]; then
    echo "install_gpu_operator: chart not found at ${chart_path}" >&2
    return 1
  fi

  # Match Python: only distinguish by presence of nvidia-smi (OSError equivalent)
  local driver
  if command -v nvidia-smi >/dev/null 2>&1; then
    driver="host"
  else
    driver="operator"
  fi

  local driver_enabled
  if [[ "${driver}" == "operator" ]]; then
    driver_enabled="true"
  else
    driver_enabled="false"
  fi

  # Feed JSON values to Helm via stdin (equivalent to -f - in the Python script)
  cat <<EOF | "${helm}" install "${chart_name}" "${chart_path}" \
    --version="${chart_version}" \
    --create-namespace \
    --namespace="${chart_name}-resources" \
    -f -
{
  "operator": {
    "defaultRuntime": "containerd"
  },
  "driver": {
    "enabled": "${driver_enabled}"
  },
  "toolkit": {
    "enabled": "true",
    "env": [
      { "name": "CONTAINERD_CONFIG", "value": "${containerd_toml}" },
      { "name": "CONTAINERD_SOCKET", "value": "${containerd_socket}" },
      { "name": "CONTAINERD_SET_AS_DEFAULT", "value": "1" }
    ]
  }
}
EOF
}
