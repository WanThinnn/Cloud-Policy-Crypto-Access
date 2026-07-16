# OpenVPN Standard ECC (Legacy & Mobile Device Support)

This directory contains a parallel OpenVPN server configured to use standard Elliptic Curve Cryptography (ECC - prime256v1). 
Since many mobile devices (like iPhones and Androids) and standard OpenVPN clients do not yet support Post-Quantum Cryptography (ML-DSA), this server acts as a fallback to ensure all devices can securely access the internal network.

## Features
- **Base Image:** `ubuntu:26.04`.
- **Signature Algorithm:** Standard ECC (`prime256v1`) for broad compatibility.
- **TLS Version:** Supports TLS 1.2+ to accommodate older clients.
- **NAT Routing:** Connects to the same internal Docker network (`app-network`) but uses a separate subnet (`10.9.0.0/24`) to prevent routing conflicts with the PQC server.
- **Port:** Listens on **port 1195 (UDP)**.

## Usage & Client Generation

This server is deeply integrated into the project's startup scripts and runs automatically alongside the PQC server when the `--vpn` flag is used.

### Generating Client Profiles
You do not need to interact with this container manually. When you generate a VPN client profile using the project's main script:

```bash
python start.py --vpn vpn_client username
```

The script will automatically trigger the internal `gen-client.sh` tool within this container. It will output a `username_classic.ovpn` file in the project's root directory.

This `_classic.ovpn` file uses standard ECC cryptography and connects via port 1195, making it 100% compatible with the official OpenVPN Connect app on the iOS App Store and Google Play Store.
