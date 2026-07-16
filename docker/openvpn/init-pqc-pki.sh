#!/bin/bash
set -e

# Create TUN device if it doesn't exist (useful for WSL or bare Docker)
if [ ! -c /dev/net/tun ]; then
    mkdir -p /dev/net
    mknod /dev/net/tun c 10 200 || true
    chmod 600 /dev/net/tun || true
fi

CONFIG_DIR="/etc/openvpn"
PKI_DIR="/etc/openvpn/pki"

cd $CONFIG_DIR

if [ ! -f "$PKI_DIR/ca.crt" ]; then
    # Read environment variables with defaults
    DOMAIN_NAME=${DOMAIN_NAME:-"cyberfortress.local"}
    COMPANY_NAME=${COMPANY_NAME:-"CyberFortress"}
    COUNTRY=${COUNTRY:-"VN"}
    STATE=${STATE:-"Ho Chi Minh"}
    LOCALITY=${LOCALITY:-"Thu Duc"}
    ORG=${ORG:-"VNU"}
    ORG_UNIT=${ORG_UNIT:-"UIT"}

    echo "Initializing new PQC PKI with mldsa87 using OpenSSL..."
    mkdir -p $PKI_DIR/private
    mkdir -p $PKI_DIR/issued
    
    # 1. Generate Root CA
    openssl req -x509 -new -newkey mldsa87 -keyout $PKI_DIR/private/ca.key -out $PKI_DIR/ca.crt -nodes -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCALITY}/O=${COMPANY_NAME}/OU=${ORG_UNIT}/CN=${COMPANY_NAME} VPN Root CA" -days 3650
    
    # 2. Generate Server Certificate
    openssl req -new -newkey mldsa87 -keyout $PKI_DIR/private/server.key -out $PKI_DIR/server.csr -nodes -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCALITY}/O=${COMPANY_NAME}/OU=${ORG_UNIT}/CN=${COMPANY_NAME} VPN Server"
    echo -e "extendedKeyUsage=serverAuth\nkeyUsage=digitalSignature" > $PKI_DIR/server_ext.cnf
    openssl x509 -req -in $PKI_DIR/server.csr -CA $PKI_DIR/ca.crt -CAkey $PKI_DIR/private/ca.key -CAcreateserial -out $PKI_DIR/issued/server.crt -days 3650 -extfile $PKI_DIR/server_ext.cnf
    
    # 3. Generate DH params (for TLS fallback if necessary)
    openssl dhparam -out $PKI_DIR/dh.pem 2048
    
    # 4. Generate tls-crypt-v2 key
    openvpn --genkey tls-crypt-v2-server $PKI_DIR/private/tls-crypt-v2-server.key
    
    # Copy to main dir
    cp $PKI_DIR/ca.crt $CONFIG_DIR/CyberFortress-VPN-RootCA.crt
    cp $PKI_DIR/issued/server.crt $CONFIG_DIR/cyberfortress-vpn-server.crt
    cp $PKI_DIR/private/server.key $CONFIG_DIR/cyberfortress-vpn-server.key
    cp $PKI_DIR/dh.pem $CONFIG_DIR/dh.pem
    cp $PKI_DIR/private/tls-crypt-v2-server.key $CONFIG_DIR/tls-crypt-v2-server.key
    
    echo "PQC PKI Initialization Complete!"
else
    echo "PKI already exists. Skipping initialization."
fi

if [ ! -f "$CONFIG_DIR/server.conf" ]; then
    # Determine proto based on VPN_PROTO (ipv6/dual → tcp6-server, all others → udp)
    VPN_PROTO=${VPN_PROTO:-"ipv4"}
    if [ "$VPN_PROTO" = "ipv6" ] || [ "$VPN_PROTO" = "dual" ]; then
        PROTO_VALUE="tcp6-server"
    else
        PROTO_VALUE="udp"
    fi
    sed "s/VPN_PROTO_VALUE/${PROTO_VALUE}/g" $CONFIG_DIR/server.conf.template > $CONFIG_DIR/server.conf
    echo "Server config created with proto=${PROTO_VALUE} (VPN_PROTO=${VPN_PROTO})"
fi

# Configure and start dnsmasq for local domain resolution using Docker's internal DNS (127.0.0.11)
DOMAIN_NAME=${DOMAIN_NAME:-"cyberfortress.local"}
echo "server=/$DOMAIN_NAME/127.0.0.11" > /etc/dnsmasq.conf
echo "server=8.8.8.8" >> /etc/dnsmasq.conf
echo "Starting dnsmasq..."
dnsmasq
