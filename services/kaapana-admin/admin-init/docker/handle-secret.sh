#!/bin/bash

# Parameters
#ACTION=$ACTION # install | remove
#SECRET_NAME=$SECRET_NAME
#SECRET_NAMESPACE=$SECRET_NAMESPACE
#COMMON_NAME=$COMMON_NAME
#EXPIRATION=$EXPIRATION

set -u

TLS_CERT_FILE="/cert/tls/tls.crt"
TLS_KEY_FILE="/cert/tls/tls.key"
CA_BUNDLE_SECRET_NAME="${CA_BUNDLE_SECRET_NAME:-ca-bundle}"
CA_BUNDLE_KEY="${CA_BUNDLE_KEY:-ca-bundle.pem}"
CA_BUNDLE_FILE="/tmp/${CA_BUNDLE_KEY}"
SYSTEM_CA_BUNDLE_CANDIDATES=(
    "/etc/ssl/certs/ca-certificates.crt"
    "/etc/ssl/cert.pem"
    "/etc/pki/tls/certs/ca-bundle.crt"
    "/etc/ssl/certs/ca-bundle.crt"
)

function apply_secret_from_stdin {
    TARGET_NAMESPACE=$1
    kubectl apply -n "$TARGET_NAMESPACE" -f - >/dev/null 2>&1
}

function replace_or_create_secret_from_stdin {
    TARGET_NAMESPACE=$1

    SECRET_MANIFEST=$(cat)
    if ! echo "$SECRET_MANIFEST" | kubectl replace -n "$TARGET_NAMESPACE" -f - >/dev/null 2>&1; then
        echo "$SECRET_MANIFEST" | kubectl create -n "$TARGET_NAMESPACE" -f - >/dev/null 2>&1
    fi
}

function install_or_update_tls_secret {
    CERT_FILE=$1
    KEY_FILE=$2
    echo "Applying TLS secret $SECRET_NAME in namespace $ADMIN_NAMESPACE ..."
    kubectl --insecure-skip-tls-verify=true create secret tls "$SECRET_NAME" \
        --key "$KEY_FILE" \
        --cert "$CERT_FILE" \
        --dry-run=client -o yaml | apply_secret_from_stdin "$ADMIN_NAMESPACE"
}

function fetch_cert_to_file {
    SOURCE_SECRET_NAME=$1
    SOURCE_NAMESPACE=$2
    OUTPUT_FILE=$3
    kubectl get secret "$SOURCE_SECRET_NAME" -n "$SOURCE_NAMESPACE" -o jsonpath='{.data.tls\.crt}' | base64 -d > "$OUTPUT_FILE"
}

function append_system_ca_bundle {
    for candidate in "${SYSTEM_CA_BUNDLE_CANDIDATES[@]}"; do
        if [ -f "$candidate" ]; then
            echo "Appending system CA bundle from $candidate ..."
            cat "$candidate" >> "$CA_BUNDLE_FILE"
            return
        fi
    done

    echo "No system CA bundle found. Continuing without appending public roots."
}

function generate_ca_bundle {
    SOURCE_CERT_FILE=$1
    cp "$SOURCE_CERT_FILE" "$CA_BUNDLE_FILE"
    append_system_ca_bundle

    if [ -n "${HOSTNAME:-}" ] && [ -n "${HTTPS_PORT:-}" ]; then
        echo "Fetching external TLS chain from ${HOSTNAME}:${HTTPS_PORT} ..."
        set +e
        curl -sk --max-time 10 --output /dev/null \
            --write-out "%{certs}" \
            "https://${HOSTNAME}:${HTTPS_PORT}" > /tmp/external-chain-raw.pem 2>/dev/null
        CURL_EXIT=$?
        set -e

        if [ ${CURL_EXIT} -eq 0 ] && grep -q "BEGIN CERTIFICATE" /tmp/external-chain-raw.pem 2>/dev/null; then
            awk '
                /-----BEGIN CERTIFICATE-----/ { in_cert=1 }
                in_cert { print }
                /-----END CERTIFICATE-----/ { in_cert=0 }
            ' /tmp/external-chain-raw.pem > /tmp/external-chain.pem

            if grep -q "BEGIN CERTIFICATE" /tmp/external-chain.pem 2>/dev/null; then
                cat /tmp/external-chain.pem >> "$CA_BUNDLE_FILE"
            else
                echo "External TLS chain did not contain clean PEM blocks. Using internal certificate only."
            fi
        else
            echo "No external TLS chain fetched. Using internal certificate only."
        fi
        rm -f /tmp/external-chain-raw.pem /tmp/external-chain.pem
    fi

    echo "CA bundle contains $(grep -c 'BEGIN CERTIFICATE' "$CA_BUNDLE_FILE") certificate(s)."
}

function install_or_update_ca_bundle_secret {
    echo "Applying CA bundle secret $CA_BUNDLE_SECRET_NAME in namespace $ADMIN_NAMESPACE ..."
    kubectl create secret generic "$CA_BUNDLE_SECRET_NAME" \
        --from-file="${CA_BUNDLE_KEY}=${CA_BUNDLE_FILE}" \
        --dry-run=client -o yaml | apply_secret_from_stdin "$ADMIN_NAMESPACE"
}

function install_cert_files {
    CERT_FILE=$1
    KEY_FILE=$2
    install_or_update_tls_secret "$CERT_FILE" "$KEY_FILE"
}

function copy_secret_between_namespaces {
    SOURCE_SECRET_NAME=$1
    TARGET_NAMESPACE=$2

    if kubectl get secret "$SOURCE_SECRET_NAME" -n "$TARGET_NAMESPACE" >/dev/null 2>&1; then
        echo "Secret $SOURCE_SECRET_NAME already present in namespace $TARGET_NAMESPACE -> replacing."
    else
        echo "Copy secret $SOURCE_SECRET_NAME from namespace $ADMIN_NAMESPACE -> $TARGET_NAMESPACE ..."
    fi

    if ! kubectl get secret "$SOURCE_SECRET_NAME" -n "$ADMIN_NAMESPACE" -o json \
        | jq 'del(.metadata["namespace","creationTimestamp","resourceVersion","selfLink","uid"])' \
        | replace_or_create_secret_from_stdin "$TARGET_NAMESPACE"; then
        echo "ERROR copying secret $SOURCE_SECRET_NAME into namespace $TARGET_NAMESPACE"
        exit 1
    fi

    echo "Secret $SOURCE_SECRET_NAME created in namespace $TARGET_NAMESPACE"
}

function copy_cert {
    if [ "$SECRET_NAMESPACE" == "$ADMIN_NAMESPACE" ]; then
        echo "SERVICES_NAMESPACE == ADMIN_NAMESPACE -> skip copy of secret."
        return 0
    fi

    # Wait until source secret exists
    max_retry=10
    counter=0
    until kubectl get secret "$SECRET_NAME" -n "$ADMIN_NAMESPACE" >/dev/null 2>&1 && kubectl get secret "$CA_BUNDLE_SECRET_NAME" -n "$ADMIN_NAMESPACE" >/dev/null 2>&1; do
        [[ $counter -eq $max_retry ]] && echo "Failed waiting for secret in $ADMIN_NAMESPACE" && exit 1
        ((counter++))
        echo "Cert secrets not found in $ADMIN_NAMESPACE -> waiting #$counter ..."
        sleep 5
    done

    copy_secret_between_namespaces "$SECRET_NAME" "$SECRET_NAMESPACE"
    copy_secret_between_namespaces "$CA_BUNDLE_SECRET_NAME" "$SECRET_NAMESPACE"
}


function install_cert {
    CERT_SOURCE_FILE=""
    if [ -e "$TLS_CERT_FILE" ] && [ -e "$TLS_KEY_FILE" ]; then
        echo "Found $TLS_CERT_FILE and $TLS_KEY_FILE, installing those."
        CERT_SOURCE_FILE="$TLS_CERT_FILE"
    else
        if kubectl -n "$ADMIN_NAMESPACE" get secret "$SECRET_NAME" >/dev/null 2>&1; then
            echo "TLS secret $SECRET_NAME already exists in namespace $ADMIN_NAMESPACE, reusing certificate for CA bundle."
            CERT_SOURCE_FILE="/tmp/tls.crt"
            fetch_cert_to_file "$SECRET_NAME" "$ADMIN_NAMESPACE" "$CERT_SOURCE_FILE"
            generate_ca_bundle "$CERT_SOURCE_FILE"
            install_or_update_ca_bundle_secret
            return
        fi

        echo "No tls certificates found, creating self-signed ones..."

        echo "Generating new self-signed certificate for $COMMON_NAME"

        if echo "$HOSTNAME" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}$'; then
            echo "HOSTNAME ${HOSTNAME} is an IP address"
            SAN="IP:${HOSTNAME}"
        else
            HOST_IP=$(nslookup $HOSTNAME | awk '/^Address: / { print $2; exit }')

            if [ -z "$HOST_IP" ]; then
                echo "Error: Unable to resolve IP for $HOSTNAME"
                exit 1
            fi
            echo "DNS for ${HOSTNAME} -> ${HOST_IP}"

            SAN="DNS:$HOSTNAME"
        fi

        openssl genrsa 4096 > tls.key
        openssl req -new -x509 -nodes -sha256 -days $EXPIRATION -key tls.key -out tls.crt -subj "/CN=$COMMON_NAME" -addext "extendedKeyUsage = serverAuth" -addext "subjectAltName=${SAN}"
        
        TLS_CERT_FILE="tls.crt"
        TLS_KEY_FILE="tls.key"
        CERT_SOURCE_FILE="$TLS_CERT_FILE"
    fi

    install_cert_files "$TLS_CERT_FILE" "$TLS_KEY_FILE"
    generate_ca_bundle "$CERT_SOURCE_FILE"
    install_or_update_ca_bundle_secret
}

function remove_cert {
    if ! kubectl get namespace $SECRET_NAMESPACE; then
        echo "Namespace $SECRET_NAMESPACE does not exist... skipping deletion"
        return
    fi

    if kubectl -n $SECRET_NAMESPACE get secret $SECRET_NAME >/dev/null 2>&1; then
        if ! kubectl -n $SECRET_NAMESPACE delete secret $SECRET_NAME; then
            echo "ERROR could not delete secret $SECRET_NAME from namespace $SECRET_NAMESPACE."
            exit 1
        fi
        echo "Secret $SECRET_NAME deleted from namespace $SECRET_NAMESPACE."
    else
        echo "Secret $SECRET_NAME not present in namespace $SECRET_NAMESPACE... skipping deletion"
    fi

    if kubectl -n $SECRET_NAMESPACE get secret $CA_BUNDLE_SECRET_NAME >/dev/null 2>&1; then
        if ! kubectl -n $SECRET_NAMESPACE delete secret $CA_BUNDLE_SECRET_NAME; then
            echo "ERROR could not delete secret $CA_BUNDLE_SECRET_NAME from namespace $SECRET_NAMESPACE."
            exit 1
        fi
        echo "Secret $CA_BUNDLE_SECRET_NAME deleted from namespace $SECRET_NAMESPACE."
    else
        echo "Secret $CA_BUNDLE_SECRET_NAME not present in namespace $SECRET_NAMESPACE... skipping deletion"
    fi
}

case $ACTION in
install)
    install_cert
    ;;
copy)
    copy_cert
    ;;
remove)
    remove_cert
    ;;
*)
    echo "ERROR Unkown action $ACTION"
    exit 1
esac
