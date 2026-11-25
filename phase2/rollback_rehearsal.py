#!/usr/bin/env python3
"""Live empty-anchor rehearsal: no traffic rules and no PF enable/disable."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2 import firewall, config

if __name__ == '__main__':
    c=config.load()
    if firewall.STATE.exists():
        raise SystemExit('Outstanding rollback record: restore the previous installation first')
    before=firewall.pf('-sr')
    current=firewall.pf('-a',firewall.ANCHOR,'-sr')
    if any(line.startswith(('pass ','block ','anchor ')) for line in current.splitlines()):
        raise SystemExit('Project anchor already populated; refusing to replace it')
    # Load an EMPTY anchor, exercise the actual privileged rollback routine,
    # and confirm no change to root rules. PF is never enabled by this rehearsal.
    firewall.pf('-a',firewall.ANCHOR,'-f','/dev/null')
    firewall.STATE.parent.mkdir(parents=True,exist_ok=True)
    firewall.STATE.write_text(json.dumps({'anchor':firewall.ANCHOR,'token':None}))
    firewall.STATE.chmod(0o600)
    firewall.rollback()
    after=firewall.pf('-sr')
    remaining=firewall.pf('-a',firewall.ANCHOR,'-sr')
    if before != after or any(line.startswith(('pass ','block ','anchor ')) for line in remaining.splitlines()):
        raise SystemExit('Rollback rehearsal verification failed; do not install policy')
    marker=config.ROOT/'phase2/runtime/rollback-rehearsal.json'
    marker.write_text(json.dumps({'rules_sha256':hashlib.sha256(firewall.rules(c).encode()).hexdigest(),'root_rules_unchanged':True},indent=2))
    print('PASS: actual privileged anchor rollback rehearsed; root rules unchanged. PF enable-token release remains unit-tested, not exercised by this empty-anchor rehearsal.')
