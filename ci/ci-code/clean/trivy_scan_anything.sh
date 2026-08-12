#!/usr/bin/env bash
set -Eeuo pipefail

# Trivy-scan any snap package (without installing it) or any file/directory.
#
# Why: `trivy fs` cannot analyze Go binaries inside snaps (returns 0 findings),
# but packing them into a scratch docker image and running `trivy image` works.
# This script generalizes that pack-and-scan trick.
#
# stdout carries only trivy's own output (table or JSON) — every status echo
# below is sent to stderr instead, since OfflinePackagesScanner (build_cli)
# captures stdout and parses it as JSON when --format json is used.

SEVERITY="${SEVERITY:-CRITICAL,HIGH}"
FORMAT="${FORMAT:-table}"
# Pinned (not :latest) so scan results stay comparable run-to-run — matches
# the pinned trivy binary (TRIVY_VERSION in ci/images/ci-base/Dockerfile).
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.70.0}"

usage() {
  cat <<'EOF'
Usage:
  trivy-scan-anything.sh [options] snap <name> [channel]      scan a snap package (downloaded, not installed)
  trivy-scan-anything.sh [options] path <file-or-directory>   scan any local file or directory

Options:
  -s, --severity LIST   trivy severity filter, comma-separated
                        (UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL — default: CRITICAL,HIGH)
  -f, --format FMT      output format: table | json  (default: table)
  -h, --help            show this help

Examples:
  trivy-scan-anything.sh snap microk8s 1.33/stable
  trivy-scan-anything.sh -s CRITICAL snap helm
  trivy-scan-anything.sh --severity CRITICAL --format json path /usr/local/bin/ctr

Env-var equivalents: SEVERITY, FORMAT, TRIVY_IMAGE (flags win). Channel default: latest/stable.
EOF
}

ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    -s|--severity) SEVERITY="${2:?missing value for $1}"; shift 2 ;;
    -f|--format)   FORMAT="${2:?missing value for $1}"; shift 2 ;;
    -h|--help)     usage; exit 0 ;;
    -*)            echo "ERROR: unknown option $1" >&2; usage >&2; exit 1 ;;
    *)             ARGS+=("$1"); shift ;;
  esac
done
MODE="${ARGS[0]:-}"
TARGET="${ARGS[1]:-}"
CHANNEL="${ARGS[2]:-latest/stable}"
IMG="trivy-scan-tmp:$$"

[ -z "$MODE" ] || [ -z "$TARGET" ] && { usage >&2; exit 1; }
command -v docker >/dev/null || { echo "ERROR: docker required" >&2; exit 1; }

W=$(mktemp -d)
cleanup() {
  [ -n "${W:-}" ] && [ -d "$W" ] && rm -rf "$W"
  docker rmi -f "$IMG" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
mkdir -p "$W/rootfs"

case "$MODE" in
  snap)
    command -v snap >/dev/null || { echo "ERROR: snap CLI required" >&2; exit 1; }
    command -v unsquashfs >/dev/null || { echo "ERROR: unsquashfs required (apt install squashfs-tools)" >&2; exit 1; }
    # channel = <track>/<risk>[/<branch>], risk must be stable|candidate|beta|edge
    if [[ "$CHANNEL" == */* ]] && ! [[ "$CHANNEL" =~ ^[^/]+/(stable|candidate|beta|edge)(/.+)?$ ]]; then
      echo "ERROR: invalid channel '$CHANNEL' — format: <track>/<risk>, risk = stable|candidate|beta|edge (e.g. 1.33/stable, latest/stable)" >&2
      exit 1
    fi
    echo "# downloading snap '$TARGET' channel '$CHANNEL' (not installing)..." >&2
    (cd "$W" && snap download "$TARGET" --channel="$CHANNEL" --basename=pkg >/dev/null) || {
      echo "ERROR: snap download failed — check the snap name ('$TARGET' — typo?) and channel ('$CHANNEL'); list channels with: snap info $TARGET" >&2
      exit 1
    }
    # -no-xattrs + tolerate errors: rootless unsquashfs cannot create device nodes
    # (e.g. in base snaps like core20) — irrelevant for scanning; verify extraction instead
    unsquashfs -q -n -f -no-xattrs -d "$W/rootfs" "$W/pkg.snap" >/dev/null 2>&1 || true
    [ -n "$(ls -A "$W/rootfs" 2>/dev/null)" ] || { echo "ERROR: snap extraction produced no files" >&2; exit 1; }
    # some snaps ship mode-000 dirs (e.g. core20 var/lib/snapd/void) that break the docker build context
    chmod -R u+rwX "$W/rootfs"
    LABEL="snap=$TARGET channel=$CHANNEL ($(stat -c%s "$W/pkg.snap") bytes)"
    ;;
  path)
    [ -e "$TARGET" ] || { echo "ERROR: $TARGET does not exist" >&2; exit 1; }
    cp -a "$TARGET" "$W/rootfs/"
    LABEL="path=$TARGET"
    ;;
  *) echo "ERROR: unknown mode '$MODE'" >&2; usage >&2; exit 1 ;;
esac

# Pack at image root so trivy's OS-package detection (os-release, dpkg/apk DBs)
# works in addition to per-file analyzers (gobinary, jars, ...).
printf 'FROM scratch\nCOPY rootfs/ /\n' > "$W/Dockerfile"
docker build -q -t "$IMG" "$W" >/dev/null

echo "# scanned: $LABEL  date: $(date -u +%Y-%m-%dT%H:%M:%SZ)  severity: $SEVERITY" >&2
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  "$TRIVY_IMAGE" image --scanners vuln --severity "$SEVERITY" -f "$FORMAT" "$IMG"
