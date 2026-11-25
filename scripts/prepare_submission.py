#!/usr/bin/env python3
"""Build a review submission from existing artifacts; never operate live services."""
import datetime
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {'.git', '__pycache__', 'runtime', 'generated', 'tmp', '.venv', 'node_modules', 'originals'}
EXCLUDED_SUFFIXES = {'.key', '.pem', '.p12', '.pfx', '.pyc', '.pid', '.log'}
EXCLUDED_FILES = {'evidence/wireshark/tls-background-traffic.png', 'evidence/phase2/pcaps/dns-tcp-tls.pcap'}


def main():
    stamp = datetime.datetime.now().astimezone().strftime('%Y%m%d-%H%M%S')
    base = ROOT / 'submission'
    base.mkdir(exist_ok=True)
    dest = base / ('cn-project-phase2-' + stamp)
    dest.mkdir()  # Never overwrite an earlier submission tree.
    included, exclusions = [], []
    candidates = []
    for folder in ('backend', 'dns', 'nginx', 'tls', 'scripts', 'phase2', 'docs', 'evidence', 'wireshark'):
        candidates.extend((ROOT / folder).rglob('*'))
    candidates.extend(ROOT / name for name in ('README.md', 'ARCHITECTURE.md', 'Makefile', 'SUBMISSION_CHECKLIST.md', 'network.env.example', '.gitignore', 'output/pdf/phase2-final-report.pdf'))
    for src in sorted(set(candidates)):
        rel = src.relative_to(ROOT)
        if not src.is_file() or src.is_symlink():
            continue
        reason = None
        if any(p in EXCLUDED_DIRS for p in rel.parts) or rel.parts[:2] in [('phase2', 'tls'), ('tls', 'certs')]:
            reason = 'runtime/generated/private material or superseded originals retained in repository'
        elif src.suffix.lower() in EXCLUDED_SUFFIXES or src.name in {'network.env', '.DS_Store', '.env'}:
            reason = 'private/runtime/unnecessary file'
        elif str(rel) in EXCLUDED_FILES:
            reason = 'partial capture or unrelated background traffic; retained in repository, excluded from clean submission'
        if reason:
            exclusions.append({'path':str(rel),'reason':reason})
            continue
        data = src.read_bytes()
        for marker in (b'-----BEGIN '+b'PRIVATE KEY-----', b'-----BEGIN RSA '+b'PRIVATE KEY-----', b'-----BEGIN EC '+b'PRIVATE KEY-----'):
            if marker in data:
                raise ValueError('Private key marker detected in '+str(rel))
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        included.append(str(rel))
    (dest/'SUBMISSION_README.md').write_text('''# Phase 2 submission for review\n\nStart with SUBMISSION_CHECKLIST.md. This package is NOT fully acceptance-ready:\nlatest safe acceptance is FAIL; peer inventory/reciprocal tests, several live\nPhase 1 failure demonstrations and faculty F remain outstanding. Historical\nsuccesses are preserved with timestamps. No secrets/runtime state are included.\n\nSection 9 mapping: docs/phase2/ARCHITECTURE.md + architecture.svg/png;\ndocs/phase2/CONFIGURATION_BUNDLE.md + templates/current-configuration;\nbackend/ + phase2/ + scripts/ + Makefile; evidence/phase2/exports/README.md;\ndocs/phase2/FINAL_REPORT.md + output/pdf/phase2-final-report.pdf;\ndocs/phase2/DEMO.md (11 steps) + VIVA.md.\n\nThe clean pcapng is the packet artifact. Partial pcap, unrelated background\nTLS screenshot and superseded original DNS image remain in the source repository\nand are listed in EXCLUSIONS.json, not submitted as complete evidence. Some\nhistorical audit records mention them to explain integrity limitations.\nScreenshots/exports are in evidence/, not appended as report screenshot pages.\n\nRegenerate a reviewed PDF using phase2/build_report.py (ReportLab required),\nthen `make submission` to create a NEW dated submission directory and ZIP.\nThis does not deploy or restart anything. Do not replace live network.env or\nprivate keys from a package: those files are intentionally excluded.\n''')
    (dest/'EXCLUSIONS.json').write_text(json.dumps(exclusions,indent=2)+'\n')
    lines = []
    for file in sorted(dest.rglob('*')):
        if file.is_file():
            lines.append(hashlib.sha256(file.read_bytes()).hexdigest()+'  '+str(file.relative_to(dest)))
    (dest/'MANIFEST.sha256').write_text('\n'.join(lines)+'\n')
    out = ROOT/'output/submission/cn-project-phase2-submission.zip'
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(dest.rglob('*')):
            if file.is_file(): archive.write(file,Path(dest.name)/file.relative_to(dest))
    with zipfile.ZipFile(out) as archive:
        assert archive.testzip() is None
        assert not any(Path(n).suffix.lower() in EXCLUDED_SUFFIXES or Path(n).name in {'network.env','.env'} for n in archive.namelist())
    digest=hashlib.sha256(out.read_bytes()).hexdigest()
    Path(str(out)+'.sha256').write_text(digest+'  '+out.name+'\n')
    meta={'directory':str(dest.relative_to(ROOT)),'zip':str(out.relative_to(ROOT)),'sha256':digest,'file_count':len(lines)+1,'readiness':'NOT FULLY READY - see SUBMISSION_CHECKLIST.md'}
    (base/'build.json').write_text(json.dumps(meta,indent=2)+'\n')
    (base/'README.md').write_text('# Submission directory\n\nLatest reviewed package: ['+dest.name+']('+dest.name+'/SUBMISSION_README.md).\n\nReadiness: NOT FULLY READY; see the root SUBMISSION_CHECKLIST.md.\nFile hashes are in the package MANIFEST.sha256; ZIP digest is adjacent to ZIP.\nEarlier generated trees are preserved on later runs.\n')
    print(json.dumps(meta,indent=2))

if __name__ == '__main__':
    main()
