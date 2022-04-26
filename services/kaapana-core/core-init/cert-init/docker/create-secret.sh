#!/bin/sh
kubectl -n kube-system get secret certificate 
if [ $? -eq 0 ]; then
    echo "Secret already exist... skipping creation"
    exit 0
fi

echo "Generating new self-signed certificate for $COMMON_NAME"
openssl genrsa 4096 > tls.key
openssl req -new -x509 -nodes -sha256 -days $EXPIRATION -key tls.key -out tls.crt -subj "/CN=$COMMON_NAME" -addext "extendedKeyUsage = serverAuth"

echo "Installing new self-signed certificate for $COMMON_NAME"
kubectl --insecure-skip-tls-verify=true -n kube-system create secret tls certificate --key tls.key --cert tls.crt