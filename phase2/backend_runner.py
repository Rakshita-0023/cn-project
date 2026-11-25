"""Launch the preserved Phase 1 backend with an explicit LAN bind address."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.backend_a import serve

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--name", choices=("backend-a", "backend-b"), required=True)
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, required=True)
    a = p.parse_args()
    serve(a.name[-1].upper(), port=a.port, host=a.host, write_pid=False)
