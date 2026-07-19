"""
Cross-platform Docker helper using only Python built-ins.

Usage:
    python start.py [--prod|--dev] [--tunnel] [--vpn] [--ai] [--ipv6|--ipv4|--ipv46] <command> [args]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
import os
import json
import socket

REPO_ROOT = Path(__file__).resolve().parent
NO_SSL_OVERRIDE = REPO_ROOT / "docker" / "docker-compose.nossl.yml"
CERTS_DIR = REPO_ROOT / "config" / "certs"
ENV_FILE = REPO_ROOT / ".env"
CLOUDFLARE_CONFIG = REPO_ROOT / "config" / "cloudflare" / "config.yml"

# Default SSL certificate filenames (can be overridden via .env)
DEFAULT_SSL_CERT = "_.cyberfortress.local.crt"
DEFAULT_SSL_KEY = "_.cyberfortress.local.key"


def compose_cmd(files: list[Path], use_ssl: bool, use_tunnel: bool, use_vpn: bool = False, use_ai: bool = False) -> list[str]:
    cmd: list[str] = ["docker", "compose", "--project-directory", str(REPO_ROOT)]
    for f in files:
        cmd += ["-f", str(f)]
    if use_ssl:
        cmd += ["--profile", "ssl"]
    if use_tunnel:
        cmd += ["--profile", "tunnel"]
    if use_vpn:
        cmd += ["--profile", "vpn"]
    if use_ai:
        cmd += ["--profile", "ai"]
    return cmd


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def call_setup(script_path: Path) -> None:
    run([sys.executable, str(script_path)])


def extract_pqc_raw_key(c: list[str]) -> None:
    cert_path = CERTS_DIR / "pq-CyberFortress-RootCA.crt"
    raw_pk_path = CERTS_DIR / "root_ca_raw_pk.b64"
    if not cert_path.exists():
        return
    # Check if raw_pk_path exists and is newer than cert_path
    if raw_pk_path.exists() and raw_pk_path.stat().st_mtime >= cert_path.stat().st_mtime:
        return
    
    print(color_info(f"\n[+] Extracting PQC Raw Public Key from Root CA..."))
    try:
        # Run docker exec on pki_signer to extract the key
        cmd_extract = c + ["exec", "-T", "pki_signer", "sh", "-c", "openssl x509 -in /certs/pq-CyberFortress-RootCA.crt -pubkey -noout | openssl pkey -pubin -outform der | tail -c +23 | base64 -w0"]
        result = subprocess.run(cmd_extract, capture_output=True, text=True, check=True)
        raw_b64 = result.stdout.strip()
        if raw_b64:
            raw_pk_path.write_text(raw_b64, encoding="ascii")
            print("[OK] Raw Public Key extracted successfully.")
    except Exception as e:
        print(color_warning(f"Failed to extract Raw Public Key: {e}"))


def add_manage_args(base: list[str], extra: list[str]) -> list[str]:
    return base + extra


def color_env_label(environment: str) -> str:
    base = f"[{environment}]"
    if not sys.stdout.isatty():
        return base
    color = "\033[92m" if environment == "prod" else "\033[94m"
    return f"\033[1m{color}{base}\033[0m"


def env_status_lines(environment: str, use_ssl: bool, use_tunnel: bool, use_vpn: bool, use_ai: bool) -> str:
    label = color_env_label(environment)
    ssl_note = "on" if use_ssl else "off"
    tunnel_note = "on" if use_tunnel else "off"
    vpn_note = "on" if use_vpn else "off"
    ai_note = "on" if use_ai else "off"
    return f"{label} SSL/TLS={ssl_note} CloudflareTunnel={tunnel_note} VPN={vpn_note} AI={ai_note}"


def env_access_urls(use_ssl: bool) -> str:
    access_urls = (
        "https://localhost, https://cloudsafe.cyberfortress.local (if you installed Root CA and set hosts)"
        if use_ssl
        else "http://localhost:8080"
    )
    return f"Access: {access_urls}"

UDP6_RELAY_PIDFILE = REPO_ROOT / ".udp6_relay.pid"

def start_udp6_relay(relay_port_map: dict[int, int] | None = None) -> None:
    """Start the UDP6 relay on Windows (Docker Desktop lacks IPv6 UDP port forwarding).
    
    Args:
        relay_port_map: Dict mapping listen_port -> forward_port.
                        e.g. {53: 1194, 443: 1195}
    """
    if sys.platform != "win32":
        return  # Not needed on Linux/Mac
    stop_udp6_relay()  # Kill any existing relay
    relay_script = REPO_ROOT / "scripts" / "udp6_relay.py"
    if not relay_script.exists():
        print(color_warning("[!] UDP6 relay script not found. IPv6 VPN may not work."))
        return
    if relay_port_map is None:
        relay_port_map = {53: 1194, 443: 1195}
    # Use pythonw.exe for a truly detached background process on Windows
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = shutil.which("pythonw")
    if not pythonw:
        # Fallback to regular python
        pythonw = sys.executable
    
    cmd = [str(pythonw), str(relay_script)]
    cmd += ["--ports"] + [str(p) for p in relay_port_map.keys()]
    cmd += ["--forward-ports"] + [str(p) for p in relay_port_map.values()]
    log_file = REPO_ROOT / ".udp6_relay.log"
    cmd += ["--log", str(log_file)]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
        # Wait briefly to check if process starts successfully
        import time
        time.sleep(2)
        
        # Verify relay is actually listening by checking the port
        try:
            test_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            test_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            first_port = list(relay_port_map.keys())[0]
            test_sock.bind(("::", first_port))
            # If we can bind, relay is NOT listening → it failed
            test_sock.close()
            error_output = log_file.read_text().strip() if log_file.exists() else "Unknown error"
            print(color_warning(f"[!] UDP6 relay failed to start. Log:"))
            for line in error_output.split("\n")[-5:]:
                print(color_warning(f"    {line.strip()}"))
            print(color_warning("    Try: python scripts/udp6_relay.py (run manually)"))
            return
        except OSError:
            # Port is already in use → relay is running! 
            pass
        
        UDP6_RELAY_PIDFILE.write_text(json.dumps({"pid": proc.pid, "ports": list(relay_port_map.keys())}))
        mapping_str = ", ".join(f"{k}->{v}" for k, v in relay_port_map.items())
        print(color_info(f"[+] UDP6 Relay started (PID {proc.pid}): {mapping_str}"))
        print(color_info(f"    Log: {log_file}"))
    except Exception as e:
        print(color_warning(f"[!] Failed to start UDP6 relay: {e}"))
        print(color_warning("    Try: python scripts/udp6_relay.py (run manually)"))

def stop_udp6_relay() -> None:
    """Stop the UDP6 relay if running."""
    if not UDP6_RELAY_PIDFILE.exists():
        return
    try:
        info = json.loads(UDP6_RELAY_PIDFILE.read_text())
        pid = info.get("pid")
        if pid:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
    except Exception:
        pass
    finally:
        try:
            UDP6_RELAY_PIDFILE.unlink()
        except Exception:
            pass

def color_warning(text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[1m\033[93m{text}\033[0m"  # Bright yellow/orange

def color_info(text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[1m\033[94m{text}\033[0m"  # Bright blue


def load_env_file(env_path: Path) -> dict[str, str]:
    env_vars: dict[str, str] = {}
    if not env_path.exists():
        return env_vars

    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def set_env_var(env_path: Path, key: str, value: str) -> None:
    """Set or update a single key=value in the .env file."""
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return

    content = env_path.read_text()
    lines = content.splitlines(keepends=True)
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        # Ensure there's a newline at end of file before appending
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] = new_lines[-1] + "\n"
        new_lines.append(f"{key}={value}\n")
    env_path.write_text("".join(new_lines))


def should_enable_tunnel(env_vars: dict[str, str]) -> tuple[bool, str]:
    tunnel_id = env_vars.get("CLOUDFLARE_TUNNEL_ID")
    domain = env_vars.get("TUNNEL_DOMAIN")
    config_path = Path(env_vars.get("CLOUDFLARE_CONFIG", CLOUDFLARE_CONFIG))
    credentials_file = env_vars.get(
        "CLOUDFLARE_CREDENTIALS_FILE",
        str(config_path.parent / f"{tunnel_id}.json") if tunnel_id else "",
    )

    if not tunnel_id and not domain:
        return False, ""

    if not tunnel_id or not domain:
        return False, "Cloudflare tunnel skipped (CLOUDFLARE_TUNNEL_ID/TUNNEL_DOMAIN missing in .env)."

    missing = []
    if not config_path.exists():
        missing.append(str(config_path))
    if credentials_file and not Path(credentials_file).exists():
        missing.append(credentials_file)

    if missing:
        return False, f"Cloudflare tunnel skipped (missing files: {', '.join(missing)})."

    return True, ""

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h', '--help', action='store_true', help='Show this help message and exit')
    parser.add_argument("--prod", action="store_true", help="Use production compose file")
    parser.add_argument("--dev", action="store_true", help="Use development compose file (default)")
    parser.add_argument("--tunnel", action="store_true", help="Enable Cloudflare tunnel profile")
    parser.add_argument("--vpn", action="store_true", help="Enable VPN server profile")
    parser.add_argument("--ai", action="store_true", help="Enable AI features (Ollama)")
    parser.add_argument("--ipv6", action="store_true", help="Use IPv6 for VPN client profiles (VPN_PROTO=ipv6)")
    parser.add_argument("--ipv46", action="store_true", help="Use both IPv4 and IPv6 for VPN client profiles (VPN_PROTO=dual)")
    parser.add_argument("command", nargs="?", help="Command to run")
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="Extra args for manage.py commands")
    args = parser.parse_args(argv)

    vault_cmd = ["exec", "web", "python", "vault_manager.py"]
    if args.prod:
        vault_cmd.append("--prod")

    compose_file = REPO_ROOT / "docker" / ("docker-compose.prod.yml" if args.prod else "docker-compose.yml")
    env_vars = load_env_file(ENV_FILE)
    
    # Get SSL certificate filenames from .env or use defaults
    ssl_cert_file = env_vars.get("SSL_CERT_FILE", env_vars.get("PQC_SSL_CERT_FILE", DEFAULT_SSL_CERT))
    ssl_key_file = env_vars.get("SSL_KEY_FILE", env_vars.get("PQC_SSL_KEY_FILE", DEFAULT_SSL_KEY))
    cert_path = CERTS_DIR / ssl_cert_file
    key_path = CERTS_DIR / ssl_key_file
    
    use_ssl_env = str(env_vars.get("USE_EXTERNAL_TLS", "True")).lower() in ("true", "1", "yes", "on")
    use_ssl = use_ssl_env and cert_path.exists() and key_path.exists()
    
    compose_files = [compose_file] if use_ssl else [compose_file, NO_SSL_OVERRIDE]
    use_tunnel = False
    tunnel_note = ""
    if args.tunnel:
        use_tunnel, tunnel_note = should_enable_tunnel(env_vars)
    elif env_vars.get("CLOUDFLARE_TUNNEL_ID") or env_vars.get("TUNNEL_DOMAIN"):
        tunnel_note = "Cloudflare tunnel disabled (pass --tunnel to enable)."

    if tunnel_note:
        print(color_warning(tunnel_note))

    # Force VPN profile if running vpn-related commands
    if args.command in ["vpn_client"]:
        args.vpn = True

    # Determine VPN_PROTO from flags
    if args.ipv46:
        vpn_proto = "dual"
    elif args.ipv6:
        vpn_proto = "ipv6"
    else:
        vpn_proto = "ipv4"

    # Persist VPN_PROTO to .env so containers read it on startup
    # Only update when explicitly passing a VPN-related flag or vpn command
    if args.vpn or args.command in ["vpn_client"]:
        current_proto = env_vars.get("VPN_PROTO", "")
        if current_proto != vpn_proto:
            set_env_var(ENV_FILE, "VPN_PROTO", vpn_proto)
            print(color_info(f"[*] VPN_PROTO set to '{vpn_proto}' in .env"))

    if args.ai:
        current_ai = env_vars.get("AI_FEATURES_ENABLED", "")
        if current_ai.lower() != "true":
            set_env_var(ENV_FILE, "AI_FEATURES_ENABLED", "True")
            print(color_info("[*] AI_FEATURES_ENABLED set to 'True' in .env"))

    c = compose_cmd(compose_files, use_ssl, use_tunnel, args.vpn, args.ai)
    environment = "prod" if args.prod else "dev"
    status_line = env_status_lines(environment, use_ssl, use_tunnel, args.vpn, args.ai)

    print(status_line)
    print("─" * 50)

    cmd = args.command or "help"
    extra = args.rest[1:] if args.rest and args.rest[0] == "--" else args.rest

    scripts_dir = REPO_ROOT / "scripts"

    try:
        if cmd == "setup":
            try:
                call_setup(scripts_dir / "setup.py")
                # setup.py already printed success message and next steps
            except subprocess.CalledProcessError as exc:
                # setup.py already printed error messages and next steps
                return exc.returncode or 1
        elif cmd == "build":
            # print(f"{status_line}\n")
            if args.prod:
                run(c + ["pull"])
            run(c + ["build"])
            print(color_info(f"\n[OK] Build completed.\n"))
            print(color_info("Next: "))
            print("  python start.py up")
        elif cmd == "update":
            print(color_info("\n[1/3] Pulling latest code from git..."))
            try:
                run(["git", "pull"])
            except subprocess.CalledProcessError:
                print(color_warning("Failed to git pull. Please check your git status."))
                return 1
            
            print(color_info("\n[2/3] Pulling and building latest Docker images..."))
            if args.prod:
                run(c + ["pull"])
            run(c + ["build"])
            
            print(color_info("\n[3/3] Restarting containers..."))
            run(c + ["up", "-d"])
            print(color_info(f"\n[+] Waiting for Vault to start and running Auto-Unseal..."))
            import time
            success = False
            for _ in range(10):
                try:
                    run(c + vault_cmd)
                    success = True
                    break
                except subprocess.CalledProcessError:
                    time.sleep(2)
            if not success:
                print(color_warning("Could not run vault_manager.py. The web container might still be starting."))
            
            extract_pqc_raw_key(c)
            
            print(color_info(f"\n[OK] Update completed successfully!\n"))
            print(color_info(f"{env_access_urls(use_ssl)}"))
        elif cmd in {"up"}:
            # print(f"{status_line}\n")
            run(c + ["up", "-d"])
            print(color_info(f"\n[+] Waiting for Vault to start and running Auto-Unseal..."))
            import time
            success = False
            for _ in range(10):
                try:
                    run(c + vault_cmd)
                    success = True
                    break
                except subprocess.CalledProcessError:
                    time.sleep(2)
            if not success:
                print(color_warning("Could not run vault_manager.py. The web container might still be starting."))
            
            extract_pqc_raw_key(c)
            
            print(color_info(f"\n[OK] Services started.\n"))
            print(color_info(f"{env_access_urls(use_ssl)}"))
            if args.vpn and vpn_proto in ("ipv6", "dual"):
                start_udp6_relay({53: 1194, 443: 1195})
        elif cmd in {"down"}:
            # print(f"{status_line}\n")
            stop_udp6_relay()
            run(c + ["down"])
            print("[OK] Services stopped.")
        elif cmd == "restart":
            # print(f"{status_line}\n")
            run(c + ["restart"])
            print(color_info(f"\n[+] Waiting for Vault to start and running Auto-Unseal..."))
            import time
            success = False
            for _ in range(10):
                try:
                    run(c + vault_cmd)
                    success = True
                    break
                except subprocess.CalledProcessError:
                    time.sleep(2)
            if not success:
                print(color_warning("Could not run vault_manager.py. The web container might still be starting."))
            
            extract_pqc_raw_key(c)
            
            print("[OK] Services restarted.")
            if args.vpn and vpn_proto in ("ipv6", "dual"):
                start_udp6_relay({53: 1194, 443: 1195})
        elif cmd == "logs":
            # print(f"{status_line}\n")
            run(c + ["logs", "-f"])
        elif cmd == "makemigrations":
            # print(f"{status_line}\n")
            run(add_manage_args(c + ["exec", "web", "python", "manage.py", "makemigrations"], extra))
        elif cmd == "migrate":
            # print(f"{status_line}\n")
            run(add_manage_args(c + ["exec", "web", "python", "manage.py", "migrate"], extra))
        elif cmd == "initdata":
            # print(f"{status_line}\n")
            print(color_info("\n[0/4] Initializing and unsealing Vault..."))
            run(c + vault_cmd)
            print(color_info("\n[1/4] Running database migrations..."))
            run(add_manage_args(c + ["exec", "web", "python", "manage.py", "migrate"], []))
            print(color_info("\n[2/4] Initializing superuser..."))
            run(c + ["exec", "web", "python", "init_data.py"])
            print(color_info("\n[3/4] Seeding default ABAC policies..."))
            run(add_manage_args(c + ["exec", "web", "python", "manage.py", "seed_policies"], []))
            print(color_info("\n[4/4] Seeding test users & ABAC attributes..."))
            run(add_manage_args(c + ["exec", "web", "python", "manage.py", "seed_test_data"], []))
            
            extract_pqc_raw_key(c)
            
            print(color_info("\n[OK] Initialization complete!"))
            super_admin_user = env_vars.get("DJANGO_SUPERUSER_USERNAME", "super_admin")
            super_admin_pass = env_vars.get("DJANGO_SUPERUSER_PASSWORD", "super_admin123")
            print(color_warning("\n" + "="*50))
            print(color_warning("⚠️  SUPER ADMIN ACCOUNT CREDENTIALS ⚠️"))
            print(color_warning(f"Username: {super_admin_user}"))
            print(color_warning(f"Password: {super_admin_pass}"))
            print(color_warning("\n[!] WARNING: Please log in and change this password IMMEDIATELY!"))
            print(color_warning("="*50 + "\n"))
        elif cmd == "initsettings":
            # print(f"{status_line}\n")
            run(add_manage_args(c + ["exec", "web", "python", "manage.py", "init_settings"], extra))
        elif cmd == "createsuperuser":
            # print(f"{status_line}\n")
            run(c + ["exec", "web", "python", "manage.py", "create_super_admin"])
        elif cmd == "shell":
            # print(f"{status_line}\n")
            run(c + ["exec", "web", "python", "manage.py", "shell"])
        elif cmd == "collectstatic":
            # print(f"{status_line}\n")
            run(c + ["exec", "web", "python", "manage.py", "collectstatic", "--noinput"])
        elif cmd == "clean":
            # print(f"{status_line}\n")
            run(c + ["down", "-v"])
            run(["docker", "system", "prune", "-f"])
            print("[OK] Cleaned up containers, volumes, and system.")
        elif cmd == "rebuild":
            # print(f"{status_line}\n")
            run(compose_cmd(compose_files, use_ssl, use_tunnel, args.vpn) + ["down", "-v"])
            run(compose_cmd(compose_files, use_ssl, use_tunnel, args.vpn) + ["build", "--no-cache"])
            run(compose_cmd(compose_files, use_ssl, use_tunnel, args.vpn) + ["up", "-d"])
            print(color_info(f"\n[+] Waiting for Vault to start and running Auto-Unseal..."))
            try:
                run(c + vault_cmd)
            except subprocess.CalledProcessError:
                print(color_warning("Could not run vault_manager.py. The web container might still be starting."))
            
            extract_pqc_raw_key(c)
            
            print(f"[OK] Rebuilt and started services.\n")
            print(f"{env_access_urls(use_ssl)}")
            if args.vpn and vpn_proto in ("ipv6", "dual"):
                start_udp6_relay({53: 1194, 443: 1195})
        elif cmd == "help":
            print(color_info("Crypto Access Management System"))
            print("─" * 50)
            print(color_info("Usage: python start.py [--prod|--dev] <command> [args]\n"))
            print(color_info("Commands:"))
            print("  setup           Setup environment (.env, certs, Root CA)")
            print("  update          Pull latest code, update images, and restart")
            print("  build           Build Docker images (pull first in prod)")
            print("  up              Start all services")
            print("  down            Stop all services")
            print("  restart         Restart all services")
            print("  logs            Follow logs")
            print("  makemigrations  Create new migrations (passes extra args)")
            print("  migrate         Run database migrations (passes extra args)")
            print("  initsettings    Initialize dynamic system settings")
            print("  initdata        Initialize sample data")
            print("  createsuperuser Create super_admin user (interactive)")
            print("  shell           Open Django shell")
            print("  collectstatic   Collect static files")
            print("  clean           Remove containers and volumes, prune system")
            print("  rebuild         Clean rebuild and start")
            print("  vpn_client      Generate OpenVPN client profile (.ovpn)")
            print("  gencerts <path> Generate PQC certificates in a specific directory")
            print("  ai_setup        Pull the AI model specified in .env (OLLAMA_MODEL)\n")
            print(color_info("VPN Protocol Flags (for vpn_client):"))
            print("  (none)          Default: IPv4 only (uses VPN_PUBLIC_IP)")
            print("  --ipv6          IPv6 only (uses VPN_PUBLIC_IP_V6, proto udp6)")
            print("  --ipv46         Dual-stack: adds both IPv4 and IPv6 remote entries\n")
            print(color_info("Examples:"))
            print("  python start.py setup")
            print("  python start.py build")
            print("  python start.py up")
            print("  python start.py --prod up")
            print("  python start.py migrate -- app_label")
            print("  python start.py vpn_client my_laptop")
        elif cmd == "vpn_client":
            if not extra:
                print(color_warning("Usage: python start.py [--dev/--prod] [--ipv6|--ipv46] vpn_client <client_name>"))
                return 1
            client_name = extra[0]

            # Build environment for container exec to pass VPN_PROTO
            env_override = ["--env", f"VPN_PROTO={vpn_proto}"]
            proto_label = {"ipv4": "IPv4", "ipv6": "IPv6", "dual": "Dual-Stack IPv4+IPv6"}.get(vpn_proto, vpn_proto)
            print(color_info(f"\n[+] Generating PQC Native .ovpn profile for {client_name} ({proto_label})..."))
            
            try:
                # Gọi trực tiếp script tự động bên trong container openvpn (PQC)
                run(c + ["exec"] + env_override + ["openvpn", "/usr/local/bin/gen-client.sh", client_name])
                run(["docker", "cp", f"openvpn_server:/tmp/{client_name}.ovpn", f"./{client_name}_pqc.ovpn"])
                print(color_info(f"\n[OK] Successfully created ./{client_name}_pqc.ovpn (cho Laptop/PC)!"))

                print(color_info(f"\n[+] Generating Standard ECC .ovpn profile for {client_name} ({proto_label})..."))
                # Gọi trực tiếp script tự động bên trong container openvpn_standard
                run(c + ["exec"] + env_override + ["openvpn_standard", "/usr/local/bin/gen-client.sh", client_name])
                run(["docker", "cp", f"openvpn_standard_server:/tmp/{client_name}.ovpn", f"./{client_name}_classic.ovpn"])
                print(color_info(f"\n[OK] Successfully created ./{client_name}_classic.ovpn (cho iPhone/Android)!"))
            except subprocess.CalledProcessError:
                print(color_warning("\n[!] Failed to generate VPN client profile. Is the 'openvpn' container running? Try 'python start.py --vpn up' first."))
        elif cmd == "gencerts":
            if len(sys.argv) < 3:
                print(color_warning("Usage: python start.py gencerts <output_dir>"))
                print("Example: python start.py gencerts ./my_new_certs")
                sys.exit(1)
            
            out_dir = Path(sys.argv[2]).resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
            print(color_info(f"\n[+] Spawning OQS-OpenSSL container to generate PQC certificates in {out_dir}..."))
            
            script_path = REPO_ROOT / "config" / "certs" / "generate_pq_certs_docker.sh"
            
            # Mount the script individually and set the output dir as the working volume
            docker_cmd = [
                "docker", "run", "-it", "--rm",
                "--env-file", str(ENV_FILE),
                "-v", f"{script_path}:/generate.sh:ro",
                "-v", f"{out_dir}:/certs",
                "-w", "/certs",
                "--entrypoint", "/bin/sh",
                "openquantumsafe/curl",
                "/generate.sh"
            ]
            run(docker_cmd)
            print(color_info(f"\n[OK] Certificates generated successfully in {out_dir}!"))
        elif cmd == "ai_setup":
            import re
            model = "qwen2.5-coder:3b"
            if ENV_FILE.exists():
                m = re.search(r'^OLLAMA_MODEL=(.*)$', ENV_FILE.read_text(encoding="utf-8"), re.MULTILINE)
                if m:
                    model = m.group(1).strip()
            print(color_info(f"\n[+] Pulling AI model {model} (this may take a while)..."))
            run(c + ["exec", "ollama", "ollama", "pull", model])
            print(color_info("\n[OK] AI model downloaded successfully!"))
        else:
            print(f"Unknown command: {cmd}")
            return 1
        
        print(f"\n{status_line}")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"\n{status_line}")
        return exc.returncode or 1


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    raise SystemExit(main(sys.argv[1:]))