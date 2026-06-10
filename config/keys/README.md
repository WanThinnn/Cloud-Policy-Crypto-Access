# Keys Directory

This directory contains sensitive key files:

- `cpabe_msk.key` / `cpabe_pk.key` - CP-ABE Master & Public keys (backup from Vault)
- `vault_unseal_keys.json` - Vault unseal keys (auto-generated on init)
- `vault_token.txt` - Vault root token (auto-generated on init)

> These files **MUST NOT** be pushed to Git.