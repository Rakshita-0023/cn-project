#!/usr/bin/env python3
"""Render Laptop 1's dnsmasq configuration from the sole network.env file."""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _common import binary, load_network, render_dns, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--record-laptop", type=int, choices=(1, 2), help="Controlled wrong-record demonstration; default Laptop 2")
    target.add_argument("--record-ip", help="Actual private LAN destination for the wrong-record demonstration")
    parser.add_argument("--check", action="store_true", help="Also run dnsmasq syntax validation without starting it")
    args = parser.parse_args()
    try:
        config = load_network()
        target_ip = config[f"LAPTOP{args.record_laptop}_IP"] if args.record_laptop else args.record_ip
        file = render_dns(config, target_ip)
        if args.check:
            run([binary("dnsmasq"), "--test", "--conf-file=" + str(file)])
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
