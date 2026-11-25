#!/usr/bin/env python3
"""Inspect exactly the Git index for public-submission risks, without printing secrets."""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    ('private-key', rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    ('github-token', rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})'),
    ('pf-enable-reference', rb'(?:Token\s*:\s*|pfctl\s+-X\s+)\d{10,}'),
    ('aws-access-id', rb'AKIA[0-9A-Z]{16}'),
]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--history', action='store_true', help='Also inspect historical blobs without rewriting history')
    a = p.parse_args()
    files = [s.decode() for s in git('ls-files', '-z').split(b'\0') if s]
    findings = []
    total = 0
    for name in files:
        path = Path(name)
        if (path.name in {'network.env', '.env', '.DS_Store'} or
            (path.name.startswith('network.env.') and path.name != 'network.env.example') or
            path.suffix.lower() in {'.key', '.pem', '.p12', '.pfx', '.pid', '.pyc', '.keychain', '.keychain-db', '.zip'} or
            any(s in {'.git', '__pycache__', 'runtime', 'generated', 'tmp', '.venv', 'venv', 'node_modules', 'submission'} for s in path.parts)):
            findings.append({'path': name, 'type': 'private-or-runtime-path'})
        data = git('show', ':' + name)
        total += len(data)
        if len(data) > 5 * 1024 * 1024:
            findings.append({'path': name, 'type': 'large-file-needs-review'})
        for label, pattern in PATTERNS:
            if re.search(pattern, data):
                findings.append({'path': name, 'type': label})
        if name.endswith('.pcap'):
            findings.append({'path': name, 'type': 'raw-pcap-requires-filtering-review'})
    history_count = 0
    if a.history:
        for row in git('rev-list', '--objects', '--all').decode().splitlines():
            oid, _, name = row.partition(' ')
            if git('cat-file', '-t', oid).strip() != b'blob':
                continue
            history_count += 1
            data = git('cat-file', 'blob', oid)
            for label, pattern in PATTERNS:
                if re.search(pattern, data):
                    findings.append({'object': oid, 'path': name, 'type': 'historical-' + label})
    print(json.dumps({'index_files_checked': len(files), 'index_bytes': total,
                      'historical_blobs_checked': history_count, 'findings': findings,
                      'scope': 'pattern/path audit plus separately reviewed image/capture provenance'}, indent=2))
    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
