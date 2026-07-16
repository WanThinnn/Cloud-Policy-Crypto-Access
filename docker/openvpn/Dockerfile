FROM ubuntu:26.04

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# Install OpenVPN 3.5 and required networking tools
RUN apt-get update && \
    apt-get install -y openvpn iptables iproute2 bash ufw jq curl dnsmasq && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /etc/openvpn

# Copy initialization script, configuration template and auth script
COPY init-pqc-pki.sh /usr/local/bin/init-pqc-pki.sh
COPY server.conf.template /etc/openvpn/server.conf.template
COPY auth-django.sh /etc/openvpn/auth-django.sh

# Make scripts executable
RUN chmod +x /usr/local/bin/init-pqc-pki.sh /etc/openvpn/auth-django.sh

# The script will initialize PKI if missing, then start OpenVPN
CMD ["/bin/bash", "-c", "/usr/local/bin/init-pqc-pki.sh && iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -j MASQUERADE && openvpn --config /etc/openvpn/server.conf"]
