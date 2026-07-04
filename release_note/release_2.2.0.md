## Cloud Policy **Quantum** Access v2.2.0

> [!WARNING]
> **Post-Quantum TLS Requirement:** This system strictly enforces **Hybrid ML-KEM-768 (Kyber)** key exchange and **ML-DSA-87** certificates. You **MUST use Chrome or Edge version 150+** to successfully complete the TLS handshake. Older browsers or browsers without ML-DSA support will fail to connect.

### What's New in v2.2.0

This release focuses on hardening the internal cryptographic architecture, ensuring true Zero-Trust and Cryptography-as-a-Service principles are applied across the entire system.

#### 1. True Cryptography-as-a-Service Architecture
- **Complete Master Key Isolation:** The CP-ABE Master Secret Key (MSK) is now exclusively generated, stored, and utilized deep within the HashiCorp Vault custom plugin's internal storage. The MSK no longer touches the Django application memory or the local host disk at any time, eliminating the risk of root key compromise via host access.
- **Detailed CP-ABE Processing Flows:** The entire cryptographic lifecycle is now handled inside Vault's secure enclave:
  - **Setup (`/v1/abe/setup`):** Executed securely inside the Vault C++ Engine. The MSK is generated and stored directly into the Vault plugin's backend (`msk/abe`). Only the Public Key (PK) is returned to the application.
  - **Key Generation (`/v1/abe/genkey`):** The application sends the user's attributes to Vault. Vault uses the internally stored MSK to mathematically generate a unique User Secret Key (SK) strictly bound to those attributes, returning it Just-In-Time (JIT) for the active session.
  - **Encryption (`/v1/abe/encrypt`):** The application delegates encryption by sending the plaintext DEK (Data Encryption Key) and access policy to Vault. Vault performs the complex Hybrid PQC + CP-ABE encryption and returns the ciphertext.
  - **Decryption (`/v1/abe/decrypt`):** The application sends the ciphertext and the ephemeral User SK to Vault. Vault validates the policy and returns the plaintext, ensuring sensitive data manipulation remains within the secure boundary.

#### 2. Encrypted RAM Caching for Ephemeral Keys
- **AES-256-GCM Cache Encryption:** Ephemeral CP-ABE User Secret Keys cached in Redis are now fully encrypted *at rest* within the RAM. 
- **HKDF Context Binding:** The AES encryption key used for the cache is securely derived using HKDF from the Vault `MASTER_FIELD_ENCRYPTION_KEY`, and is cryptographically bound to the user's specific `user_id` and attribute hash via AES-GCM's Additional Authenticated Data (AAD). This prevents cache swapping and protects the keys even if a full Redis memory dump is compromised.

#### 3. Secure Initialization (Disk-less Key Generation)
- **Zero-Disk-Write Setup:** Removed the legacy behavior in `init_data.py` that created a plaintext backup of the `MASTER_FIELD_ENCRYPTION_KEY` on the local file system. The key is now generated strictly in memory and injected securely into Vault's KV v2 engine (`secret/`), heavily reducing the attack surface during system provisioning.

#### 4. Vault Stability & Logging Improvements
- **Idempotent Engine Initialization:** Fixed an issue where the Vault Manager script spam-logged `"path is already in use"` errors during container restarts. The initialization script now properly interrogates existing mounted secret engines (`secret/` and `abe/`) before attempting enablement, resulting in clean, noise-free Vault logs.

#### 5. Supabase Storage Reliability Fix
- **Upload Stream Bug Resolved:** Fixed a critical bug (`UnboundLocalError: local variable 'response' referenced before assignment`) that occurred when uploading files to Supabase after the storage instance experienced a cold start or temporary API failure. The data payload is now explicitly wrapped in an `io.BytesIO()` stream, ensuring proper handling by the underlying `supabase-py` HTTP client.

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
