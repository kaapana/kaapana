#!/bin/bash
set -euo pipefail

# Shared Ollama service (ollama-chart) that Continue talks to; set by the chart.
OLLAMA_API_BASE="${OLLAMA_API_BASE:-http://ollama-service.services.svc:11434}"
OLLAMA_STARTUP_TIMEOUT="${OLLAMA_STARTUP_TIMEOUT:-30}"
OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-10m}"
OLLAMA_WARMUP_MODEL="${OLLAMA_WARMUP_MODEL:-}"

# Load the autocomplete model before the editor opens: a cold load on the CPU-only
# service takes longer than Continue waits for a completion. code-server must start
# even when Ollama is unavailable, so every failure here is only a warning.
if [ -n "${OLLAMA_WARMUP_MODEL}" ]; then
  ollama_ready="0"
  for _ in $(seq 1 "${OLLAMA_STARTUP_TIMEOUT}"); do
    if curl -sf --max-time 2 -o /dev/null "${OLLAMA_API_BASE}/api/tags"; then
      ollama_ready="1"
      break
    fi
    sleep 1
  done

  if [ "${ollama_ready}" != "1" ]; then
    echo "WARNING: Ollama at ${OLLAMA_API_BASE} not ready within ${OLLAMA_STARTUP_TIMEOUT}s."
  elif curl -sf -o /dev/null --max-time 30 \
       -H "Content-Type: application/json" \
       "${OLLAMA_API_BASE}/api/generate" \
       -d "{\"model\":\"${OLLAMA_WARMUP_MODEL}\",\"prompt\":\"hi\",\"stream\":false,\"keep_alive\":\"${OLLAMA_KEEP_ALIVE}\",\"options\":{\"num_predict\":1}}"; then
    echo "Model '${OLLAMA_WARMUP_MODEL}' loaded."
  else
    echo "WARNING: Failed to load model '${OLLAMA_WARMUP_MODEL}' in Ollama."
  fi
fi

# exec keeps code-server as PID 1 for signal handling. Telemetry and update checks
# are off because they only produce timeouts on offline platforms.
exec code-server \
  --disable-workspace-trust \
  --disable-telemetry \
  --disable-update-check \
  --auth none \
  --bind-addr 0.0.0.0:8080 \
  "${WORKSPACE:-/kaapana}"
