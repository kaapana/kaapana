FROM docker.io/alpine:3.19

LABEL IMAGE="node-exporter-textfile-collector"
LABEL VERSION="0.0.1"
LABEL BUILD_IGNORE="False"

CMD ["/bin/sh", "-c", "\
    set -euo pipefail; \
    TEXTFILE_DIR=\"/textfile\"; \
    FAST_DIR=\"/fast\"; \
    SLOW_DIR=\"/slow\"; \
    SLEEP_INTERVAL=\"${TEXTFILE_POLL_INTERVAL:-300}\"; \
    while true; do \
        fast_kb=$(du -s \"${FAST_DIR}\" 2>/dev/null | awk '{print $1}') || fast_kb=0; \
        fast_bytes=$((fast_kb * 1024)); \
        fast_kb_total=$(df -kP \"${FAST_DIR}\" 2>/dev/null | awk 'NR==2 {print $2}') || fast_kb_total=0; \
        fast_kb_available=$(df -kP \"${FAST_DIR}\" 2>/dev/null | awk 'NR==2 {print $4}') || fast_kb_available=0; \
        fast_fs_bytes=$((fast_kb_total * 1024)); \
        fast_bytes_available=$((fast_kb_available * 1024)); \
        slow_kb=$(du -s \"${SLOW_DIR}\" 2>/dev/null | awk '{print $1}') || slow_kb=0; \
        slow_bytes=$((slow_kb * 1024)); \
        slow_kb_total=$(df -kP \"${SLOW_DIR}\" 2>/dev/null | awk 'NR==2 {print $2}') || slow_kb_total=0; \
        slow_kb_available=$(df -kP \"${SLOW_DIR}\" 2>/dev/null | awk 'NR==2 {print $4}') || slow_kb_available=0; \
        slow_fs_bytes=$((slow_kb_total * 1024)); \
        slow_bytes_available=$((slow_kb_available * 1024)); \
        printf '%s\\n%s\\n%s\\n' \
          '# HELP kaapana_fast_dir_size_bytes Size of FAST_DATA_DIR contents in bytes' \
          '# TYPE kaapana_fast_dir_size_bytes gauge' \
          \"kaapana_fast_dir_size_bytes{path=\\\"\\${FAST_PATH}\\\"} \\${fast_bytes}\" \
          > \"${TEXTFILE_DIR}/kaapana_fast_size.prom\"; \
        printf '%s\\n%s\\n%s\\n' \
          '# HELP kaapana_fast_fs_size_bytes Total filesystem capacity backing FAST_DATA_DIR' \
          '# TYPE kaapana_fast_fs_size_bytes gauge' \
          \"kaapana_fast_fs_size_bytes{path=\\\"\\${FAST_PATH}\\\"} \\${fast_fs_bytes}\" \
          >> \"${TEXTFILE_DIR}/kaapana_fast_size.prom\"; \
        printf '%s\\n%s\\n%s\\n' \
          '# HELP kaapana_fast_fs_available_bytes Available filesystem space for FAST_DATA_DIR' \
          '# TYPE kaapana_fast_fs_available_bytes gauge' \
          \"kaapana_fast_fs_available_bytes{path=\\\"\\${FAST_PATH}\\\"} \\${fast_bytes_available}\" \
          >> \"${TEXTFILE_DIR}/kaapana_fast_size.prom\"; \
        printf '%s\\n%s\\n%s\\n' \
          '# HELP kaapana_slow_dir_size_bytes Size of SLOW_DATA_DIR contents in bytes' \
          '# TYPE kaapana_slow_dir_size_bytes gauge' \
          \"kaapana_slow_dir_size_bytes{path=\\\"\\${SLOW_PATH}\\\"} \\${slow_bytes}\" \
          > \"${TEXTFILE_DIR}/kaapana_slow_size.prom\"; \
        printf '%s\\n%s\\n%s\\n' \
          '# HELP kaapana_slow_fs_size_bytes Total filesystem capacity backing SLOW_DATA_DIR' \
          '# TYPE kaapana_slow_fs_size_bytes gauge' \
          \"kaapana_slow_fs_size_bytes{path=\\\"\\${SLOW_PATH}\\\"} \\${slow_fs_bytes}\" \
          >> \"${TEXTFILE_DIR}/kaapana_slow_size.prom\"; \
        printf '%s\\n%s\\n%s\\n' \
          '# HELP kaapana_slow_fs_available_bytes Available filesystem space for SLOW_DATA_DIR' \
          '# TYPE kaapana_slow_fs_available_bytes gauge' \
          \"kaapana_slow_fs_available_bytes{path=\\\"\\${SLOW_PATH}\\\"} \\${slow_bytes_available}\" \
          >> \"${TEXTFILE_DIR}/kaapana_slow_size.prom\"; \
        sleep \"${SLEEP_INTERVAL}\"; \
    done"]