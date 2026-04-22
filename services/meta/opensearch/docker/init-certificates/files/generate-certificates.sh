#!/bin/sh
set -e -o pipefail

# Admin cert
openssl genrsa -out admin-key-temp.pem 2048
openssl pkcs8 -inform PEM -outform PEM -in admin-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out admin-key.pem
openssl req -new -key admin-key.pem -subj "/C=CA/ST=ONTARIO/L=TORONTO/O=ORG/OU=UNIT/CN=A" -out admin.csr
openssl x509 -req -in admin.csr -CA root-ca.pem -CAkey root-ca-key.pem -CAcreateserial -sha256 -out admin.pem -days 730

# Node cert 1
openssl genrsa -out node1-key-temp.pem 2048
openssl pkcs8 -inform PEM -outform PEM -in node1-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out node1-key.pem
openssl req -new -key node1-key.pem -subj "/C=CA/ST=ONTARIO/L=TORONTO/O=ORG/OU=UNIT/CN=node1.dns.a-record" -out node1.csr
echo 'subjectAltName=DNS:node1.dns.a-record' > node1.ext
openssl x509 -req -in node1.csr -CA root-ca.pem -CAkey root-ca-key.pem -CAcreateserial -sha256 -out node1.pem -days 730 -extfile node1.ext

# Node cert 2
openssl genrsa -out node2-key-temp.pem 2048
openssl pkcs8 -inform PEM -outform PEM -in node2-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out node2-key.pem
openssl req -new -key node2-key.pem -subj "/C=CA/ST=ONTARIO/L=TORONTO/O=ORG/OU=UNIT/CN=node2.dns.a-record" -out node2.csr
echo 'subjectAltName=DNS:node2.dns.a-record' > node2.ext
openssl x509 -req -in node2.csr -CA root-ca.pem -CAkey root-ca-key.pem -CAcreateserial -sha256 -out node2.pem -days 730 -extfile node2.ext

# Client cert
openssl genrsa -out client-key-temp.pem 2048
openssl pkcs8 -inform PEM -outform PEM -in client-key-temp.pem -topk8 -nocrypt -v1 PBE-SHA1-3DES -out client-key.pem
openssl req -new -key client-key.pem -subj "/C=CA/ST=ONTARIO/L=TORONTO/O=ORG/OU=UNIT/CN=client.dns.a-record" -out client.csr
echo 'subjectAltName=DNS:client.dns.a-record' > client.ext
openssl x509 -req -in client.csr -CA root-ca.pem -CAkey root-ca-key.pem -CAcreateserial -sha256 -out client.pem -days 730 -extfile client.ext

# -----------------------------------------------------------------------
# Build root-ca-bundle.pem from the shared platform trust anchor.
# External chain handling belongs in cert-init/cert-copy, not here.
# -----------------------------------------------------------------------
KEYSTORE_PASSWORD="keystorepassword"

if [ -f ca-bundle.pem ]; then
  cp ca-bundle.pem root-ca-bundle.pem
else
  cp root-ca.pem root-ca-bundle.pem
fi
echo "Bundle contains $(grep -c 'BEGIN CERTIFICATE' root-ca-bundle.pem) certificate(s) total."

# -----------------------------------------------------------------------
# Generate Truststore from bundle
# -----------------------------------------------------------------------
CERT_INDEX=0
CURRENT_CERT=""
while IFS= read -r line; do
  CURRENT_CERT="${CURRENT_CERT}${line}
"
  if echo "${line}" | grep -q "END CERTIFICATE"; then
    CERT_FILE="truststore-cert-${CERT_INDEX}.pem"
    printf '%s' "${CURRENT_CERT}" > "${CERT_FILE}"
    set +e
    keytool -importcert -noprompt \
      -alias "ca-${CERT_INDEX}" \
      -keystore truststore.jks \
      -file "${CERT_FILE}" \
      -storepass "${KEYSTORE_PASSWORD}" \
      -trustcacerts -deststoretype pkcs12 2>/dev/null
    IMPORT_EXIT=$?
    set -e
    [ ${IMPORT_EXIT} -eq 0 ] && echo "  Imported cert ${CERT_INDEX} into truststore" || echo "  Skipped cert ${CERT_INDEX} (duplicate or not a CA)"
    rm -f "${CERT_FILE}"
    CERT_INDEX=$((CERT_INDEX + 1))
    CURRENT_CERT=""
  fi
done < root-ca-bundle.pem

echo "Truststore contains ${CERT_INDEX} entry/entries processed."

# Copy all generated certs to /os/certs first
cp -r /certs/* /os/certs/

cp root-ca-bundle.pem /os/certs/root-ca.pem
echo "root-ca.pem in /os/certs now contains $(grep -c 'BEGIN CERTIFICATE' /os/certs/root-ca.pem) certificate(s)."

# Cleanup
rm -f admin-key-temp.pem admin.csr
rm -f node1-key-temp.pem node1.csr node1.ext
rm -f node2-key-temp.pem node2.csr node2.ext
rm -f client-key-temp.pem client.csr client.ext
rm -f root-ca-bundle.pem
