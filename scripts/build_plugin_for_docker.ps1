$ErrorActionPreference = "Stop"

$PROJECT_ROOT = Resolve-Path -Path "$PSScriptRoot\.." | Select-Object -ExpandProperty Path
$PLUGIN_SRC_DIR = "$PROJECT_ROOT\src\vault-plugin"
$PLUGIN_OUT_DIR = "$PROJECT_ROOT\docker\vault\plugins"

Write-Host "========================================================="
Write-Host " Building Vault ABE Plugin for Linux AMD64 via Docker..."
Write-Host "========================================================="

if (-not (Test-Path -Path $PLUGIN_OUT_DIR)) {
    New-Item -ItemType Directory -Path $PLUGIN_OUT_DIR | Out-Null
}

Push-Location $PLUGIN_SRC_DIR
Write-Host "Building docker image for cross-compilation..."
docker build -t vault-abe-builder --target builder -f Dockerfile .

Write-Host "Extracting compiled binary to $PLUGIN_OUT_DIR..."
# In powershell we need to properly format paths for docker volumes
$VOL_PATH = $PLUGIN_OUT_DIR -replace '\\', '/'
docker run --rm -v "${VOL_PATH}:/out" vault-abe-builder cp /app/build/vault-plugin-abe /out/vault-plugin-abe

Pop-Location

Write-Host "Done! The plugin binary is now at $PLUGIN_OUT_DIR\vault-plugin-abe"
