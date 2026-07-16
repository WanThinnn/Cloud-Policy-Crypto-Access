#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./gen-client.sh <client_name>"
    exit 1
fi

CLIENT_NAME=$1
PKI_DIR="/etc/openvpn/pki"
OVPN_FILE="/tmp/${CLIENT_NAME}.ovpn"

COUNTRY=${COUNTRY:-"VN"}
STATE=${STATE:-"Ho Chi Minh"}
LOCALITY=${LOCALITY:-"Thu Duc"}
COMPANY_NAME=${COMPANY_NAME:-"CyberFortress"}
ORG_UNIT=${ORG_UNIT:-"UIT"}

echo "Generating PQC Native Certificate for $CLIENT_NAME..."
# 1. Tạo Client Certificate (ML-DSA-87)
cd $PKI_DIR
openssl req -new -newkey mldsa87 \
    -keyout private/${CLIENT_NAME}.key \
    -out ${CLIENT_NAME}.csr \
    -nodes \
    -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCALITY}/O=${COMPANY_NAME}/OU=${ORG_UNIT}/CN=${CLIENT_NAME}"

echo -e "extendedKeyUsage=clientAuth\nkeyUsage=digitalSignature" > ${CLIENT_NAME}_ext.cnf
openssl x509 -req -in ${CLIENT_NAME}.csr \
    -CA ca.crt -CAkey private/ca.key -CAcreateserial \
    -out issued/${CLIENT_NAME}.crt -days 3650 -extfile ${CLIENT_NAME}_ext.cnf

# 2. Tạo TLS-Crypt-V2 Client Key
openvpn --tls-crypt-v2 /etc/openvpn/tls-crypt-v2-server.key \
    --genkey tls-crypt-v2-client private/${CLIENT_NAME}.tls

# 3. Determine proto and remote lines based on VPN_PROTO
VPN_PROTO=${VPN_PROTO:-"ipv4"}

if [ "$VPN_PROTO" = "ipv6" ]; then
    PROTO_LINE="proto tcp"
    REMOTE_LINES="remote ${VPN_PUBLIC_IP_V6:-${DOMAIN_NAME:-cyberfortress.local}} 1194"
elif [ "$VPN_PROTO" = "dual" ]; then
    PROTO_LINE="proto tcp"
    REMOTE_LINES="remote ${VPN_PUBLIC_IP:-${DOMAIN_NAME:-cyberfortress.local}} 1194
remote ${VPN_PUBLIC_IP_V6:-${DOMAIN_NAME:-cyberfortress.local}} 1194"
else
    # default: ipv4
    PROTO_LINE="proto udp"
    REMOTE_LINES="remote ${VPN_PUBLIC_IP:-${DOMAIN_NAME:-cyberfortress.local}} 1194"
fi

# 4. Tạo file cấu hình OVPN
cat > $OVPN_FILE << EOF
client
dev tun
${PROTO_LINE}
${REMOTE_LINES}
resolv-retry infinite
nobind
persist-key
persist-tun
cipher AES-256-GCM
data-ciphers AES-256-GCM
tls-version-min 1.3
remote-cert-tls server
verb 3
auth-user-pass
EOF

# 5. Gắn key vào file
echo "<ca>" >> $OVPN_FILE
cat ca.crt >> $OVPN_FILE
echo "</ca>" >> $OVPN_FILE

echo "<cert>" >> $OVPN_FILE
cat issued/${CLIENT_NAME}.crt >> $OVPN_FILE
echo "</cert>" >> $OVPN_FILE

echo "<key>" >> $OVPN_FILE
cat private/${CLIENT_NAME}.key >> $OVPN_FILE
echo "</key>" >> $OVPN_FILE

echo "<tls-crypt-v2>" >> $OVPN_FILE
cat private/${CLIENT_NAME}.tls >> $OVPN_FILE
echo "</tls-crypt-v2>" >> $OVPN_FILE

echo "=========================================="
echo "Done! The profile is at $OVPN_FILE inside the container."
echo "To copy it to Windows, run this in your Windows terminal:"
echo "docker cp openvpn_server:$OVPN_FILE ./${CLIENT_NAME}_pqc.ovpn"
echo "=========================================="
