# Configuration Directory

This directory contains all the sensitive configuration files for the system.

## Structure

```
config/
├── keys/          # CP-ABE keys, Vault unseal keys, Vault root token
│   ├── cpabe_msk.key              # CP-ABE Master Secret Key (backup)
│   ├── cpabe_pk.key               # CP-ABE Public Key (backup)
│   ├── vault_unseal_keys.json     # Vault unseal keys (auto-generated)
│   └── vault_token.txt            # Vault root token (auto-generated)
├── certs/         # SSL/TLS certificates
│   ├── _.cyberfortress.local.crt  # Wildcard certificate
│   ├── _.cyberfortress.local.key  # Wildcard private key
│   └── CyberFortress-RootCA.crt   # Root CA certificate
└── README.md      # This file
```

## Security Notes

> ⚠️ **DO NOT PUSH** key and certificate files to Git. They have been added to `.gitignore`.

- Only `README.md` files in each subdirectory are tracked by Git.
- When cloning the project, you need to recreate or copy the sensitive files.
