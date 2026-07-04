#!/usr/bin/env bash

set -euo pipefail

FAST_DATA_DIR="${FAST_DATA_DIR:-/home/kaapana/fast}"
KUBECTL_BIN="${KUBECTL_BIN:-microk8s.kubectl}"
ADMIN_NAMESPACE="${ADMIN_NAMESPACE:-admin}"
SERVICES_NAMESPACE="${SERVICES_NAMESPACE:-services}"
ASSUME_YES="false"
ANALYZE_ONLY="false"
FAIL_ON_ISSUES="false"
EXPECTED_HOSTNAME="${EXPECTED_HOSTNAME:-$(hostname -f 2>/dev/null || hostname 2>/dev/null || true)}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--fast-dir DIR] [--kubectl BIN] [--admin-namespace NS] [--services-namespace NS] [--hostname HOST] [--analyze-only] [--fail-on-issues] [--yes]

Delete Kaapana's persisted certificate state by:
  - deleting secret/certificate in the admin namespace
  - deleting secret/certificate in the services namespace
  - removing the persisted TLS directory from FAST_DATA_DIR
  - removing the persisted OpenSearch cert directory from FAST_DATA_DIR

Defaults:
  --fast-dir            ${FAST_DATA_DIR}
  --kubectl             ${KUBECTL_BIN}
  --admin-namespace     ${ADMIN_NAMESPACE}
  --services-namespace  ${SERVICES_NAMESPACE}
  --hostname            ${EXPECTED_HOSTNAME}
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fast-dir)
            FAST_DATA_DIR="$2"
            shift 2
            ;;
        --kubectl)
            KUBECTL_BIN="$2"
            shift 2
            ;;
        --admin-namespace)
            ADMIN_NAMESPACE="$2"
            shift 2
            ;;
        --services-namespace)
            SERVICES_NAMESPACE="$2"
            shift 2
            ;;
        --hostname)
            EXPECTED_HOSTNAME="$2"
            shift 2
            ;;
        --analyze-only)
            ANALYZE_ONLY="true"
            shift
            ;;
        --fail-on-issues)
            FAIL_ON_ISSUES="true"
            shift
            ;;
        --yes)
            ASSUME_YES="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if ! command -v "$KUBECTL_BIN" >/dev/null 2>&1; then
    echo "ERROR: kubectl binary not found: $KUBECTL_BIN" >&2
    exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
    echo "ERROR: openssl not found" >&2
    exit 1
fi

collect_existing_dirs() {
    local pattern
    for pattern in "$@"; do
        # Expand patterns here so the script works with the Longhorn-style PVC
        # directories as well as the older direct FAST_DATA_DIR layouts.
        for candidate in $pattern; do
            if [[ -d "$candidate" ]]; then
                printf '%s\n' "$candidate"
            fi
        done
    done
}

collect_existing_files() {
    local pattern
    for pattern in "$@"; do
        for candidate in $pattern; do
            if [[ -f "$candidate" ]]; then
                printf '%s\n' "$candidate"
            fi
        done
    done
}

hostname_matches_certificate() {
    local cert_file="$1"
    local hostname="$2"
    local output

    if [[ -z "$hostname" ]]; then
        return 2
    fi

    # `openssl x509 -checkhost` prints a useful match/mismatch message, but on
    # some OpenSSL builds it still exits with status 0 even for mismatches.
    # Parse the explicit result text instead of trusting the exit code here.
    if [[ "$hostname" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        output="$(openssl x509 -in "$cert_file" -noout -checkip "$hostname" 2>&1 || true)"
    else
        output="$(openssl x509 -in "$cert_file" -noout -checkhost "$hostname" 2>&1 || true)"
    fi

    [[ "$output" == *"does match certificate"* ]]
}

print_certificate_analysis() {
    local label="$1"
    local cert_file="$2"
    local issues=()
    local start_raw end_raw start_epoch end_epoch now_epoch

    echo "  ${label}:"
    echo "    source: ${cert_file}"
    echo "    subject: $(openssl x509 -in "$cert_file" -noout -subject | sed 's/^subject=//')"
    echo "    issuer:  $(openssl x509 -in "$cert_file" -noout -issuer | sed 's/^issuer=//')"
    echo "    sha256:  $(openssl x509 -in "$cert_file" -noout -fingerprint -sha256 | sed 's/^sha256 Fingerprint=//')"

    local san_block
    san_block="$(openssl x509 -in "$cert_file" -noout -ext subjectAltName 2>/dev/null | sed '1d' | sed 's/^/      /')"
    if [[ -n "$san_block" ]]; then
        echo "    SANs:"
        echo "$san_block"
    else
        echo "    SANs:   none"
        issues+=("no SAN extension")
    fi

    start_raw="$(openssl x509 -in "$cert_file" -noout -startdate | cut -d= -f2-)"
    end_raw="$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2-)"
    echo "    validity:"
    echo "      notBefore: ${start_raw}"
    echo "      notAfter:  ${end_raw}"

    # Convert the OpenSSL timestamps to epoch seconds so the script can flag
    # certificates that are expired or not yet valid without depending on
    # external tooling beyond the base system date command.
    now_epoch="$(date +%s)"
    start_epoch="$(date -d "$start_raw" +%s 2>/dev/null || echo "")"
    end_epoch="$(date -d "$end_raw" +%s 2>/dev/null || echo "")"
    if [[ -n "$start_epoch" && "$now_epoch" -lt "$start_epoch" ]]; then
        issues+=("certificate not yet valid")
    fi
    if [[ -n "$end_epoch" && "$now_epoch" -gt "$end_epoch" ]]; then
        issues+=("certificate expired")
    fi

    if [[ -n "$EXPECTED_HOSTNAME" ]]; then
        if hostname_matches_certificate "$cert_file" "$EXPECTED_HOSTNAME"; then
            echo "    hostname: matches expected host ${EXPECTED_HOSTNAME}"
        else
            echo "    hostname: does NOT match expected host ${EXPECTED_HOSTNAME}"
            issues+=("hostname mismatch")
        fi
    else
        echo "    hostname: skipped (no expected hostname configured)"
    fi

    if [[ ${#issues[@]} -eq 0 ]]; then
        echo "    issues:   none detected"
        return 0
    else
        printf '    issues:   %s\n' "$(IFS=', '; echo "${issues[*]}")"
        return 1
    fi
}

extract_secret_certificate() {
    local namespace="$1"
    local tmp_file="$2"
    local cert_data

    cert_data="$("$KUBECTL_BIN" get secret certificate -n "$namespace" -o jsonpath='{.data.tls\.crt}' 2>/dev/null || true)"
    if [[ -z "$cert_data" ]]; then
        return 1
    fi

    # The script keeps secret inspection read-only by decoding the certificate
    # into a temporary file instead of modifying any cluster state.
    printf '%s' "$cert_data" | base64 -d > "$tmp_file"
}

mapfile -t TARGET_DIRS < <(
    collect_existing_dirs \
        "${FAST_DATA_DIR}/admin-tls-pv-claim-pvc-*" \
        "${FAST_DATA_DIR}/services-os-certs-pv-claim-pvc-*" \
        "${FAST_DATA_DIR}/tls" \
        "${FAST_DATA_DIR}/os/certs" | sort -u
)

mapfile -t TLS_CERT_FILES < <(
    collect_existing_files \
        "${FAST_DATA_DIR}/admin-tls-pv-claim-pvc-*/tls.crt" \
        "${FAST_DATA_DIR}/tls/tls.crt" | sort -u
)

echo "Existing certificate analysis"
echo "  Expected hostname: ${EXPECTED_HOSTNAME:-<none>}"
ANALYSIS_ISSUES_FOUND="false"
if [[ ${#TLS_CERT_FILES[@]} -eq 0 ]]; then
    echo "  Persisted TLS files: none found"
else
    for cert_file in "${TLS_CERT_FILES[@]}"; do
        if ! print_certificate_analysis "Persisted TLS file" "$cert_file"; then
            ANALYSIS_ISSUES_FOUND="true"
        fi
    done
fi

for namespace in "$ADMIN_NAMESPACE" "$SERVICES_NAMESPACE"; do
    secret_tmp_file="$(mktemp)"
    # Use a temp file for secret analysis so the logic stays read-only.
    if extract_secret_certificate "$namespace" "$secret_tmp_file"; then
        if ! print_certificate_analysis "Secret ${namespace}/certificate" "$secret_tmp_file"; then
            ANALYSIS_ISSUES_FOUND="true"
        fi
    else
        echo "  Secret ${namespace}/certificate: not found"
    fi
    rm -f "$secret_tmp_file"
done

if [[ "$FAIL_ON_ISSUES" == "true" && "$ANALYSIS_ISSUES_FOUND" == "true" ]]; then
    # Exit code 2 is reserved for "analysis found cert issues" so deploy
    # preflights can distinguish that case from generic execution failures.
    echo "Certificate analysis detected issues."
    exit 2
fi

if [[ "$ANALYZE_ONLY" == "true" ]]; then
    echo "Analyze-only mode requested; no secrets or directories were deleted."
    exit 0
fi

echo "Certificate reset targets"
echo "  Secrets:"
echo "    - ${ADMIN_NAMESPACE}/certificate"
echo "    - ${SERVICES_NAMESPACE}/certificate"
echo "  Directories:"
if [[ ${#TARGET_DIRS[@]} -eq 0 ]]; then
    echo "    - none found under ${FAST_DATA_DIR}"
else
    printf '    - %s\n' "${TARGET_DIRS[@]}"
fi

if [[ "$ASSUME_YES" != "true" ]]; then
    read -r -p "Delete the certificate secrets and directories listed above? [y/N] " reply
    case "$reply" in
        y|Y|yes|YES)
            ;;
        *)
            echo "Aborted."
            exit 1
            ;;
    esac
fi

echo "Deleting certificate secrets..."
"$KUBECTL_BIN" delete secret certificate -n "$ADMIN_NAMESPACE" --ignore-not-found
"$KUBECTL_BIN" delete secret certificate -n "$SERVICES_NAMESPACE" --ignore-not-found

if [[ ${#TARGET_DIRS[@]} -gt 0 ]]; then
    echo "Removing persisted certificate directories..."
    for dir in "${TARGET_DIRS[@]}"; do
        # Remove the whole directory so the next deployment recreates the
        # certificate state from scratch instead of reusing stale files from
        # the TLS PV or the derived OpenSearch cert/trust PV.
        rm -rf -- "$dir"
        echo "  removed $dir"
    done
fi

echo "Certificate state reset complete."
