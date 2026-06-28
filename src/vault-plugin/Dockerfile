FROM ubuntu:24.04 AS builder

RUN apt-get update && apt-get install -y \
    build-essential cmake libssl-dev wget golang-go

WORKDIR /app
COPY . .

# Build Go Plugin
RUN go build -o build/vault-plugin-abe cmd/vault-plugin-abe/main.go
