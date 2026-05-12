#!/bin/bash
set -euo pipefail

WORKSPACE="${WORKSPACE:-/kaapana}"
# Shared Ollama API endpoint used by Continue and CLI commands.
OLLAMA_HOST="${OLLAMA_HOST:-ollama-service.services.svc:11434}"
# Give the shared Ollama service time to become reachable before code-server
# starts sending completion requests.
OLLAMA_STARTUP_TIMEOUT="${OLLAMA_STARTUP_TIMEOUT:-30}"
# Keep models loaded briefly so the first autocomplete request after idle does
# not need to wait for a full reload while also avoiding pinned residency.
OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-10m}"
# Model to pre-load in the shared Ollama service for faster first completions.
OLLAMA_WARMUP_MODEL="${OLLAMA_WARMUP_MODEL:-qwen2.5-coder:7b}"
OLLAMA_API_BASE="http://${OLLAMA_HOST}"

# Probe the shared Ollama service and optionally warm the configured model.
# The dev-code-server must still start when Ollama is temporarily unavailable.
if command -v curl >/dev/null 2>&1; then
  ollama_ready="0"
  for _ in $(seq 1 "${OLLAMA_STARTUP_TIMEOUT}"); do
    if curl -sf --max-time 2 -o /dev/null "${OLLAMA_API_BASE}/api/tags"; then
      ollama_ready="1"
      break
    fi
    sleep 1
  done

  if [ "${ollama_ready}" != "1" ]; then
    echo "WARNING: Shared Ollama API at ${OLLAMA_API_BASE} did not become ready within ${OLLAMA_STARTUP_TIMEOUT}s."
  else
    echo "Shared Ollama API ready at ${OLLAMA_API_BASE}."

    # Pre-load the model in shared Ollama so Continue can serve inline
    # completions immediately without waiting for a cold model load.
    if [ -n "${OLLAMA_WARMUP_MODEL}" ]; then
      echo "Warming up model '${OLLAMA_WARMUP_MODEL}' ..."
      if curl -sf -o /dev/null \
           --max-time 30 \
           -H "Content-Type: application/json" \
           "${OLLAMA_API_BASE}/api/generate" \
           -d "{\"model\":\"${OLLAMA_WARMUP_MODEL}\",\"prompt\":\"hi\",\"stream\":false,\"keep_alive\":\"${OLLAMA_KEEP_ALIVE}\",\"options\":{\"num_predict\":1}}"; then
        echo "Model '${OLLAMA_WARMUP_MODEL}' loaded and warm."
      else
        echo "WARNING: Failed to warm up model '${OLLAMA_WARMUP_MODEL}'."
      fi
    fi
  fi
else
  echo "WARNING: curl is not available; skipping shared Ollama readiness check."
fi

# Workaround: The Continue extension's autocomplete provider calls
# `ide.getClipboardContent()` for context snippets, but this API hangs
# indefinitely in code-server (headless environment without desktop clipboard).
# Every autocomplete request blocks until VS Code's cancellation token aborts it,
# preventing inline completions from ever being displayed.
# Short-circuit the clipboard snippet function to return [] immediately.
# The sed is idempotent — it only matches the unpatched pattern.
find /root/.local/share/code-server/extensions/ \
  -path '*/continue.continue-*/out/extension.js' \
  -exec sed -i 's/getClipboardSnippets = async (ide) => {/getClipboardSnippets = async (ide) => { return [];/' {} \; \
  2>/dev/null || true

# Keep code-server as PID 1 for proper signal handling in containers.
# `--disable-telemetry` and `--disable-update-check` prevent outbound calls
# in offline environments and avoid noisy timeout popups in the UI.
exec code-server \
  --disable-workspace-trust \
  --disable-telemetry \
  --disable-update-check \
  --auth none \
  --bind-addr 0.0.0.0:8080 \
  "${WORKSPACE}"
