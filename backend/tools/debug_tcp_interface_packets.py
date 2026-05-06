#!/usr/bin/env python3

import argparse
import datetime
import socket
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Simple TCP loopback listener that prints any packets it receives. "
            "Intended for debugging the middleware TcpInterface (127.0.0.1:5001)."
        )
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="IP address to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="TCP port to listen on (default: 5001)",
    )
    return parser.parse_args()


def hexdump(data: bytes) -> None:
    """Pretty-print bytes as hex + ASCII."""
    bytes_per_line = 16
    for offset in range(0, len(data), bytes_per_line):
        chunk = data[offset : offset + bytes_per_line]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join((chr(b) if 32 <= b < 127 else ".") for b in chunk)
        print(f"{offset:04X}  {hex_part:<47}  {ascii_part}")


def create_server(host: str, port: int) -> socket.socket:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(1)
    return srv


def accept_client(
    server: socket.socket,
) -> tuple[socket.socket, tuple[str, int]]:
    print("Waiting for TCP connection...")
    client_sock, addr = server.accept()
    print(f"Accepted connection from {addr[0]}:{addr[1]}")
    return client_sock, addr


def main() -> int:
    args = parse_args()

    print(
        f"Starting TCP debug listener on {args.host}:{args.port} "
        "(expecting TcpInterface to connect here)."
    )

    try:
        server = create_server(args.host, args.port)
    except OSError as e:
        print(
            f"Failed to bind to {args.host}:{args.port}: {e}", file=sys.stderr)
        return 1

    try:
        client_sock, _ = accept_client(server)
    except KeyboardInterrupt:
        print("\nInterrupted before client connected.")
        return 0

    with client_sock, server:
        try:
            while True:
                data = client_sock.recv(4096)
                if not data:
                    print("Client closed connection.")
                    break

                timestamp = datetime.datetime.now().isoformat(
                    timespec="milliseconds"
                )
                print(
                    f"[{timestamp}] Received {len(data)} bytes from TcpInterface:"
                )
                hexdump(data)
                print()
        except KeyboardInterrupt:
            print("\nInterrupted by user.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
