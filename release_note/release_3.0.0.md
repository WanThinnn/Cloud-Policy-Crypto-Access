## Cloud Policy **Quantum** Access v3.0.0

> [!WARNING]
> **Post-Quantum TLS Requirement:** This system strictly enforces **Hybrid ML-KEM-768 (Kyber)** key exchange and **ML-DSA-87** certificates. You **MUST use Chrome or Edge version 150+** to successfully complete the TLS handshake. Older browsers or browsers without ML-DSA support will fail to connect.

### What's New in v3.0.0

This major release brings two groundbreaking features: an intelligent AI Policy Assistant for Natural Language to CP-ABE translation, and a Dual-Engine CP-ABE infrastructure supporting both TKN20 and AC17 schemes simultaneously.

#### 1. AI Policy Assistant (Local LLM Integration)
- **Natural Language to CP-ABE:** Administrators can now generate complex Attribute-Based Access Control (ABAC) and CP-ABE policies simply by describing them in natural language (e.g., "Allow IT staff to read documents, except interns"). It fully supports multiple languages, including Vietnamese.
- **Privacy-Preserving Local AI:** The assistant runs entirely on-premise using Ollama (supporting models like `Phi-4-mini` or `Qwen-2.5 3B`). No policy data or metadata is ever sent to external APIs like OpenAI.
- **Intelligent Metadata & Negation Handling:** The AI automatically deduces and auto-fills `Policy Name`, `Description`, and `Priority`. It properly translates Python AST syntax and handles CP-ABE negations correctly using `not` and `not in`.
- **Customizable RAM Management:** Added `OLLAMA_KEEP_ALIVE` via `.env` configurations to control how long the AI model resides in VRAM/RAM. The start script now features background model warmups (`warmup_ai`) to prevent first-request freezes.

#### 2. Dual-Engine CP-ABE Infrastructure
- **TKN20 & AC17 Coexistence:** The system now mounts and supports two distinct Vault ABE engines (`abe_tkn20/` and `abe_ac17/`) running side-by-side.
- **Seamless Backwards Compatibility:** New files are automatically encrypted using the modern `tkn20` scheme. When users attempt to preview or download older files, the system dynamically checks the database (`abe_scheme` field) and routes the decryption request to the correct legacy `ac17` engine without any user intervention.
- **Blind Index Lookups for File Verification:** Fixed critical bugs related to retrieving `abe_scheme` metadata when database Field Encryption is enabled. The system now utilizes secure blind indexing (`get_db_file_by_path`) to correctly match file paths and route them to the proper decryption scheme.

---

### How PQC Signature & Passkey Works

> [!NOTE] 
> **"How can my fingerprint, face or PIN sign a document?"**
> **Your fingerprint/face/PIN does NOT directly sign documents.** Instead, it **unlocks** a Post-Quantum Cryptography (PQC) signing key that was encrypted and stored securely on our server. Here is the full process:

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

| Term                     | Explanation                                                                                                                                     |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **ML-DSA-87**            | Post-Quantum digital signature algorithm (NIST standardized). Replaces RSA/ECDSA. Resistant to quantum computer attacks.                        |
| **WebAuthn PRF**         | A cryptographic extension that derives a deterministic secret from your Passkey + device hardware. Used to encrypt/decrypt the signing key.     |
| **TPM / Secure Enclave** | Hardware security chip on your device. Stores the Passkey securely — it cannot be extracted or copied.                                          |
| **Recovery Phrase**      | A 24-word backup phrase. If you lose your device, you can use this phrase to decrypt your signing key and create a new Passkey on a new device. |

#### Cross-Browser & Cross-Device Behavior

| Platform        | Passkey stored in   | Cross-browser (same device)                                  | Cross-device sync                             |
| --------------- | ------------------- | ------------------------------------------------------------ | --------------------------------------------- |
| **Windows**     | Windows Hello (TPM) | ✅ All browsers (Chrome, Edge, etc.) share the same Passkey   | ❌ Device-bound — cannot sync to another PC    |
| **macOS / iOS** | iCloud Keychain     | ✅ All browsers (Safari, Chrome, etc.) share the same Passkey | ✅ Syncs across Mac ↔ iPhone ↔ iPad via iCloud |

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
