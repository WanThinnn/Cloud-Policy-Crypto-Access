## Cloud Policy **Quantum** Access v2.3.0

> [!WARNING]
> **Post-Quantum TLS Requirement:** This system strictly enforces **Hybrid ML-KEM-768 (Kyber)** key exchange and **ML-DSA-87** certificates. You **MUST use Chrome or Edge version 150+** to successfully complete the TLS handshake. Older browsers or browsers without ML-DSA support will fail to connect.

### What's New in v2.3.0

This release brings major improvements to the dynamic Attribute-Based Access Control (ABAC) engine, robust protection against privilege escalation, and significant bug fixes in the cryptography workflow.

#### 1. Dynamic ABAC Engine Overhaul
- **Fixed PyCasbin Evaluation Failure:** Resolved a critical bug where PyCasbin's internal `eval()` failed to evaluate complex attribute-based logic due to missing `r.sub.` prefixes. The system now utilizes a highly robust, manual AST (Abstract Syntax Tree) evaluation loop using `safe_eval_condition` in `CasbinService`. This ensures that dynamic Access Policies (stored in the database) correctly restrict endpoints based on real-time user attributes.
- **Removed Hardcoded Permissions:** Eliminated legacy, hardcoded RBAC checks (like `IsSuperAdmin`) from the API layer (`attributes.py`), fully handing over access control to the dynamic ABAC middleware. This allows for truly fine-grained, policy-driven authorization without modifying source code.

#### 2. Robust Privilege Escalation Protection
- **Hierarchy Enforcement (RBAC):** Added strict security checks in `users.py` to prevent any non-SuperAdmin user from creating, updating, deleting, or resetting passwords for SuperAdmin accounts.
- **Prevention of Self-Demotion/Lockout:** SuperAdmins can no longer accidentally (or maliciously) alter their own `user_type` (downgrade privileges) or `account_status` (lock themselves out). This mitigates self-inflicted Denial of Service (DoS) and logic flaws.
- **Separation of Duties (SoD) for Attributes:** Implemented strict SoD controls in `attributes.py`. Administrators are now explicitly blocked from assigning, bulk-assigning, or deleting their own ABAC attributes. This effectively prevents the "Privilege Escalation via Self-Assignment" vulnerability.

#### 3. Enhanced UI Error Handling & User Experience
- **Visible Security Alerts:** Fixed multiple issues in the Frontend (`users.html`) where critical Backend HTTP 403 (Forbidden) security errors were swallowed or rendered invisibly. Error messages regarding privilege violations or SoD breaches now appear directly inside the modal forms (e.g., User Creation, Attribute Assignment), ensuring the user immediately sees why an action was blocked.

#### 4. Cryptography Workflow Bug Fix
- **PQC Master Public Key Retrieval:** Fixed an issue where the `download_public_key` API endpoint crashed because it attempted to retrieve the MPK from the wrong location. It now correctly fetches the MPK from the Vault KV backend (`secret/abe/mpk`) instead of the non-existent `abe/` namespace, restoring the ability for users to download the system's public key.


### How PQC Signature & Passkey Works

> [!NOTE] "How can my fingerprint sign a document?"
> **Your fingerprint does NOT directly sign documents.** Instead, it **unlocks** a Post-Quantum Cryptography (PQC) signing key that was encrypted and stored securely on our server. Here is the full process:

#### Architecture: Dual-Layer PQC Signature

```
┌─────────────────────────────────────────────────────────────────┐
│                     One-Time Key Setup                          │
│                                                                 │
│  1. Browser generates ML-DSA-87 Keypair (Public + Secret Key)   │
│  2. Browser creates a Passkey via WebAuthn (stored in TPM)      │
│  3. WebAuthn PRF derives a 256-bit AES key from the Passkey     │
│  4. Secret Key is encrypted (AES-GCM-256) with the PRF key     │
│  5. Encrypted Secret Key is uploaded to the server              │
│  6. A 24-word Recovery Phrase is generated as backup             │
│                                                                 │
│  ⚠️ The raw Secret Key NEVER leaves your device unencrypted     │
│  ⚠️ The server ONLY stores the encrypted blob                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Signing a Document                            │
│                                                                 │
│  1. User clicks "Upload" on a document                            │
│  2. Browser prompts for biometric (fingerprint/face/PIN)        │
│  3. WebAuthn PRF re-derives the SAME 256-bit AES key            │
│  4. Encrypted Secret Key is downloaded from server              │
│  5. Secret Key is decrypted in browser memory (WASM sandbox)    │
│  6. ML-DSA-87 signs the document hash using the Secret Key      │
│  7. Signature is uploaded to server                             │
│  8. Secret Key is wiped from memory after 30 min of inactivity  │
│                                                                 │
│  ✅ Your biometric = unlock key, NOT the signing key itself     │
└─────────────────────────────────────────────────────────────────┘
```

#### Key Concepts

| Term | Explanation |
|---|---|
| **ML-DSA-87** | Post-Quantum digital signature algorithm (NIST standardized). Replaces RSA/ECDSA. Resistant to quantum computer attacks. |
| **WebAuthn PRF** | A cryptographic extension that derives a deterministic secret from your Passkey + device hardware. Used to encrypt/decrypt the signing key. |
| **TPM / Secure Enclave** | Hardware security chip on your device. Stores the Passkey securely — it cannot be extracted or copied. |
| **Recovery Phrase** | A 24-word backup phrase. If you lose your device, you can use this phrase to decrypt your signing key and create a new Passkey on a new device. |

#### Cross-Browser & Cross-Device Behavior

| Platform | Passkey stored in | Cross-browser (same device) | Cross-device sync |
|---|---|---|---|
| **Windows** | Windows Hello (TPM) | ✅ All browsers (Chrome, Edge, etc.) share the same Passkey | ❌ Device-bound — cannot sync to another PC |
| **macOS / iOS** | iCloud Keychain | ✅ All browsers (Safari, Chrome, etc.) share the same Passkey | ✅ Syncs across Mac ↔ iPhone ↔ iPad via iCloud |

> [!IMPORTANT]
> **When creating a Passkey, you MUST select your device's built-in security:**
> - **Windows:** Select **"Windows Hello"** (fingerprint, PIN, or face recognition)
> - **macOS:** Select **"This Device"** or **Touch ID**
>
> Do **NOT** select Google Password Manager, iCloud Keychain sync, 1Password, Bitwarden, or any third-party Password Manager — they do not reliably support the PRF encryption required for PQC signatures.

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
