"""Validated configuration, generated configuration snapshots and role mapping."""
import datetime
import hashlib
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import _common as common


def load(path=None):
    c = common.load_network(path)
    for key, reference in (("DNS_BACKUP_IP", "LAPTOP2_IP"), ("STANDBY_EDGE_IP", "LAPTOP1_IP")):
        c.setdefault(key, c[reference])
        if c[key] != c[reference]:
            raise ValueError(f"{key} must equal {reference} in the two-Mac topology")
    c.setdefault("LAN_INTERFACE", "en0")
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9]{0,14}", c["LAN_INTERFACE"]):
        raise ValueError("LAN_INTERFACE must be an interface name such as en0")
    c.setdefault("EDGE_USER", "_www")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", c["EDGE_USER"]):
        raise ValueError("Invalid dedicated EDGE_USER")
    c.setdefault("FAIL_TIMEOUT", "5")
    if not str(c["FAIL_TIMEOUT"]).isdigit() or not 1 <= int(c["FAIL_TIMEOUT"]) <= 60:
        raise ValueError("FAIL_TIMEOUT must be 1..60 seconds")
    c["FAIL_TIMEOUT"] = int(c["FAIL_TIMEOUT"])
    return c


def local_role(c):
    if sys.platform != "darwin":
        raise ValueError("Live deployment requires macOS; use make test-local on other hosts")
    addresses = re.findall(r"\binet\s+(\S+)", subprocess.check_output(["ifconfig"], text=True))
    roles = [n for n in (1, 2) if c[f"LAPTOP{n}_IP"] in addresses]
    if len(roles) != 1:
        raise ValueError("Current LAN IP does not match exactly one laptop in network.env; regenerate the inventory/config")
    return roles[0]


def services(role):
    return ("dns-primary", "backend-a", "edge-standby") if role == 1 else ("dns-backup", "backend-b", "edge-primary")


def record_state(c):
    file = ROOT / "phase2/runtime/record.json"
    state = json.loads(file.read_text()) if file.exists() else {"target": "primary", "ttl": c["DNS_TTL"]}
    if set(state) != {"target", "ttl"} or state["target"] not in ("primary", "standby"):
        raise ValueError("Invalid record state; inspect phase2/runtime/record.json")
    if type(state["ttl"]) is not int or not 1 <= state["ttl"] <= 65535:
        raise ValueError("Record TTL must be 1..65535 seconds")
    return state


def record_ip(c, state):
    return c["EDGE_IP"] if state["target"] == "primary" else c["STANDBY_EDGE_IP"]


def runtime(name):
    # nginx workers cannot traverse a private home/Downloads directory. Only its
    # temp paths/logs live here; root master reads certificates from the repo.
    return Path("/private/tmp" if sys.platform == "darwin" else "/tmp") / f"cn-phase2-{os.getuid()}" / name


def snapshot_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == content:
        return
    if path.exists():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        backup = ROOT / "phase2/runtime/config-backups" / f"{path.parent.name}-{path.name}-{digest}"
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(path, backup)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content)
    temporary.replace(path)


def generated(name):
    return ROOT / "phase2/generated" / name / ("dnsmasq.conf" if name.startswith("dns-") else "nginx.conf")


def render(c, name, state=None):
    state = state or record_state(c)
    r = runtime(name)
    r.mkdir(parents=True, exist_ok=True)
    r.parent.chmod(0o755)
    r.chmod(0o755)
    if name.startswith("dns-"):
        ip = c["DNS_IP"] if name == "dns-primary" else c["DNS_BACKUP_IP"]
        values = dict(c, DNS_LISTEN=ip, RECORD_IP=record_ip(c, state), TTL=state["ttl"],
                      ZONE=c["APP_DOMAIN"].split(".", 1)[1], DNS_PID=r / "service.pid", DNS_LOG=r / "dns.log",
                      UPSTREAM_LINES="\n".join(f"server={ip}" for ip in c["UPSTREAM_DNS"]))
        template = ROOT / "phase2/templates/dnsmasq.conf.template"
    else:
        for directory in (r / "client_temp", r / "proxy_temp"):
            directory.mkdir(exist_ok=True)
        ip = c["EDGE_IP"] if name == "edge-primary" else c["STANDBY_EDGE_IP"]
        values = dict(c, EDGE_LISTEN=ip, EDGE_LABEL=name, RUNTIME=common.quote_nginx(r),
                      NGINX_PID=common.quote_nginx(r / "service.pid"),
                      ERROR_LOG=common.quote_nginx(r / "error.log"), ACCESS_LOG=common.quote_nginx(r / "access.log"),
                      CLIENT_TEMP=common.quote_nginx(r / "client_temp"), PROXY_TEMP=common.quote_nginx(r / "proxy_temp"),
                      SERVER_CERT=common.quote_nginx(ROOT / "phase2/tls" / name / "server.crt"),
                      SERVER_KEY=common.quote_nginx(ROOT / "phase2/tls" / name / "server.key"))
        template = ROOT / "phase2/templates/nginx.conf.template"
    output = generated(name)
    snapshot_write(output, common.render_template(template, values))
    return output


def worker_uid(c):
    user = pwd.getpwnam(c["EDGE_USER"])
    if user.pw_uid in (0, os.getuid()):
        raise ValueError("EDGE_USER must be a dedicated non-root identity, different from the client user")
    return user.pw_uid


def init(role, peer_ip, interface=None, output=None):
    peer_ip = common.ipv4(peer_ip, "peer IP")
    if not interface:
        route = subprocess.check_output(["route", "-n", "get", "default"], text=True)
        match = re.search(r"interface:\s+(\S+)", route)
        if not match:
            raise ValueError("Cannot detect interface; specify --interface")
        interface = match.group(1)
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9]{0,14}", interface):
        raise ValueError("Invalid interface")
    own_ip = common.ipv4(subprocess.check_output(["ipconfig", "getifaddr", interface], text=True).strip(), "own LAN IP")
    if own_ip == peer_ip:
        raise ValueError("Peer IP must differ from this Mac")
    ips = {role: own_ip, 3 - role: peer_ip}
    text = (ROOT / "network.env.example").read_text().replace("192.168.1.10", ips[1]).replace("192.168.1.20", ips[2])
    text = text.replace("team1", "codexers")
    text += f"\nDNS_BACKUP_IP={ips[2]}\nSTANDBY_EDGE_IP={ips[1]}\nLAN_INTERFACE={interface}\nEDGE_USER=_www\nFAIL_TIMEOUT=5\n"
    file = Path(output) if output else ROOT / "network.env"
    with file.open("x") as stream:
        stream.write(text)
    load(file)
    print(f"Created {file}; review current IPs before starting services. Existing files are never overwritten.")
