"""
Cross-platform Docker helper using only Python built-ins.

Usage:
    python start.py [--prod|--dev] <command> [args]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
NO_SSL_OVERRIDE = REPO_ROOT / "docker" / "docker-compose.nossl.yml"
CERTS_DIR = REPO_ROOT / "certs"
ENV_FILE = REPO_ROOT / ".env"
CLOUDFLARE_CONFIG = REPO_ROOT / "cloudflared" / "config.yml"

# Default SSL certificate filenames (can be overridden via .env)
DEFAULT_SSL_CERT = "_.cyberfortress.local.crt"
DEFAULT_SSL_KEY = "_.cyberfortress.local.key"


def compose_cmd(files: list[Path], use_ssl: bool, use_tunnel: bool) -> list[str]:
    cmd: list[str] = ["docker", "compose", "--project-directory", str(REPO_ROOT)]
    for f in files:
        cmd += ["-f", str(f)]
    if use_ssl:
        cmd += ["--profile", "ssl"]
    if use_tunnel:
        cmd += ["--profile", "tunnel"]
    return cmd


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def call_setup(script_path: Path) -> None:
    run([sys.executable, str(script_path)])


def add_manage_args(base: list[str], extra: list[str]) -> list[str]:
    return base + extra


def color_env_label(environment: str) -> str:
    base = f"[{environment}]"
    if not sys.stdout.isatty():
        return base
    color = "\033[92m" if environment == "prod" else "\033[94m"
    return f"\033[1m{color}{base}\033[0m"


def env_status_lines(environment: str, use_ssl: bool, use_tunnel: bool) -> str:
    label = color_env_label(environment)
    ssl_note = "on" if use_ssl else "off"
    tunnel_note = "on" if use_tunnel else "off"
    return f"{label} SSL/TLS={ssl_note} CloudflareTunnel={tunnel_note}"


def env_access_urls(use_ssl: bool) -> str:
    access_urls = (
        "https://localhost, https://cloudsafe.cyberfortress.local (if you installed Root CA and set hosts)"
        if use_ssl
        else "http://localhost:8080"
    )
    return f"Access: {access_urls}"


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
    parser.add_argument("--prod", action="store_true", help="Use production compose file")
    parser.add_argument("--dev", action="store_true", help="Use development compose file (default)")
    parser.add_argument("--tunnel", action="store_true", help="Enable Cloudflare tunnel profile")
    parser.add_argument("command", nargs="?", help="Command to run")
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="Extra args for manage.py commands")
    args = parser.parse_args(argv)

    compose_file = REPO_ROOT / "docker" / ("docker-compose.prod.yml" if args.prod else "docker-compose.yml")
    env_vars = load_env_file(ENV_FILE)
    
    # Get SSL certificate filenames from .env or use defaults
    ssl_cert_file = env_vars.get("SSL_CERT_FILE", DEFAULT_SSL_CERT)
    ssl_key_file = env_vars.get("SSL_KEY_FILE", DEFAULT_SSL_KEY)
    cert_path = CERTS_DIR / ssl_cert_file
    key_path = CERTS_DIR / ssl_key_file
    
    use_ssl = cert_path.exists() and key_path.exists()
    compose_files = [compose_file] if use_ssl else [compose_file, NO_SSL_OVERRIDE]
    use_tunnel = False
    tunnel_note = ""
    if args.tunnel:
        use_tunnel, tunnel_note = should_enable_tunnel(env_vars)
    elif env_vars.get("CLOUDFLARE_TUNNEL_ID") or env_vars.get("TUNNEL_DOMAIN"):
        tunnel_note = "Cloudflare tunnel disabled (pass --tunnel to enable)."

    if tunnel_note:
        print(color_warning(tunnel_note))

    c = compose_cmd(compose_files, use_ssl, use_tunnel)
    environment = "prod" if args.prod else "dev"
    status_line = env_status_lines(environment, use_ssl, use_tunnel)

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
        elif cmd in {"up"}:
            # print(f"{status_line}\n")
            run(c + ["up", "-d"])
            print(color_info(f"\n[+] Waiting for Vault to start and running Auto-Unseal..."))
            try:
                run(c + ["exec", "web", "python", "vault_manager.py"])
            except subprocess.CalledProcessError:
                print(color_warning("Could not run vault_manager.py. The web container might still be starting."))
            print(color_info(f"\n[OK] Services started.\n"))
            print(color_info(f"{env_access_urls(use_ssl)}"))
        elif cmd in {"down"}:
            # print(f"{status_line}\n")
            run(c + ["down"])
            print("[OK] Services stopped.")
        elif cmd == "restart":
            # print(f"{status_line}\n")
            run(c + ["restart"])
            print("[OK] Services restarted.")
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
            run(c + ["exec", "web", "python", "vault_manager.py"])
            print(color_info("\n[1/4] Running database migrations..."))
            run(add_manage_args(c + ["exec", "web", "python", "manage.py", "migrate"], []))
            print(color_info("\n[2/4] Initializing superuser..."))
            run(c + ["exec", "web", "python", "init_data.py"])
            print(color_info("\n[3/4] Seeding default ABAC policies..."))
            run(add_manage_args(c + ["exec", "web", "python", "manage.py", "seed_policies"], []))
            print(color_info("\n[4/4] Seeding test users & ABAC attributes..."))
            run(add_manage_args(c + ["exec", "web", "python", "manage.py", "seed_test_data"], []))
            print(color_info("\n[OK] Initialization complete!"))
        elif cmd == "initsettings":
            # print(f"{status_line}\n")
            run(add_manage_args(c + ["exec", "web", "python", "manage.py", "init_settings"], extra))
        elif cmd == "createsuperuser":
            # print(f"{status_line}\n")
            run(c + ["exec", "web", "python", "manage.py", "createsuperuser"])
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
            run(compose_cmd(compose_files, use_ssl, use_tunnel) + ["down", "-v"])
            run(compose_cmd(compose_files, use_ssl, use_tunnel) + ["build", "--no-cache"])
            run(compose_cmd(compose_files, use_ssl, use_tunnel) + ["up", "-d"])
            print(color_info(f"\n[+] Waiting for Vault to start and running Auto-Unseal..."))
            try:
                run(c + ["exec", "web", "python", "vault_manager.py"])
            except subprocess.CalledProcessError:
                print(color_warning("Could not run vault_manager.py. The web container might still be starting."))
            print(f"[OK] Rebuilt and started services.\n")
            print(f"{env_access_urls(use_ssl)}")
        elif cmd == "help":
            print(color_info("Crypto Access Management System"))
            print("─" * 50)
            print(color_info("Usage: python start.py [--prod|--dev] <command> [args]\n"))
            print(color_info("Commands:"))
            print("  setup           Setup environment (.env, certs, Root CA)")
            print("  build           Build Docker images (pull first in prod)")
            print("  up              Start all services")
            print("  down            Stop all services")
            print("  restart         Restart all services")
            print("  logs            Follow logs")
            print("  makemigrations  Create new migrations (passes extra args)")
            print("  migrate         Run database migrations (passes extra args)")
            print("  initsettings    Initialize dynamic system settings")
            print("  initdata        Initialize sample data")
            print("  createsuperuser Create Django superuser")
            print("  shell           Open Django shell")
            print("  collectstatic   Collect static files")
            print("  clean           Remove containers and volumes, prune system")
            print("  rebuild         Clean rebuild and start\n")
            print(color_info("Examples:"))
            print("  python start.py setup")
            print("  python start.py build")
            print("  python start.py up")
            print("  python start.py --prod up")
            print("  python start.py migrate -- app_label")
        else:
            print(f"Unknown command: {cmd}")
            return 1
        
        print(f"\n{status_line}")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"\n{status_line}")
        return exc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))