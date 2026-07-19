"""
UDP IPv6-to-IPv4 Relay for Docker Desktop on Windows.

Docker Desktop for Windows does NOT support IPv6 UDP port forwarding.
This script bridges the gap by:
  1. Listening on the host's public IPv6 address for UDP packets
  2. Forwarding them to 127.0.0.1 (Docker's IPv4 mapped port)
  3. Relaying responses back to the original IPv6 client

Usage:
    python udp6_relay.py                                        # Auto-detect IPv6 address
    python udp6_relay.py --bind 2405:4802:a3fa:28c0::1          # Bind specific address
    python udp6_relay.py --ports 1194                           # Relay only port 1194
"""

import argparse
import socket
import select
import threading
import sys
import signal
import time

BUFFER_SIZE = 65535
CLIENT_TIMEOUT = 300  # 5 minutes idle timeout for NAT mappings


def detect_public_ipv6() -> str | None:
    """Detect the host's public (global) IPv6 address."""
    try:
        # Create a UDP6 socket and connect to a public IPv6 DNS server
        # This doesn't actually send data, just determines the source address
        s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        s.connect(("2001:4860:4860::8888", 80))  # Google DNS IPv6
        addr = s.getsockname()[0]
        s.close()
        # Filter out link-local and loopback
        if addr.startswith("fe80") or addr == "::1":
            return None
        return addr
    except Exception:
        return None


def get_all_ipv6_addresses() -> list[str]:
    """Get all global IPv6 addresses from all interfaces."""
    addrs = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET6):
            addr = info[4][0]
            if not addr.startswith("fe80") and addr != "::1" and "%" not in addr:
                addrs.append(addr)
    except Exception:
        pass
    return list(set(addrs))


class UDPRelay:
    """Relay UDP packets from IPv6 to IPv4 (localhost) for a single port."""

    def __init__(self, bind_addr: str, port: int, forward_port: int | None = None):
        self.bind_addr = bind_addr
        self.port = port
        self.forward_port = forward_port or port
        self.running = False
        # Map: (client_ipv6_addr) -> (ipv4_socket, last_activity)
        self.client_map: dict[tuple, tuple[socket.socket, float]] = {}
        self.lock = threading.Lock()

        # IPv6 listener
        self.ipv6_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.ipv6_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ipv6_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        self.ipv6_sock.bind((bind_addr, port))
        self.ipv6_sock.setblocking(False)

    def _get_or_create_v4_sock(self, client_addr: tuple) -> socket.socket:
        """Get existing or create new IPv4 socket to forward to Docker."""
        with self.lock:
            if client_addr in self.client_map:
                sock, _ = self.client_map[client_addr]
                self.client_map[client_addr] = (sock, time.time())
                return sock

            print(f"  [+] New client connected: {client_addr}", flush=True)
            # Create new IPv4 socket to forward to Docker
            v4_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            v4_sock.setblocking(False)
            self.client_map[client_addr] = (v4_sock, time.time())
            return v4_sock

    def _cleanup_stale(self):
        """Remove stale client mappings."""
        with self.lock:
            now = time.time()
            stale = [
                addr
                for addr, (_, last) in self.client_map.items()
                if now - last > CLIENT_TIMEOUT
            ]
            for addr in stale:
                sock, _ = self.client_map.pop(addr)
                try:
                    sock.close()
                except Exception:
                    pass

    def run(self):
        """Main relay loop."""
        self.running = True
        last_cleanup = time.time()

        while self.running:
            try:
                with self.lock:
                    v4_socks = {sock: addr for addr, (sock, _) in self.client_map.items()}
                
                readers = [self.ipv6_sock] + list(v4_socks.keys())
                ready, _, _ = select.select(readers, [], [], 1.0)

                for sock in ready:
                    if sock is self.ipv6_sock:
                        # Client -> Server
                        try:
                            data, client_addr = self.ipv6_sock.recvfrom(BUFFER_SIZE)
                            if data:
                                v4_sock = self._get_or_create_v4_sock(client_addr)
                                v4_sock.sendto(data, ("127.0.0.1", self.forward_port))
                        except Exception:
                            pass
                    else:
                        # Server -> Client
                        client_addr = v4_socks.get(sock)
                        if not client_addr:
                            continue
                        try:
                            data, _ = sock.recvfrom(BUFFER_SIZE)
                            if data:
                                self.ipv6_sock.sendto(data, client_addr)
                                with self.lock:
                                    if client_addr in self.client_map:
                                        self.client_map[client_addr] = (sock, time.time())
                        except Exception:
                            pass

                # Periodic cleanup
                if time.time() - last_cleanup > 60:
                    self._cleanup_stale()
                    last_cleanup = time.time()

            except Exception as e:
                if self.running:
                    continue
                break

    def stop(self):
        self.running = False
        try:
            self.ipv6_sock.close()
        except Exception:
            pass
        with self.lock:
            for sock, _ in self.client_map.values():
                try:
                    sock.close()
                except Exception:
                    pass
            self.client_map.clear()


def main():
    parser = argparse.ArgumentParser(
        description="UDP IPv6-to-IPv4 Relay for Docker Desktop (Windows)"
    )
    parser.add_argument(
        "--ports",
        type=int,
        nargs="+",
        default=[53, 443],
        help="IPv6 UDP ports to listen on (default: 53 443)",
    )
    parser.add_argument(
        "--forward-ports",
        type=int,
        nargs="+",
        default=None,
        help="IPv4 ports to forward to on localhost (default: same as --ports). "
             "Must match --ports count. E.g. --ports 53 443 --forward-ports 1194 1195",
    )
    parser.add_argument(
        "--log",
        type=str,
        default=None,
        help="Path to log file to write output to",
    )
    parser.add_argument(
        "--bind",
        type=str,
        default="::",
        help="IPv6 address to bind to (default: :: = all IPv6 addresses)",
    )
    args = parser.parse_args()

    if args.log:
        log_file = open(args.log, "w")
        sys.stdout = log_file
        sys.stderr = log_file

    # Build port mapping
    forward_ports = args.forward_ports if args.forward_ports is not None else [1194, 1195]
    if len(forward_ports) != len(args.ports):
        print("  [!] --ports and --forward-ports must have the same number of entries.")
        return 1
    port_map = list(zip(args.ports, forward_ports))

    bind_addr = args.bind

    print("=" * 55)
    print("  UDP6 Relay for Docker Desktop (Windows)")
    print("=" * 55)
    print(f"  Bind address: {bind_addr}")
    print(f"  Relaying IPv6 UDP -> IPv4 localhost (Docker)")
    for listen_port, fwd_port in port_map:
        print(f"    [{bind_addr}]:{listen_port}  -->  127.0.0.1:{fwd_port}")
    print(f"\n  Press Ctrl+C to stop.\n")

    relays: list[UDPRelay] = []
    threads: list[threading.Thread] = []

    for listen_port, fwd_port in port_map:
        try:
            relay = UDPRelay(bind_addr, listen_port, fwd_port)
            relays.append(relay)
            t = threading.Thread(target=relay.run, daemon=True)
            threads.append(t)
            t.start()
            print(f"  [OK] Listening on [{bind_addr}]:{listen_port}/udp6 -> 127.0.0.1:{fwd_port}", flush=True)
        except OSError as e:
            print(f"  [FAIL] Port {listen_port}: {e}", flush=True)
            if "10013" in str(e) or "10048" in str(e):
                print(f"         Port may be in use or blocked.", flush=True)

    if not relays:
        print("\n  [!] No ports could be bound. Exiting.")
        return 1

    print(f"\n  Relay is running...\n")

    # Wait for Ctrl+C
    def signal_handler(sig, frame):
        print("\n  [*] Shutting down relay...")
        for r in relays:
            r.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

    return 0


if __name__ == "__main__":
    sys.exit(main())
