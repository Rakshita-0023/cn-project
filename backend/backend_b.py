#!/usr/bin/env python3
"""Backend B uses the same working HTTP/cache implementation as Backend A."""
import sys

if __package__:
    from .backend_a import serve
else:
    from backend_a import serve


if __name__ == "__main__":
    try:
        serve("B")
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
