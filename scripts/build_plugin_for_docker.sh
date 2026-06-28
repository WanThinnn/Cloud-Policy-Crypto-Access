#!/bin/bash
set -e

PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
PLUGIN_SRC_DIR="$PROJECT_ROOT/src/vault-plugin"
PLUGIN_OUT_DIR="$PROJECT_ROOT/docker/vault/plugins"

echo "========================================================="
echo " Building Vault ABE Plugin for Linux AMD64 via Docker..."
echo "========================================================="

mkdir -p "$PLUGIN_OUT_DIR"

cd "$PLUGIN_SRC_DIR"
echo "Building docker image for cross-compilation..."
docker build -t vault-abe-builder --target builder -f Dockerfile .

echo "Extracting compiled binary to $PLUGIN_OUT_DIR..."
docker run --rm -v "$PLUGIN_OUT_DIR:/out" vault-abe-builder cp /app/build/vault-plugin-abe /out/vault-plugin-abe

echo "Done! The plugin binary is now at $PLUGIN_OUT_DIR/vault-plugin-abe"
