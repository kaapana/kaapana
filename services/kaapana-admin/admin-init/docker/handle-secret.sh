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
    if ! kubectl get secret $SECRET_NAME --namespace=$ADMIN_NAMESPACE; then
        echo "Secret $SECRET_NAME not found in namespace $ADMIN_NAMESPACE -> creating new secret ..."
        if ! kubectl --insecure-skip-tls-verify=true -n $ADMIN_NAMESPACE create secret tls $SECRET_NAME --key $KEY_FILE --cert $CERT_FILE; then
            echo "ERROR creating secret $SECRET_NAME in namespace $ADMIN_NAMESPACE -> maybe already existing?"
        fi
    else
        echo "Secret $SECRET_NAME already found in namespace $ADMIN_NAMESPACE"
    fi    
}

function copy_cert {
    if [ "$SECRET_NAMESPACE" == "$ADMIN_NAMESPACE" ]; then
        echo "SERVICES_NAMESPACE == ADMIN_NAMESPACE -> skip copy of secret."
    else
        if kubectl get namespace $SECRET_NAMESPACE; then
            max_retry=10
            counter=0
            until kubectl get secret --namespace=$ADMIN_NAMESPACE $SECRET_NAME;
                do
                    [[ counter -eq $max_retry ]] && echo "Failed!" && exit 1
                    ((counter++))
                    echo "Cert secret not found at $ADMIN_NAMESPACE -> waiting #$counter ..."
                    sleep 5
                done

            if ! kubectl get secret --namespace=$SECRET_NAMESPACE $SECRET_NAME; then
                echo "Copy secret $SECRET_NAME from namespace $ADMIN_NAMESPACE -> $SECRET_NAMESPACE ..."
                if ! kubectl get secret $SECRET_NAME --namespace=$ADMIN_NAMESPACE -ojson | jq 'del(.metadata["namespace","creationTimestamp","resourceVersion","selfLink","uid"])' | kubectl apply --namespace=$SECRET_NAMESPACE -f -; then
                    echo "ERROR copying secret $SECRET_NAME in namespace $SECRET_NAMESPACE" 
                    exit 1
                fi
                echo "Secret $SECRET_NAME created in namespace $SECRET_NAMESPACE"
            else
                echo "Secret $SECRET_NAME already present in namespace $SECRET_NAMESPACE -> skipping."
            fi
        else
            echo "SECRET_NAMESPACE: $SECRET_NAMESPACE not present -> skipping copy of secret ..."
        fi
    fi
}

function install_cert {
    if kubectl -n $SECRET_NAMESPACE get secret $SECRET_NAME; then
        echo "Secret $SECRET_NAME already exist in namespace $SECRET_NAMESPACE... skipping creation"
        return
    fi

    echo "No secret found"
    if [ -e "$TLS_CERT_FILE" ] && [ -e "$TLS_KEY_FILE" ]; then
        echo "Found $TLS_CERT_FILE and $TLS_KEY_FILE, installing those."
        if ! kubectl -n $SECRET_NAMESPACE delete secret $SECRET_NAME; then
            echo "Could not delete secret $SECRET_NAME from namespace $SECRET_NAMESPACE -> maybe not present yet."
        fi
        if ! kubectl -n $ADMIN_NAMESPACE delete secret $SECRET_NAME; then
            echo "Could not delete secret $SECRET_NAME from namespace $ADMIN_NAMESPACE -> maybe not present yet."
        fi
    else
        echo "No tls certificates found, creating self-signed ones..."

        echo "Generating new self-signed certificate for $COMMON_NAME"
        openssl genrsa 4096 > tls.key
        openssl req -new -x509 -nodes -sha256 -days $EXPIRATION -key tls.key -out tls.crt -subj "/CN=$COMMON_NAME" -addext "extendedKeyUsage = serverAuth"

        TLS_CERT_FILE="tls.crt"
        TLS_KEY_FILE="tls.key"
    fi

    install_cert_files $TLS_CERT_FILE $TLS_KEY_FILE
}

function remove_cert {
    if ! kubectl get namespace $SECRET_NAMESPACE; then
        echo "Namespace $SECRET_NAMESPACE does not exist... skipping deletion"
        return
    fi

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
