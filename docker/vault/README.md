# HashiCorp Vault Configurations

Thư mục này chứa file cấu hình `config.hcl` cho Vault.
Khi hệ thống chạy, nó sẽ mount folder này vào trong container Vault.

> **Lưu ý**: Các khóa unseal và root token được lưu trữ trong thư mục `config/keys` (Nằm ở root project). Thư mục `config/keys` và `data/vault_data` đã được đưa vào `.gitignore` để đảm bảo không bị push lên GitHub.
