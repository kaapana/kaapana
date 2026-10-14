#!/bin/bash
# Fails unless LOCAL_PATH lies on one of the filesystem types listed in
# REQUIRED_HOST_FS_TYPE (comma-separated, e.g. "cifs") and answers in time.
# minio-sync runs it before its first write and as liveness probe, so a sync
# never writes into the local directory underneath an unmounted host share.
# An empty REQUIRED_HOST_FS_TYPE disables the check.
set -u

IFS=',' read -ra required_types <<< "${REQUIRED_HOST_FS_TYPE:-}"
allowed=()
for fs_type in "${required_types[@]}"; do
    fs_type="${fs_type//[[:space:]]/}"
    [[ -n "$fs_type" ]] && allowed+=("$fs_type")
done
# The other applications built on this image never set the variable.
[[ ${#allowed[@]} -eq 0 ]] && exit 0

path=${LOCAL_PATH:?LOCAL_PATH is required}
check_timeout=${HOST_FS_CHECK_TIMEOUT:-20}

# statfs goes to the server on network filesystems, so a stale share fails here
# (with a timeout instead of a hang) rather than on the next sync write.
if ! timeout "$check_timeout" stat -f "$path" > /dev/null 2>&1; then
    echo "ERROR: ${path} is not reachable (failed or no answer within ${check_timeout}s); the host share is unavailable."
    exit 1
fi

actual=$(timeout "$check_timeout" findmnt --noheadings --output FSTYPE --target "$path" 2>/dev/null)
for fs_type in "${allowed[@]}"; do
    [[ "$actual" == "$fs_type" ]] && exit 0
done

echo "ERROR: ${path} is on filesystem '${actual:-unknown}', not on one of '${REQUIRED_HOST_FS_TYPE}'." \
    "The host share is probably not mounted; refusing to sync into the local directory underneath it."
exit 1
