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

function install_cert_files {
    CERT_FILE=$1
    KEY_FILE=$2
    if ! kubectl get secret $SECRET_NAME --namespace=kube-system; then
        echo "Secret $SECRET_NAME not found in namespace kube-system -> creating new secret ..."
        if ! kubectl --insecure-skip-tls-verify=true -n kube-system create secret tls $SECRET_NAME --key $KEY_FILE --cert $CERT_FILE; then
            echo "ERROR creating secret $SECRET_NAME in namespace kube-system -> maybe already existing?"
            exit 1 
        fi
    fi

    echo "Copy secret $SECRET_NAME from namespace kube-system -> $SECRET_NAMESPACE ..."
    if ! kubectl get secret $SECRET_NAME --namespace=kube-system -oyaml | grep -v '^\s*namespace:\s' | kubectl apply --namespace=$SECRET_NAMESPACE -f -; then
        echo "ERROR copying secret $SECRET_NAME in namespace $SECRET_NAMESPACE" 
        exit 1
    fi
    echo "Secret $SECRET_NAME created in namespace $SECRET_NAMESPACE"
    

}

function install_cert {
    if kubectl -n $SECRET_NAMESPACE get secret $SECRET_NAME; then
        echo "Secret $SECRET_NAME already exist in namespace $SECRET_NAMESPACE... skipping creation"
        return
    fi

    echo "No secret found"
    if [ -e "$TLS_CERT_FILE" ] && [ -e "$TLS_KEY_FILE" ]; then
        echo "Found $TLS_CERT_FILE and $TLS_KEY_FILE, installing those."
        install_cert_files $TLS_CERT_FILE $TLS_KEY_FILE
    else
        echo "No tls certificates found, creating self-signed ones..."

        echo "Generating new self-signed certificate for $COMMON_NAME"
        openssl genrsa 4096 > tls.key
        openssl req -new -x509 -nodes -sha256 -days $EXPIRATION -key tls.key -out tls.crt -subj "/CN=$COMMON_NAME" -addext "extendedKeyUsage = serverAuth"

        install_cert_files "tls.crt" "tls.key"
    fi
}

function remove_cert {
    kubectl -n $SECRET_NAMESPACE get secret $SECRET_NAME 
    if [ $? -eq 0 ]; then
        echo "Secret $SECRET_NAME not present in namespace $SECRET_NAMESPACE... skipping deletion"
    else 
        if ! kubectl -n $SECRET_NAMESPACE delete secret $SECRET_NAME; then
            echo "ERROR could not delete secret $SECRET_NAME from namespace $SECRET_NAMESPACE."
            exit 1
        fi
        echo "Secret $SECRET_NAME deleted from namespace $SECRET_NAMESPACE."
    fi
}

case $ACTION in
install)
    install_cert
    ;;
remove)
    remove_cert
    ;;
*)
    echo "ERROR Unkown action $ACTION"
    exit 1
esac