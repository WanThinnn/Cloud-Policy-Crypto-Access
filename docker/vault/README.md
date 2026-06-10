# HashiCorp Vault Configurations

This directory contains the `config.hcl` configuration file for Vault.
When the system starts, this folder is mounted into the Vault container.

> **Note**: The unseal keys and root token are stored in the `config/keys` directory (located in the project root). Both `config/keys` and `data/vault_data` are included in `.gitignore` to prevent sensitive data from being pushed to GitHub.