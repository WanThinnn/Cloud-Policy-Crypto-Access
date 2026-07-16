# OpenVPN PQC Native (Post-Quantum Cryptography)

This directory contains the setup for an OpenVPN 3.5 server that natively supports Post-Quantum Cryptography (ML-DSA-87) via OpenSSL.

## Features
- **Base Image:** `ubuntu:26.04` (includes OpenVPN 3.5 & OpenSSL 3.5).
- **Signature Algorithm:** `ML-DSA-87` for Root CA, Server, and Client certificates.
- **TLS 1.3:** Enforces TLS 1.3 for Hybrid KEM (X25519MLKEM768).
- **NAT Routing:** Automatically routes and masquerades VPN traffic into the internal Docker network (`app-network`).
- **Dual Server Setup:** Runs alongside the Standard ECC OpenVPN server to support all devices. This PQC server runs on **port 1194 (UDP)**.

## Step-by-Step Guide for Fresh Installations

If you are setting up this project on a brand new server, follow these steps to initialize and start the VPN servers.

### 1. Configure the Environment
Ensure your `.env` file is properly configured. Crucially, set the `DOMAIN_NAME` to your server's base domain (e.g., `cyberfortress.local` or your public domain). Do **not** use wildcards (like `*.domain.com`) as it will result in invalid routing configurations inside the VPN profiles.

### 2. Build and Start the Services
To start the entire stack, including both the PQC and Standard VPN servers, run the python helper script with the `--vpn` flag:

```bash
python start.py --vpn rebuild
```
*(This command builds the necessary Docker images, initializes the Post-Quantum PKI, and starts the containers.)*

During the first run, the `openvpn_server` container will automatically:
- Initialize the PKI using OpenSSL.
- Generate a Root CA (ML-DSA-87).
- Generate a Server Certificate (ML-DSA-87).
- Generate the TLS-Crypt-V2 key.

All persistent PKI data is stored safely in the `openvpn_data` Docker volume.

### 3. Generate Client Profiles (.ovpn)
To create an OpenVPN profile for a new client (e.g., `alice_laptop`), simply run:

```bash
python start.py --vpn vpn_client alice_laptop
```

This helper command will automatically:
1. Generate the necessary certificates for the client.
2. Output **two** separate `.ovpn` files in your root directory:
   - `alice_laptop_pqc.ovpn` (The PQC profile: use this on PCs/Laptops with OQS-enabled OpenVPN clients).
   - `alice_laptop_classic.ovpn` (The Standard ECC profile: use this on iPhones, Androids, or standard devices).

### 4. Connect to the VPN
Import the generated `.ovpn` file into your OpenVPN client. Note that the PQC VPN server requires a client that has been compiled with OQS (Open Quantum Safe) support to successfully complete the ML-DSA-87 TLS handshake.

Enjoy your Quantum-Safe network!
