# Post-Quantum Certificates (ML-DSA-87)

> [!WARNING]
> **The certificates in this folder are self-signed and should only be used for development and testing purposes. Do not use them in production!**

This directory contains scripts to generate Post-Quantum Cryptography (PQC) certificates using the `ML-DSA-87` signature algorithm. Because standard OS OpenSSL distributions do not yet support PQC algorithms, we use a pre-compiled OpenQuantumSafe (OQS) Docker container to generate the keys.

## How to generate certificates

You must have **Docker** installed and running on your machine.
Open your terminal and `cd` into this `config/certs` directory, then run the appropriate command for your Operating System:

### For Windows (PowerShell)
```powershell
docker run -it --rm -e DOMAIN_NAME="mycompany.com" -e COMPANY_NAME="MyCompany" -v ${PWD}:/certs -w /certs --entrypoint /bin/sh openquantumsafe/curl ./generate_pq_certs_docker.sh
```

### For Windows (Command Prompt - CMD)
```cmd
docker run -it --rm -e DOMAIN_NAME="mycompany.com" -e COMPANY_NAME="MyCompany" -v "%cd%":/certs -w /certs --entrypoint /bin/sh openquantumsafe/curl ./generate_pq_certs_docker.sh
```

### For Linux / macOS
```bash
docker run -it --rm -e DOMAIN_NAME="mycompany.com" -e COMPANY_NAME="MyCompany" -v $(pwd):/certs -w /certs --entrypoint /bin/sh openquantumsafe/curl ./generate_pq_certs_docker.sh
```

### Customization (Optional):
The script supports generating certificates for any domain or company name by passing Environment Variables (`-e`) into the Docker container.
- `DOMAIN_NAME`: The domain for the certificate (e.g., `mycompany.com`). *Default: `cyberfortress.local`*
- `COMPANY_NAME`: The organization name for the Root CA (e.g., `MyCompany`). *Default: `CyberFortress`*

### What it does:
1. Spawns an ephemeral `openquantumsafe/curl` container (which includes OQS-OpenSSL).
2. Mounts your current `certs` directory into the container.
3. Executes the `generate_pq_certs_docker.sh` script to generate a Root CA and a signed Leaf Certificate based on the provided domain/company names.
4. The generated certificates (`.crt` and `.key`) are saved directly to your host machine in this folder.