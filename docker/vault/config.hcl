storage "raft" {
  path    = "/vault/file"
  node_id = "vault_server"
}

disable_mlock = true
api_addr = "https://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = 0
  tls_cert_file = "/vault/config/certs/_.cyberfortress.local.crt"
  tls_key_file  = "/vault/config/certs/_.cyberfortress.local.key"
  tls_disable_client_certs = "true"
}

ui = true
plugin_directory = "/vault/plugins"
