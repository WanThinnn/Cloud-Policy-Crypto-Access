"""
Cross-platform setup script using only Python built-ins.
Checks Docker/Docker Compose, copies .env if missing, and installs Root CA.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = REPO_ROOT / "certs"
ENV_FILE = REPO_ROOT / ".env"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
ROOT_CA = CERT_DIR / "CyberFortress-RootCA.crt"
WILDCARD_CERT = CERT_DIR / "_.cyberfortress.local.crt"
WILDCARD_KEY = CERT_DIR / "_.cyberfortress.local.key"


def check_command(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"{name} is not installed or not in PATH. Please install it first.")


def run_cmd(cmd: list[str], require_sudo: bool = False) -> None:
    if require_sudo and shutil.which("sudo"):
        cmd = ["sudo", *cmd]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def ensure_env() -> None:
    if ENV_FILE.exists():
        return
    if not ENV_EXAMPLE.exists():
        raise SystemExit(".env.example is missing; cannot create .env.")
    shutil.copy(ENV_EXAMPLE, ENV_FILE)
    print("Created .env from .env.example. Please review values.")


def ensure_certs() -> None:
    missing = [p for p in (WILDCARD_CERT, WILDCARD_KEY, ROOT_CA) if not p.exists()]
    if missing:
        names = ", ".join(str(p) for p in missing)
        raise SystemExit(f"Certificate files missing: {names}")
    print("Certificates found.")


def install_root_ca() -> bool:
    system = platform.system().lower()
    print(color_info(f"Installing Root CA on {system} ..."))
    if system == "windows":
        try:
            run_cmd(["certutil", "-addstore", "-f", "ROOT", str(ROOT_CA)])
            return True
        except subprocess.CalledProcessError:
            print(color_warning("\nRun PowerShell as Administrator and execute:"))
            print(f"certutil -addstore -f ROOT \"{ROOT_CA}\"")
            return False
    if system == "darwin":
        try:
            run_cmd(
                ["security", "add-trusted-cert", "-d", "-r", "trustRoot",
                 "-k", "/Library/Keychains/System.keychain", str(ROOT_CA)],
                require_sudo=True,
            )
            return True
        except subprocess.CalledProcessError:
            print("If this fails, install manually with:")
            print("  sudo security add-trusted-cert -d -r trustRoot "
                  "-k /Library/Keychains/System.keychain "
                  f"\"{ROOT_CA}\"")
            return False
    # Assume Linux/Unix
    ca_dir = Path("/usr/local/share/ca-certificates")
    target = ca_dir / ROOT_CA.name
    try:
        run_cmd(["cp", str(ROOT_CA), str(target)], require_sudo=True)
        run_cmd(["update-ca-certificates"], require_sudo=True)
        return True
    except subprocess.CalledProcessError:
        print("Manual install instructions:")
        print(f"  sudo cp {ROOT_CA} /usr/local/share/ca-certificates/")
        print("  sudo update-ca-certificates")
        return False

def color_warning(text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[1m\033[93m{text}\033[0m"  # Bright yellow/orange

def color_info(text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[1m\033[94m{text}\033[0m"  # Bright blue

def main() -> int:
    print("=== Library Management System - Setup ===")
    check_command("docker")
    try:
        subprocess.run(["docker", "compose", "version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        raise SystemExit("Docker Compose v2 is required (docker compose). Please enable it in Docker Desktop or install it.")

    ensure_env()
    ensure_certs()
    ca_installed = install_root_ca()


    if not ca_installed:
        
        print(color_warning("\nWARNING: Root CA was NOT installed. HTTPS certs will show as untrusted."))
        print("Options:")
        print("  1) Re-run setup as Administrator to install the cert.")
        print("  2) Bypass: run dev over HTTP at http://localhost:8080 (no SSL).")
        print(color_info("\nNext steps:"))
        print("  python start.py build")
        print("  python start.py up")
        print("  python start.py migrate")
        print("  python start.py initdata")
        return 1
    
    print(color_info("\n✓ Setup completed successfully!"))
    print(color_info("\nNext steps:"))
    print("  python start.py build")
    print("  python start.py up")
    print("  python start.py migrate")
    print("  python start.py initdata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
