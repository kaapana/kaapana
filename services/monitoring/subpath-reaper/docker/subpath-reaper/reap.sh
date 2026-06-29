#!/usr/bin/env bash
# subpath-reaper — releases orphaned kubelet subPath bind-mounts that long-lived
# containers with HostToContainer/Bidirectional host mounts pin in their own mount
# namespace (observed: nvidia-container-toolkit's /host, node-exporter's /host/root).
#
# When such a container receives a kubelet subPath bind-mount via propagation, the
# kubelet's later unmount/rmdir of the source fails with "device or resource busy".
# The pod becomes orphaned and the kubelet retries cleanup every ~2s forever,
# degrading kubelite until the scheduler stops binding pods (pods stuck Pending).
#
# This runs as a privileged, hostPID DaemonSet pod. It performs the unmount in the
# HOST mount namespace via `nsenter -t 1 -m`, so it frees the host-namespace reference
# and lets the kubelet finish cleanup — regardless of which container did the pinning.
#
# Safe by construction:
#   - only pod dirs whose UID is NOT an active pod in the API are touched,
#   - only pod dirs older than GRACE_MIN (never races a just-started pod),
#   - if the API is unreachable it does NOTHING that iteration (never unmounts blind).

set -uo pipefail

INTERVAL="${INTERVAL:-60}"                 # seconds between sweeps
GRACE_MIN="${GRACE_MIN:-2}"                # ignore pod dirs younger than this (minutes)
KUBELET_PODS="${KUBELET_PODS:-/kubelet-pods}"   # in-pod hostPath mount used to LIST pod dirs
# Real host path of the same dir — used to match findmnt/umount TARGETs in the host ns.
HOST_KUBELET_PODS="${HOST_KUBELET_PODS:-/var/snap/microk8s/common/var/lib/kubelet/pods}"

API="https://kubernetes.default.svc"
SA="/var/run/secrets/kubernetes.io/serviceaccount"
TOKEN_FILE="$SA/token"
CA="$SA/ca.crt"

log(){ echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"; }

host_findmnt(){ nsenter -t 1 -m -- findmnt -rno TARGET 2>/dev/null; }
host_umount(){ nsenter -t 1 -m -- umount -l "$1" 2>/dev/null; }

reap_once(){
  local token uids mounts cleaned=0 orphans=0

  token="$(cat "$TOKEN_FILE" 2>/dev/null)" || { log "no SA token — skipping (safe)"; return 0; }
  uids="$(curl -fsS --max-time 15 --cacert "$CA" -H "Authorization: Bearer $token" \
            "$API/api/v1/pods?limit=100000" 2>/dev/null \
            | jq -r '.items[].metadata.uid' 2>/dev/null)"
  if [ -z "$uids" ]; then
    log "could not list active pods (API unreachable?) — skipping sweep to stay safe"
    return 0
  fi

  mounts="$(host_findmnt)"
  [ -n "$mounts" ] || { log "no mounts visible in host ns — skipping"; return 0; }

  local poddir uid host_sp mp
  for poddir in "$KUBELET_PODS"/*/; do
    [ -d "$poddir" ] || continue
    uid="$(basename "$poddir")"

    # Skip active pods (includes Terminating ones still in the API).
    grep -qxF "$uid" <<<"$uids" && continue
    # Skip very new dirs to avoid racing a pod created since the API snapshot.
    [ -n "$(find "$poddir" -maxdepth 0 -mmin +"$GRACE_MIN" 2>/dev/null)" ] || continue
    [ -d "${poddir}volume-subpaths" ] || continue

    orphans=$((orphans+1))
    host_sp="${HOST_KUBELET_PODS}/${uid}/volume-subpaths"
    # Lazy-unmount every host-ns mountpoint under this orphaned pod's subpaths, deepest first.
    while IFS= read -r mp; do
      [ -n "$mp" ] || continue
      if host_umount "$mp"; then
        log "lazy-unmounted orphaned subpath: $mp"
        cleaned=$((cleaned+1))
      fi
    done < <(printf '%s\n' "$mounts" | grep -F "$host_sp" | sort -r)
  done

  [ "$cleaned" -gt 0 ] && log "released $cleaned orphaned subpath mount(s) across $orphans orphaned pod(s)"
  return 0
}

log "subpath-reaper starting (interval=${INTERVAL}s grace=${GRACE_MIN}m list=${KUBELET_PODS} host=${HOST_KUBELET_PODS})"
while true; do
  reap_once
  sleep "$INTERVAL"
done
