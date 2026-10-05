#!/usr/bin/env python3
"""Render Laptop 2's isolated nginx configuration from network.env."""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _common import load_network, nginx_args, render_nginx, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--http2", action="store_true", help="Requires nginx >=1.25.1 with HTTP/2 support")
    parser.add_argument("--check", action="store_true", help="Run nginx -t; requires the matching TLS certificate/key")
    args = parser.parse_args()
    try:
        render_nginx(load_network(), args.http2)
        if args.check:
            run(nginx_args() + ["-t"])
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
