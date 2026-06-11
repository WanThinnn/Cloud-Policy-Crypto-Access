import subprocess
import os

# --- Configuration ---
# X.509 Subject details extracted from original certificates
ROOT_SUBJ = "/C=VN/ST=Ho Chi Minh/L=Thu Duc/O=VNU/OU=UIT/CN=CyberFortress-RootCA"
LEAF_SUBJ = "/C=VN/ST=Ho Chi Minh/L=Thu Duc/O=VNU/OU=UIT/CN=cyberfortress.local"

# Post-Quantum Cryptography Algorithm (Strongest NIST Standardized - FIPS 204)
# ML-DSA-87 provides security equivalent to AES-256 (NIST Security Level 5)
PQC_ALGORITHM = "MLDSA87"

# File names with "pq-" prefix
ROOT_KEY = "pq-CyberFortress-RootCA.key"
ROOT_CRT = "pq-CyberFortress-RootCA.crt"
LEAF_KEY = "pq-_.cyberfortress.local.key"
LEAF_CSR = "pq-_.cyberfortress.local.csr"
LEAF_CRT = "pq-_.cyberfortress.local.crt"
EXT_FILE = "pq-v3.ext"
CONF_FILE = "pq-openssl.cnf"

def run_cmd(cmd):
    """Utility to run shell commands via subprocess"""
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    print("="*60)
    print(f"Generating Post-Quantum Certificates ({PQC_ALGORITHM})")
    print("="*60)

    # 0. Create minimal openssl config
    print("\n[0/4] Creating minimal openssl.cnf...")
    with open(CONF_FILE, "w", encoding="utf-8") as f:
        f.write("[req]\n")
        f.write("distinguished_name = req_distinguished_name\n")
        f.write("x509_extensions = v3_ca\n")
        f.write("prompt = no\n")
        f.write("[req_distinguished_name]\n")
        f.write("C = VN\n")
        f.write("[v3_ca]\n")
        f.write("basicConstraints = critical,CA:true\n")
    
    # 1. Generate Root CA (Key & Self-Signed Certificate)
    # Valid for 10 years (3650 days) matching original
    print("\n[1/4] Generating PQC Root CA...")
    run_cmd([
        "openssl", "req", "-config", CONF_FILE, "-x509", "-new", "-newkey", PQC_ALGORITHM, 
        "-keyout", ROOT_KEY, "-out", ROOT_CRT, "-nodes", 
        "-subj", ROOT_SUBJ, "-days", "3650"
    ])

    # 2. Generate Leaf Certificate (Key & CSR)
    print("\n[2/4] Generating PQC Leaf Key and CSR...")
    run_cmd([
        "openssl", "req", "-config", CONF_FILE, "-new", "-newkey", PQC_ALGORITHM, 
        "-keyout", LEAF_KEY, "-out", LEAF_CSR, "-nodes", 
        "-subj", LEAF_SUBJ
    ])

    # 3. Create extension file for Subject Alternative Names (SANs)
    print("\n[3/4] Creating extension config file...")
    with open(EXT_FILE, "w", encoding="utf-8") as f:
        f.write("authorityKeyIdentifier=keyid,issuer\n")
        f.write("basicConstraints=CA:FALSE\n")
        f.write("keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment\n")
        f.write("subjectAltName = @alt_names\n\n")
        f.write("[alt_names]\n")
        f.write("DNS.1 = cyberfortress.local\n")
        f.write("DNS.2 = *.cyberfortress.local\n")
    print(f"Created {EXT_FILE}")

    # 4. Sign the Leaf Certificate using the Root CA
    # Valid for 1 year (365 days) matching original
    print("\n[4/4] Signing Leaf Certificate with Root CA...")
    run_cmd([
        "openssl", "x509", "-req", "-in", LEAF_CSR, 
        "-CA", ROOT_CRT, "-CAkey", ROOT_KEY, 
        "-CAcreateserial", "-out", LEAF_CRT, 
        "-days", "365", "-extfile", EXT_FILE
    ])

    # Cleanup temporary files
    if os.path.exists(LEAF_CSR):
        os.remove(LEAF_CSR)
    if os.path.exists(EXT_FILE):
        os.remove(EXT_FILE)
    if os.path.exists(CONF_FILE):
        os.remove(CONF_FILE)

    print("\n" + "="*60)
    print("SUCCESS! Post-Quantum Certificates generated:")
    print(f" - {ROOT_CRT} & {ROOT_KEY}")
    print(f" - {LEAF_CRT} & {LEAF_KEY}")
    print("="*60)

if __name__ == "__main__":
    main()
