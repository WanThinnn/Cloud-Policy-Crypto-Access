#!/bin/sh
set -e

echo "============================================================"
echo "Generating Post-Quantum Certificates (mldsa87) inside Docker"
echo "============================================================"

# Create minimal openssl config
cat > pq-openssl.cnf << 'EOF'
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
    -keyout pq-CyberFortress-RootCA.key -out pq-CyberFortress-RootCA.crt -nodes \
    -subj "/C=VN/ST=Ho Chi Minh/L=Thu Duc/O=VNU/OU=UIT/CN=CyberFortress-RootCA" -days 3650

# 2. Generate Leaf Certificate (Key & CSR)
echo "\n[2/4] Generating PQC Leaf Key and CSR..."
openssl req -config pq-openssl.cnf -new -newkey mldsa87 \
    -keyout _.pq-cyberfortress.local.key -out pq-_.cyberfortress.local.csr -nodes \
    -subj "/C=VN/ST=Ho Chi Minh/L=Thu Duc/O=VNU/OU=UIT/CN=cyberfortress.local"

# 3. Create extension file
echo "\n[3/4] Creating extension config file..."
cat > pq-v3.ext << 'EOF'
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = cyberfortress.local
DNS.2 = *.cyberfortress.local
EOF

# 4. Sign the Leaf Certificate
echo "\n[4/4] Signing Leaf Certificate with Root CA..."
openssl x509 -req -in pq-_.cyberfortress.local.csr \
    -CA pq-CyberFortress-RootCA.crt -CAkey pq-CyberFortress-RootCA.key \
    -CAcreateserial -out _.pq-cyberfortress.local.crt \
    -days 365 -extfile pq-v3.ext

# Cleanup
rm -f pq-_.cyberfortress.local.csr pq-v3.ext pq-openssl.cnf pq-CyberFortress-RootCA.srl test.key test.crt

echo "\nSUCCESS! Certs generated inside Docker container."
