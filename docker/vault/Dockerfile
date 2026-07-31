# Stage 1: Build the plugin
FROM ubuntu:24.04 AS builder

RUN apt-get update && apt-get install -y \
    build-essential cmake libssl-dev wget golang-go unzip libcrypto++-dev

WORKDIR /app/src/vault-plugin

# Copy go.mod and go.sum to cache dependencies
COPY src/vault-plugin/go.mod src/vault-plugin/go.sum ./
RUN go mod download

# Copy the rest of the plugin source code
COPY src/vault-plugin/ ./

WORKDIR /app/src/vault-plugin
RUN go build -o build/vault-plugin-abe cmd/vault-plugin-abe/main.go

# Stage 2: Final Vault Image (Ubuntu based to support glibc and C++ bindings)
FROM ubuntu:24.04

# Install necessary libraries and utilities
RUN apt-get update && apt-get install -y wget unzip libcap2-bin ca-certificates libcrypto++8t64 \
    && rm -rf /var/lib/apt/lists/*

# Download Vault binary directly to avoid Debian package interference (like background services or default configs)
RUN wget https://releases.hashicorp.com/vault/1.15.6/vault_1.15.6_linux_amd64.zip \
    && unzip vault_1.15.6_linux_amd64.zip \
    && mv vault /usr/bin/vault \
    && rm vault_1.15.6_linux_amd64.zip

# Create directories
RUN mkdir -p /vault/plugins /vault/config /vault/file

# Copy the built plugin from Stage 1
COPY --from=builder /app/src/vault-plugin/build/vault-plugin-abe /vault/plugins/vault-plugin-abe
RUN chmod +x /vault/plugins/vault-plugin-abe

# Enable IPC_LOCK capability for vault binary so it can lock memory
RUN setcap cap_ipc_lock=+ep /usr/bin/vault

# Expose Vault port
EXPOSE 8200

# Run Vault Server
ENTRYPOINT ["/usr/bin/vault"]
CMD ["server", "-config=/vault/config/config.hcl"]
