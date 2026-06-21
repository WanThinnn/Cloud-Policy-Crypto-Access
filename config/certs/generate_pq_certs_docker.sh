#!/bin/sh
set -e

DOMAIN_NAME=${DOMAIN_NAME:-cyberfortress.local}
COMPANY_NAME=${COMPANY_NAME:-CyberFortress}
ROOT_CA_NAME="pq-${COMPANY_NAME}-RootCA"

echo "============================================================"
echo "Generating PQC (mldsa87) for Domain: $DOMAIN_NAME"
echo "Company Name: $COMPANY_NAME"
echo "============================================================"

# Create minimal openssl config
cat > pq-openssl.cnf << EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_ca
prompt = no
[req_distinguished_name]
C = VN
[v3_ca]
basicConstraints = critical,CA:true
EOF

# 1. Generate Root CA
echo "\n[1/4] Generating PQC Root CA..."
openssl req -config pq-openssl.cnf -x509 -new -newkey mldsa87 \
    -keyout "${ROOT_CA_NAME}.key" -out "${ROOT_CA_NAME}.crt" -nodes \
    -subj "/C=VN/ST=Ho Chi Minh/L=Thu Duc/O=VNU/OU=UIT/CN=${COMPANY_NAME}-RootCA" -days 3650

# 2. Generate Leaf Certificate (Key & CSR)
echo "\n[2/4] Generating PQC Leaf Key and CSR..."
openssl req -config pq-openssl.cnf -new -newkey mldsa87 \
    -keyout "_.pq-${DOMAIN_NAME}.key" -out "_.pq-${DOMAIN_NAME}.csr" -nodes \
    -subj "/C=VN/ST=Ho Chi Minh/L=Thu Duc/O=VNU/OU=UIT/CN=${DOMAIN_NAME}"

# 3. Create extension file
echo "\n[3/4] Creating extension config file..."
cat > pq-v3.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${DOMAIN_NAME}
DNS.2 = *.${DOMAIN_NAME}
EOF

# 4. Sign the Leaf Certificate
echo "\n[4/4] Signing Leaf Certificate with Root CA..."
openssl x509 -req -in "_.pq-${DOMAIN_NAME}.csr" \
    -CA "${ROOT_CA_NAME}.crt" -CAkey "${ROOT_CA_NAME}.key" \
    -CAcreateserial -out "_.pq-${DOMAIN_NAME}.crt" \
    -days 365 -extfile pq-v3.ext

# Cleanup
rm -f "_.pq-${DOMAIN_NAME}.csr" pq-v3.ext pq-openssl.cnf "${ROOT_CA_NAME}.srl" test.key test.crt

echo "\nSUCCESS! Certs generated inside Docker container."
