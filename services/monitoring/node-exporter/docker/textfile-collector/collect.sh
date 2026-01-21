#!/bin/sh
set -eu
set -o pipefail 2>/dev/null || true

TEXTFILE_DIR="/textfile"
FAST_DIR="/fast"
SLOW_DIR="/slow"
SLEEP_INTERVAL="${TEXTFILE_POLL_INTERVAL:-300}"

while true; do
  fast_kb="$(du -s "$FAST_DIR" 2>/dev/null | awk '{print $1}' || echo 0)"
  fast_bytes=$((fast_kb * 1024))
  fast_kb_total="$(df -kP "$FAST_DIR" 2>/dev/null | awk 'NR==2 {print $2}' || echo 0)"
  fast_kb_available="$(df -kP "$FAST_DIR" 2>/dev/null | awk 'NR==2 {print $4}' || echo 0)"
  fast_fs_bytes=$((fast_kb_total * 1024))
  fast_bytes_available=$((fast_kb_available * 1024))

  slow_kb="$(du -s "$SLOW_DIR" 2>/dev/null | awk '{print $1}' || echo 0)"
  slow_bytes=$((slow_kb * 1024))
  slow_kb_total="$(df -kP "$SLOW_DIR" 2>/dev/null | awk 'NR==2 {print $2}' || echo 0)"
  slow_kb_available="$(df -kP "$SLOW_DIR" 2>/dev/null | awk 'NR==2 {print $4}' || echo 0)"
  slow_fs_bytes=$((slow_kb_total * 1024))
  slow_bytes_available=$((slow_kb_available * 1024))

  tmp_fast="${TEXTFILE_DIR}/kaapana_fast_size.prom.$$"
  cat > "$tmp_fast" <<EOF
# HELP kaapana_fast_dir_size_bytes Size of FAST_DATA_DIR contents in bytes
# TYPE kaapana_fast_dir_size_bytes gauge
kaapana_fast_dir_size_bytes{path="${FAST_PATH}"} ${fast_bytes}
# HELP kaapana_fast_fs_size_bytes Total filesystem capacity backing FAST_DATA_DIR
# TYPE kaapana_fast_fs_size_bytes gauge
kaapana_fast_fs_size_bytes{path="${FAST_PATH}"} ${fast_fs_bytes}
# HELP kaapana_fast_fs_available_bytes Available filesystem space for FAST_DATA_DIR
# TYPE kaapana_fast_fs_available_bytes gauge
kaapana_fast_fs_available_bytes{path="${FAST_PATH}"} ${fast_bytes_available}
EOF
  mv "$tmp_fast" "${TEXTFILE_DIR}/kaapana_fast_size.prom"

  tmp_slow="${TEXTFILE_DIR}/kaapana_slow_size.prom.$$"
  cat > "$tmp_slow" <<EOF
# HELP kaapana_slow_dir_size_bytes Size of SLOW_DATA_DIR contents in bytes
# TYPE kaapana_slow_dir_size_bytes gauge
kaapana_slow_dir_size_bytes{path="${SLOW_PATH}"} ${slow_bytes}
# HELP kaapana_slow_fs_size_bytes Total filesystem capacity backing SLOW_DATA_DIR
# TYPE kaapana_slow_fs_size_bytes gauge
kaapana_slow_fs_size_bytes{path="${SLOW_PATH}"} ${slow_fs_bytes}
# HELP kaapana_slow_fs_available_bytes Available filesystem space for SLOW_DATA_DIR
# TYPE kaapana_slow_fs_available_bytes gauge
kaapana_slow_fs_available_bytes{path="${SLOW_PATH}"} ${slow_bytes_available}
EOF
  mv "$tmp_slow" "${TEXTFILE_DIR}/kaapana_slow_size.prom"

  sleep "$SLEEP_INTERVAL"
done
