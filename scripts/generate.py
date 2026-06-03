"""
Generate self-signed certificates for local development using OpenSSL.
Uses only Python built-ins to invoke the openssl CLI.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CERTS_DIR = REPO_ROOT / "certs"
CERT_PATH = CERTS_DIR / "cert.pem"
KEY_PATH = CERTS_DIR / "key.pem"
DAYS = "365"


def main() -> int:
    openssl = shutil.which("openssl")
    if openssl is None:
        raise SystemExit("OpenSSL not found in PATH. Please install it first.")

    CERTS_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        openssl,
        "req",
        "-x509",
        "-nodes",
        "-days",
        DAYS,
        "-newkey",
        "ec",
        "-pkeyopt",
        "ec_paramgen_curve:secp384r1",
        "-keyout",
        str(KEY_PATH),
        "-out",
        str(CERT_PATH),
        "-subj",
        "/C=VN/ST=HoChiMinh/L=HoChiMinh/O=Library/OU=IT/CN=localhost",
    ]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)

    print(f"Generated self-signed cert: {CERT_PATH}")
    print(f"Generated private key:      {KEY_PATH}")
    print("These are for development only. For production use a trusted CA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
