## Cloud Policy **Quantum** Access v2.1.0

> [!WARNING]
> **Post-Quantum TLS Requirement:** This system strictly enforces **Hybrid ML-KEM-768 (Kyber)** key exchange and **ML-DSA-87** certificates. You **MUST use Chrome or Edge version 150+** to successfully complete the TLS handshake. Older browsers or browsers without ML-DSA support will fail to connect.

### What's New in v2.1.0

This release focuses on significantly improving the developer experience (DX), infrastructure orchestration, and refining the internal zero-trust architecture.

#### 1. Flexible External TLS Management (`USE_EXTERNAL_TLS`)
- Introduced a new environment variable `USE_EXTERNAL_TLS` in `.env`.
- Developers can now easily toggle off the external Nginx HTTPS proxy by setting `USE_EXTERNAL_TLS=False` to test the application locally via `http://localhost:8080`.
- **Zero-Trust Internal Network Preserved**: Even if external TLS is disabled, the internal microservices (Django, HashiCorp Vault, Redis, PKI Signer) continue to communicate securely using automatically generated internal certificates. 

#### 2. PKI Signer Networking Fixes
- Resolved strict hostname verification issues (SSL `Hostname mismatch`) between the Django backend and the PKI Signer container.
- The system now properly validates the Custom CyberFortress Root CA within the internal container network without throwing `urllib` 400 Bad Request or SSL verification errors.

#### 3. Enhanced Terminal UI & DX
- Vault initialization and unsealing warnings in `start.py` and `initdata` have been upgraded with bold ANSI Yellow highlighting. This ensures critical security warnings (like backing up the `FIELD_ENCRYPTION_KEY` or Vault Unseal Keys) catch the administrator's attention immediately without looking like crash errors.
- Fully translated `.env.example` documentation and TLS setup instructions to English for broader accessibility.

#### 4. Automated Release Pipeline
- Integrated automated Docker Hub pushing via `./scripts/release.sh`. Multi-architecture images (`amd64`, `arm64`) for `pqc-latest` and version-specific tags (e.g., `v2.1.0`) are now automatically built and published during the CI/CD pipeline.

#### 5. Synchronous Early-Rejection ClamAV Architecture
- **Optimized Malware Scanning UX**: ClamAV scanning is now integrated synchronously using an "Early Rejection" architecture.
- Instead of scanning asynchronously and silently deleting infected files, the system now streams the plaintext buffer to ClamAV *before* performing heavy CP-ABE encryption or uploading to Supabase.
- If malware (like EICAR) is detected, the upload is aborted instantly, returning a `400 Bad Request` with a clear explanation to the user. This saves tremendous CPU and network bandwidth under malicious loads.

#### 6. Multi-Architecture Compatibility (Apple Silicon / ARM64)
- Added `platform: linux/amd64` constraint to `web` (Django) service in `docker-compose` and `docker-compose.prod.yml`.
- This ensures full compatibility on Mac M-Series chips and AWS Graviton by seamlessly engaging Rosetta 2 / QEMU emulation for native C++ x64 dependencies (like Crypto++ and libhybrid-cp-abe), preventing `wrong ELF class` crashes without requiring custom ARM64 compilation.

#### 7. Refined Configuration & Zero Trust Security
- **Environment Key Rename**: Renamed `FIELD_ENCRYPTION_KEY` to `MASTER_FIELD_ENCRYPTION_KEY` in `.env.example` and documentation to better reflect its critical role in Supabase blind indexing and AES encryption.
- **Strict TLS Enforcement**: Removed the redundant `CLAMAV_USE_TLS` variable. The system now strictly enforces TLS 1.3 encryption on the internal ClamAV connection via a `socat` sidecar proxy, honoring the Zero-Trust internal network philosophy without allowing plaintext fallbacks.

---

### Quick Start
```bash
git clone https://github.com/WanThinnn/Cloud-Policy-Crypto-Access.git
cd Cloud-Policy-Crypto-Access
git switch feature/cloud-policy-quantum-access
python start.py --prod build
python start.py --prod up
python start.py --prod initdata
```

If you are running the application locally from the source code without pulling the pre-built Docker images, you can omit the `--prod` flag:

```bash
git clone https://github.com/WanThinnn/Cloud-Policy-Crypto-Access.git
cd Cloud-Policy-Crypto-Access
git switch feature/cloud-policy-quantum-access
python start.py build
python start.py up
python start.py initdata
```

### Non-PQC Version
If you **do not wish to use the Post-Quantum Cryptography (PQC) features**, please download and use version 1.0.2 instead: https://github.com/WanThinnn/Cloud-Policy-Crypto-Access/releases/tag/v1.0.2
