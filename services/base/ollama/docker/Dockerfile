FROM ollama/ollama:0.6.8

LABEL IMAGE="ollama"
LABEL VERSION="0.0.0"
LABEL BUILD_IGNORE="False"

# Build-time model preload for fully offline runtime operation.
# Space-separated list allows future extension while keeping a fast default.
ARG OLLAMA_PRELOAD_MODELS="qwen2.5-coder:7b"

RUN set -eux; \
    export OLLAMA_HOST="127.0.0.1:11434"; \
    ollama serve >/tmp/ollama-build.log 2>&1 & \
    ollama_pid="$!"; \
    ready="0"; \
    attempts=0; \
    while [ "$attempts" -lt 60 ]; do \
      if ollama list >/dev/null 2>&1; then ready="1"; break; fi; \
      sleep 1; \
      attempts=$((attempts + 1)); \
    done; \
    if [ "${ready}" != "1" ]; then \
      echo "Ollama failed to start during image build." >&2; \
      cat /tmp/ollama-build.log >&2 || true; \
      kill "${ollama_pid}" >/dev/null 2>&1 || true; \
      exit 1; \
    fi; \
    for model in ${OLLAMA_PRELOAD_MODELS}; do \
      [ -z "${model}" ] && continue; \
      ollama pull "${model}"; \
    done; \
    kill "${ollama_pid}" >/dev/null 2>&1 || true; \
    wait "${ollama_pid}" 2>/dev/null || true
