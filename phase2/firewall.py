"""Narrow macOS PF anchor. Never reload/flush the global ruleset or states."""
import json
import hashlib
import os
import re
import subprocess
import sys

from .config import ROOT, common, snapshot_write, worker_uid
from .services import admin

ANCHOR = "com.apple/cn-phase2"
STATE = ROOT / "phase2/runtime/pf-state.json"
RULES = ROOT / "phase2/generated/backend-isolation.pf"


def rules(c):
    uid = worker_uid(c)
    return f'''# Both Macs must apply this anchor. Only dedicated nginx workers open backend sockets.
# The root dispatcher must already include anchor "com.apple/*"; no root rules are replaced.
table <cn_edges> const {{ {c['LAPTOP1_IP']}, {c['LAPTOP2_IP']} }}
table <cn_backends> const {{ {c['BACKEND_A_IP']}, {c['BACKEND_B_IP']} }}
pass out quick inet proto tcp from any to <cn_backends> port {{ {c['BACKEND_A_PORT']}, {c['BACKEND_B_PORT']} }} user {uid} flags S/SA keep state
block return out quick inet proto tcp from any to <cn_backends> port {{ {c['BACKEND_A_PORT']}, {c['BACKEND_B_PORT']} }}
pass in quick inet proto tcp from <cn_edges> to <cn_backends> port {{ {c['BACKEND_A_PORT']}, {c['BACKEND_B_PORT']} }} flags S/SA keep state
block return in quick inet proto tcp from any to <cn_backends> port {{ {c['BACKEND_A_PORT']}, {c['BACKEND_B_PORT']} }}
'''


def pf(*args):
    result = subprocess.run(admin(["/sbin/pfctl", *args]), capture_output=True, text=True, timeout=20)
    print("+ pfctl " + " ".join(map(str, args)))
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    if result.returncode:
        raise ValueError(f"pfctl failed with exit {result.returncode}; global rules were not rewritten")
    return result.stdout + result.stderr


def render(c):
    snapshot_write(RULES, rules(c))
    print(f"Rendered {RULES}")
    return RULES


def apply(c):
    if sys.platform != "darwin":
        raise ValueError("PF requires macOS")
    if STATE.exists():
        raise ValueError("A PF rollback record already exists; run firewall rollback before reapplying")
    render(c)
    pf("-n", "-a", ANCHOR, "-f", str(RULES))
    root = pf("-sr")
    if not re.search(r'anchor\s+"com\.apple/\*"', root):
        raise ValueError('Active root rules lack anchor "com.apple/*". Refusing to replace institutional/global PF configuration.')
    interfaces = pf("-s", "Interfaces", "-v")
    # Skip flags bypass every anchor. Require that loopback is filtered.
    if re.search(r"lo0\b[^\n]*\bskip\b|lo0[^\n]*\n[^\n]*\bskip\b", interfaces, re.I):
        raise ValueError("lo0 is skipped by PF: local clients would bypass UID isolation; ask faculty to review that setting")
    previous = pf("-a", ANCHOR, "-sr")
    if previous.strip() and any(line.startswith(("pass ", "block ", "anchor ")) for line in previous.splitlines()):
        raise ValueError("The project anchor is already populated without a rollback record; refusing to overwrite it")
    marker = ROOT / "phase2/runtime/rollback-rehearsal.json"
    if not marker.exists() or json.loads(marker.read_text()).get("rules_sha256") != hashlib.sha256(rules(c).encode()).hexdigest():
        raise ValueError("Run python3 phase2/rollback_rehearsal.py successfully on THIS Mac before applying this configuration")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = {"anchor": ANCHOR, "token": None}
    STATE.write_text(json.dumps(state, indent=2))
    STATE.chmod(0o600)
    (STATE.parent / "pf-root-before.txt").write_text(root)
    try:
        pf("-a", ANCHOR, "-f", str(RULES))
        output = pf("-E")
        match = re.search(r"Token\s*:\s*(\d+)", output, re.I)
        if not match:
            raise ValueError("PF did not return an enable-reference token; inspect the logged output before releasing any PF reference")
        state["token"] = match.group(1)
        STATE.write_text(json.dumps(state, indent=2))
    except BaseException:
        # Keep the record if rollback itself fails.
        rollback()
        raise
    print("PF anchor applied. Restart project backends to discard old backend TCP connections, then run test isolation on BOTH Macs.")
    print("Existing PF states are intentionally preserved. Do not call isolation verified until fresh direct requests fail and both edges still reach A/B.")


def rollback():
    if not STATE.exists():
        print("No project PF changes recorded; nothing to roll back")
        return
    state = json.loads(STATE.read_text())
    if state.get("anchor") != ANCHOR or (state.get("token") is not None and not re.fullmatch(r"\d+", state["token"])):
        raise ValueError("Invalid PF rollback record; no rules changed")
    pf("-a", ANCHOR, "-F", "rules")
    pf("-a", ANCHOR, "-F", "Tables")
    if state.get("token"):
        pf("-X", state["token"])
    STATE.unlink()
    print("PASS: removed only project rules/tables and released only the project's PF enable reference")
