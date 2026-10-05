#!/usr/bin/env python3
"""Shared Phase 1 configuration, process control and checks; standard library.

network.env is parsed as data, never executed. Shell entry points use this one
module to keep validation and paths consistent. Inventory, diagnosis and zip
export are retained from the original project's helper.
"""
import argparse
import datetime
import ipaddress
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"TEAM_NAME", "LAPTOP1_IP", "LAPTOP2_IP", "DNS_IP", "EDGE_IP",
            "BACKEND_A_IP", "BACKEND_A_PORT", "BACKEND_B_IP", "BACKEND_B_PORT",
            "APP_DOMAIN", "API_DOMAIN", "HTTPS_PORT"}
OPTIONAL = {"HTTP_PORT", "DNS_TTL", "UPSTREAM_DNS"}


def ipv4(value, name, private=True):
    try:
        address = ipaddress.IPv4Address(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must contain a usable IPv4 address") from exc
    if (address.is_loopback or address.is_unspecified or address.is_multicast
            or address.is_link_local or address.is_reserved
            or (private and not address.is_private)):
        raise ValueError(f"{name} must be a usable {'private LAN ' if private else ''}IPv4 address")
    return str(address)


def load_network(path=None):
    path = Path(path) if path else ROOT / "network.env"
    if not path.is_file():
        raise ValueError("Run cp network.env.example network.env and edit the actual LAN addresses first")
    values = {}
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path.name}:{number}: expected NAME=value")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if key not in REQUIRED | OPTIONAL or key in values:
            raise ValueError(f"{path.name}:{number}: unknown or duplicate setting {key}")
        parts = shlex.split(raw_value, comments=True, posix=True)
        if len(parts) > 1:
            raise ValueError(f"{path.name}:{number}: quote values containing spaces")
        value = parts[0] if parts else ""
        if any(char in value for char in "$`;|&<>\\\n\r"):
            raise ValueError(f"{path.name}:{number}: shell expressions are not configuration values")
        values[key] = value
    missing = REQUIRED - values.keys()
    if missing:
        raise ValueError("Missing network.env settings: " + ", ".join(sorted(missing)))
    team = values["TEAM_NAME"]
    if not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", team):
        raise ValueError("TEAM_NAME must be a DNS label")
    values["TEAM_NAME"] = team.lower()
    for name in ("APP_DOMAIN", "API_DOMAIN"):
        domain = values[name].lower()
        if (len(domain) > 240 or not domain.endswith(".test")
                or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                           for label in domain.split("."))):
            raise ValueError(f"{name} must be a DNS name under .test")
        values[name] = domain
    if (values["APP_DOMAIN"] != f"app.{values['TEAM_NAME']}.test"
            or values["API_DOMAIN"] != f"api.{values['TEAM_NAME']}.test"):
        raise ValueError("APP_DOMAIN and API_DOMAIN must match TEAM_NAME under .test")
    for name in ("LAPTOP1_IP", "LAPTOP2_IP", "DNS_IP", "EDGE_IP", "BACKEND_A_IP", "BACKEND_B_IP"):
        values[name] = ipv4(values[name], name)
    if values["LAPTOP1_IP"] == values["LAPTOP2_IP"]:
        raise ValueError("The two physical laptops must have distinct LAN addresses")
    for alias, laptop in (("DNS_IP", "LAPTOP1_IP"), ("BACKEND_A_IP", "LAPTOP1_IP"),
                          ("EDGE_IP", "LAPTOP2_IP"), ("BACKEND_B_IP", "LAPTOP2_IP")):
        if values[alias] != values[laptop]:
            raise ValueError(f"{alias} must match {laptop}; replace every occurrence of the example address")
    for name, default in (("BACKEND_A_PORT", 3001), ("BACKEND_B_PORT", 3002),
                          ("HTTPS_PORT", 8443), ("HTTP_PORT", 8080), ("DNS_TTL", 30)):
        raw = str(values.get(name, default))
        if not raw.isdigit() or not 1 <= int(raw) <= 65535:
            raise ValueError(f"{name} must be an integer from 1 to 65535")
        values[name] = int(raw)
    if len({53, values['HTTP_PORT'], values['HTTPS_PORT'], values['BACKEND_A_PORT'], values['BACKEND_B_PORT']}) != 5:
        raise ValueError("DNS, edge and backend ports must not overlap")
    upstreams = values.get("UPSTREAM_DNS", "")
    values["UPSTREAM_DNS"] = [ipv4(item.strip(), "UPSTREAM_DNS", private=False)
                               for item in upstreams.split(",") if item.strip()]
    if any(item in (values["LAPTOP1_IP"], values["LAPTOP2_IP"]) for item in values["UPSTREAM_DNS"]):
        raise ValueError("UPSTREAM_DNS must be an independent resolver, not a project laptop")
    return values


def binary(name):
    found = shutil.which(name)
    if not found and name == "dnsmasq" and shutil.which("brew"):
        prefix = subprocess.check_output(["brew", "--prefix", "dnsmasq"], text=True).strip()
        candidate = Path(prefix) / "sbin/dnsmasq"
        if candidate.is_file():
            found = str(candidate)
    if not found:
        raise ValueError(f"Missing {name}; install the software listed in README.md")
    return found


def run(command, **kwargs):
    print("+ " + shlex.join(map(str, command)), flush=True)
    return subprocess.run(list(map(str, command)), check=True, **kwargs)


def quote_nginx(path):
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$") + '"'


def render_template(file, values):
    text = Path(file).read_text()
    def replace(match):
        key = match.group(1)
        if key not in values:
            raise ValueError(f"Unknown template variable {key}")
        return str(values[key])
    return re.sub(r"\{\{([A-Z_0-9]+)\}\}", replace, text)


def render_dns(config, record_ip=None):
    runtime = ROOT / "dns/runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    generated = ROOT / "dns/generated/dnsmasq.conf"
    generated.parent.mkdir(parents=True, exist_ok=True)
    # Config paths can include spaces; dnsmasq treats the rest of these lines as the filename.
    values = dict(config, ZONE=config['APP_DOMAIN'].split('.', 1)[1],
                  DNS_LOG=str(runtime / "dnsmasq.log"), DNS_PID=str(runtime / "dnsmasq.pid"),
                  UPSTREAM_LINES="\n".join(f"server={ip}" for ip in config["UPSTREAM_DNS"]))
    if record_ip:
        values["EDGE_IP"] = ipv4(record_ip, "record IP")
    generated.write_text(render_template(ROOT / "dns/dnsmasq.conf.template", values))
    print(f"PASS: DNS configuration rendered to {generated}")
    return generated


def render_nginx(config, http2=False):
    runtime = ROOT / "nginx/runtime"
    for directory in (runtime, runtime / "client_temp", runtime / "proxy_temp"):
        directory.mkdir(parents=True, exist_ok=True)
    generated = ROOT / "nginx/generated/nginx.conf"
    generated.parent.mkdir(parents=True, exist_ok=True)
    certs = ROOT / "tls/certs"
    values = dict(config, NGINX_PID=quote_nginx(runtime / "nginx.pid"),
                  ERROR_LOG=quote_nginx(runtime / "error.log"), ACCESS_LOG=quote_nginx(runtime / "access.log"),
                  CLIENT_TEMP=quote_nginx(runtime / "client_temp"), PROXY_TEMP=quote_nginx(runtime / "proxy_temp"),
                  SERVER_CERT=quote_nginx(certs / "server.crt"), SERVER_KEY=quote_nginx(certs / "server.key"),
                  HTTP2_LINE="http2 on;" if http2 else "")
    generated.write_text(render_template(ROOT / "nginx/nginx.conf.template", values))
    print(f"PASS: nginx configuration rendered to {generated}")
    return generated


def generate_certificate(config, local_ca=False):
    certs = ROOT / "tls/certs"
    certs.mkdir(parents=True, exist_ok=True)
    names = ("server.crt", "server.key", "ca.crt", "ca.key")
    if any((certs / name).exists() for name in names):
        raise ValueError("Existing certificate material found; keep it or move it aside explicitly before rotation")
    conf = certs / "openssl.cnf"
    conf.write_text(f'''[req]
prompt = no
distinguished_name = subject
x509_extensions = server
[subject]
CN = {config['APP_DOMAIN']}
[server]
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = DNS:{config['APP_DOMAIN']},DNS:{config['API_DOMAIN']}
''')
    exe = binary("openssl")
    key, cert = certs / "server.key", certs / "server.crt"
    previous_umask = os.umask(0o077)
    created = [conf]
    try:
        if local_ca:
            ca_key, ca_cert, csr = certs / "ca.key", certs / "ca.crt", certs / "server.csr"
            created.extend([ca_key, ca_cert, csr, key, cert, certs / "ca.srl"])
            run([exe, "req", "-x509", "-newkey", "rsa:2048", "-noenc", "-sha256", "-days", "365",
                 "-subj", f"/CN={config['TEAM_NAME']} course CA", "-addext", "basicConstraints=critical,CA:TRUE",
                 "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-keyout", ca_key, "-out", ca_cert])
            run([exe, "req", "-new", "-newkey", "rsa:2048", "-noenc", "-sha256", "-config", conf,
                 "-keyout", key, "-out", csr])
            run([exe, "x509", "-req", "-in", csr, "-CA", ca_cert, "-CAkey", ca_key, "-CAcreateserial",
                 "-days", "90", "-sha256", "-extfile", conf, "-extensions", "server", "-out", cert])
            csr.unlink()
        else:
            created.extend([key, cert])
            run([exe, "req", "-x509", "-newkey", "rsa:2048", "-noenc", "-sha256", "-days", "90",
                 "-config", conf, "-keyout", key, "-out", cert])
        for name in ("server.crt", "ca.crt"):
            if (certs / name).exists():
                (certs / name).chmod(0o644)
        print("PASS: certificate includes both app/api SANs. Trust the public anchor on both clients.")
    except BaseException:
        for file in created:
            file.unlink(missing_ok=True)
        raise
    finally:
        os.umask(previous_umask)


def trust_anchor():
    certs = ROOT / "tls/certs"
    file = certs / "ca.crt" if (certs / "ca.crt").is_file() else certs / "server.crt"
    if not file.is_file():
        raise ValueError("Missing public trust certificate; generate it on Laptop 2 or copy it to this client")
    return file


def trust_certificate():
    if sys.platform != "darwin":
        raise ValueError("Client Keychain trust requires macOS")
    file = trust_anchor()
    run([binary("openssl"), "x509", "-in", file, "-noout", "-subject", "-fingerprint", "-sha256"])
    run(["sudo", "security", "add-trusted-cert", "-d", "-r", "trustRoot",
         "-k", "/Library/Keychains/System.keychain", file])
    print("PASS: trusted the public project certificate in System Keychain")


def wifi_service(service=None):
    if sys.platform != "darwin":
        raise ValueError("Client DNS configuration requires macOS")
    available = subprocess.check_output(["networksetup", "-listallnetworkservices"], text=True).splitlines()[1:]
    if service:
        if service not in available:
            raise ValueError(f"Network service {service!r} is not enabled; run networksetup -listallnetworkservices")
        return service
    order = subprocess.check_output(["networksetup", "-listnetworkserviceorder"], text=True)
    matches, current = [], None
    for line in order.splitlines():
        match = re.match(r"\(\d+\) (.+)$", line)
        if match:
            current = match.group(1)
        elif "Hardware Port: Wi-Fi," in line and current in available:
            matches.append(current)
    if len(matches) != 1:
        raise ValueError("Cannot uniquely detect Wi-Fi; pass --service with the actual active network service name")
    return matches[0]


def previous_dns(service):
    result = subprocess.check_output(["networksetup", "-getdnsservers", service], text=True).strip()
    if result.startswith("There aren't any DNS Servers set on "):
        return []
    addresses = result.splitlines()
    if not addresses:
        raise ValueError("Could not read previous DNS settings")
    for address in addresses:
        ipaddress.ip_address(address)
    return addresses


def set_client_dns(config, service=None, server=None):
    service = wifi_service(service)
    target = ipv4(server, "DNS fault-test server") if server else config["DNS_IP"]
    backup = ROOT / "dns/runtime/client-dns-backup.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    current = previous_dns(service)
    if backup.exists():
        saved = json.loads(backup.read_text())
        if saved.get("service") != service:
            raise ValueError("Restore the outstanding DNS backup before modifying another network service")
        print("Keeping the original DNS backup; repeated setup/fault tests do not overwrite it.")
    else:
        with backup.open("x") as file:
            json.dump({"service": service, "servers": current}, file, indent=2)
        backup.chmod(0o600)
    print(f"Changing {service} DNS: {current or 'automatic / DHCP'} -> {target}", flush=True)
    run(["sudo", "networksetup", "-setdnsservers", service, target])
    print(f"PASS: DNS set; original settings preserved in {backup}")


def restore_client_dns():
    backup = ROOT / "dns/runtime/client-dns-backup.json"
    if not backup.is_file():
        raise ValueError("No saved DNS settings found; nothing was changed")
    saved = json.loads(backup.read_text())
    if set(saved) != {"service", "servers"} or not isinstance(saved['servers'], list):
        raise ValueError("Invalid DNS backup; inspect it instead of changing network settings")
    service = wifi_service(saved["service"])
    for address in saved["servers"]:
        ipaddress.ip_address(address)
    print(f"Restoring {service} DNS to {saved['servers'] or 'automatic / DHCP'}", flush=True)
    run(["sudo", "networksetup", "-setdnsservers", service, *(saved["servers"] or ["Empty"])])
    backup.unlink()
    print("PASS: original DNS settings restored; backup removed only after success")


def service_pid_file(name):
    if name == "dns":
        return ROOT / "dns/runtime/dnsmasq.pid"
    if name == "nginx":
        return ROOT / "nginx/runtime/nginx.pid"
    return ROOT / "backend/runtime" / (name + ".pid")


def owned_pid(name):
    file = service_pid_file(name)
    if not file.is_file():
        return None
    try:
        contents = file.read_text().strip()
        # nginx -t can create an empty PID file without starting a process.
        # A subsequent start must not mistake this for a damaged live PID.
        if name == "nginx" and not contents:
            file.unlink(missing_ok=True)
            return None
        pid = int(contents)
        if pid < 2:
            raise ValueError("invalid PID")
    except FileNotFoundError:
        # The service may remove its own PID while a stop check is reading it.
        return None
    except ValueError as exc:
        raise ValueError(f"Invalid project PID file: {file}") from exc
    result = subprocess.run(["ps", "-p", str(pid), "-o", "command="], text=True, capture_output=True)
    if result.returncode or not result.stdout.strip():
        file.unlink(missing_ok=True)
        return None
    expected = {"dns": "dnsmasq", "nginx": "nginx", "backend-a": "backend_a.py", "backend-b": "backend_b.py"}[name]
    if expected not in result.stdout:
        raise ValueError(f"Refusing to signal unrelated process {pid} referenced by {file}")
    if name in ("dns", "nginx") and str(ROOT / name / "generated") not in result.stdout:
        raise ValueError(f"PID {pid} does not use this project's {name} configuration")
    return pid


def nginx_args():
    config = ROOT / "nginx/generated/nginx.conf"
    if not config.is_file():
        raise ValueError("Run python3 nginx/configure_nginx.py first")
    return [binary("nginx"), "-p", str(ROOT / "nginx/runtime") + "/", "-c", str(config)]


def service(name, action):
    pid = owned_pid(name)
    if action in ("stop", "restart") and pid:
        command = ["kill", "-QUIT" if name == "nginx" else "-TERM", str(pid)]
        if name == "dns" or (name == "nginx" and os.geteuid() != 0
                             and service_pid_file(name).stat().st_uid == 0):
            command.insert(0, "sudo")
        run(command)
        deadline = time.monotonic() + 5
        while owned_pid(name) and time.monotonic() < deadline:
            time.sleep(.1)
        if owned_pid(name):
            raise ValueError(f"{name} has not stopped; keep its PID file and inspect its log")
        print(f"PASS: stopped project {name}")
        pid = None
    if action == "stop":
        if pid is None:
            print(f"PASS: project {name} is stopped")
        return
    if name.startswith("backend"):
        raise ValueError("Start the backend using its backend/start_backend script or Python entry point")
    config = load_network()
    if action == "reload":
        if name != "nginx" or not pid:
            raise ValueError("Project nginx is not running")
        run(nginx_args() + ["-t"])
        command = ["kill", "-HUP", str(pid)]
        if service_pid_file(name).stat().st_uid == 0 and os.geteuid() != 0:
            command.insert(0, "sudo")
        run(command)
        print("PASS: validated and reloaded project nginx")
        return
    if pid:
        print(f"PASS: project {name} already running with PID {pid}")
        return
    if name == "dns":
        file = ROOT / "dns/generated/dnsmasq.conf"
        if not file.is_file():
            raise ValueError("Run python3 dns/configure_dns.py first")
        run([binary("dnsmasq"), "--test", "--conf-file=" + str(file)])
        command = [binary("dnsmasq"), "--conf-file=" + str(file)]
        if os.geteuid() != 0:
            command.insert(0, "sudo")
        run(command)
    else:
        command = nginx_args()
        run(command + ["-t"])
        if min(config["HTTP_PORT"], config["HTTPS_PORT"]) < 1024 and os.geteuid() != 0:
            command.insert(0, "sudo")
        run(command)
    deadline = time.monotonic() + 3
    while not owned_pid(name) and time.monotonic() < deadline:
        time.sleep(.1)
    if not owned_pid(name):
        raise ValueError(f"{name} did not create a running project PID; inspect its runtime log")
    print(f"PASS: project {name} running with PID {owned_pid(name)}")


def curl_args(secure=False):
    command = [binary("curl"), "--noproxy", "*", "--http1.1", "--connect-timeout", "4", "--max-time", "15"]
    if secure:
        command += ["--cacert", str(trust_anchor())]
    return command


def request(url, secure=False, extra=(), show=True):
    result = subprocess.run(curl_args(secure) + ["-sS", "-D", "-", *extra, url],
                            text=True, capture_output=True, timeout=20)
    if result.returncode:
        raise ValueError(f"curl failed ({result.returncode}): {result.stderr.strip()}")
    if show:
        print(result.stdout, end="")
    raw, body = result.stdout.split("\n\n", 1)
    lines = raw.splitlines()
    status = int(lines[0].split()[1])
    headers = {key.lower(): value.strip() for key, value in
               (line.split(":", 1) for line in lines[1:] if ":" in line)}
    return status, headers, body


def app_url(config, path="/api/status", api=False):
    host = config["API_DOMAIN" if api else "APP_DOMAIN"]
    return f"https://{host}:{config['HTTPS_PORT']}{path}"


def expect(value, message):
    if not value:
        raise ValueError(message)


def check(config, name, count=10, wanted="both", strict=False):
    if name == "ping":
        if sys.platform != "darwin":
            raise ValueError("The physical LAN ping check is for macOS; use test_all.sh --local for development")
        interfaces = subprocess.check_output(["ifconfig"], text=True)
        addresses = re.findall(r"\binet\s+(\S+)", interfaces)
        roles = [role for role in (1, 2) if config[f"LAPTOP{role}_IP"] in addresses]
        expect(len(roles) == 1, "This host must have exactly one configured laptop LAN address")
        role = roles[0]
        peer = 2 if role == 1 else 1
        run(["ping", "-c", "3", config[f"LAPTOP{peer}_IP"]])
        print(f"PASS: Laptop {role} -> Laptop {peer}. Run this script on the other laptop for the opposite direction.")
    elif name == "backends":
        for identifier in ("A", "B"):
            ip, port = config[f"BACKEND_{identifier}_IP"], config[f"BACKEND_{identifier}_PORT"]
            for path in ("/", "/api/status"):
                status, headers, body = request(f"http://{ip}:{port}{path}")
                expect(status == 200 and headers.get("x-backend") == identifier,
                       f"Backend {identifier} must return HTTP200 and X-Backend: {identifier}")
                expect(json.loads(body).get("backend") == identifier, "Backend body identifier does not match")
            print(f"PASS: direct Backend {identifier}")
    elif name == "dns":
        for host in (config["APP_DOMAIN"], config["API_DOMAIN"]):
            for transport in ([], ["+tcp"]):
                result = run([binary("dig"), "@" + config["DNS_IP"], host, "A", "+time=2", "+tries=1", *transport],
                             text=True, capture_output=True)
                print(result.stdout)
                rows = [line.split() for line in result.stdout.splitlines() if line.startswith(host + ".")]
                answers = [row[4] for row in rows if len(row) >= 5 and row[3] == "A"]
                expect(answers == [config["EDGE_IP"]], f"{host} must resolve to EDGE_IP")
            print(f"PASS: {host} -> {config['EDGE_IP']} over DNS UDP and TCP")
    elif name == "https":
        for api in (False, True):
            status, headers, _ = request(app_url(config, api=api), secure=True)
            expect(status == 200 and headers.get("x-backend") in ("A", "B"), "Expected a healthy HTTPS backend response")
        print("PASS: trusted HTTPS for both app/api names; hostname/certificate validation enabled")
    elif name == "load-balancing":
        expect(count >= 2, "Use at least two requests")
        seen = []
        for number in range(1, count + 1):
            status, headers, _ = request(app_url(config), secure=True, show=False)
            expect(status == (502 if wanted == "unavailable" else 200), f"Unexpected HTTP {status}")
            identifier = headers.get("x-backend", "unavailable")
            print(f"Request {number}: HTTP {status}, X-Backend: {identifier}")
            seen.append(identifier)
        expected = {"A", "B"} if wanted == "both" else {wanted}
        expect(set(seen) == expected, f"Expected {expected}, observed {set(seen)}")
        if strict and wanted == "both":
            expect(all(a != b for a, b in zip(seen, seen[1:])), "Requests did not strictly alternate; quiet other traffic")
        print(f"PASS: expected backend set {wanted}; actual sequence: {', '.join(seen)}")
    elif name == "caching":
        status, headers, _ = request(app_url(config, "/cache-demo"), secure=True, extra=["-I"])
        expect(status == 200 and headers.get("cache-control") == "public, max-age=60", "Expected Cache-Control on HEAD")
        status, headers, _ = request(app_url(config, "/cache-demo"), secure=True)
        etag = headers.get("etag")
        expect(status == 200 and bool(etag), "Expected cacheable HTTP200 with ETag")
        print(f"Actual ETag: {etag}; sending it unchanged in If-None-Match")
        status, _, body = request(app_url(config, "/cache-demo"), secure=True, extra=["-H", f"If-None-Match: {etag}"])
        expect(status == 304 and not body, "Expected conditional HTTP304 without a response body")
        print("PASS: Cache-Control, ETag and conditional 304 through nginx")
    else:
        raise ValueError(f"Unknown check {name}")


def inventory(laptop, interface=None):
    if sys.platform != "darwin":
        raise ValueError("LAN inventory requires macOS")
    route = subprocess.run(["/sbin/route", "-n", "get", "default"], text=True, capture_output=True)
    if not interface:
        match = re.search(r"interface:\s*(\S+)", route.stdout)
        expect(bool(match), "No default interface; specify --interface with the actual Wi-Fi/LAN device")
        interface = match.group(1)
    detail = subprocess.check_output(["/sbin/ifconfig", interface], text=True)
    address = re.search(r"inet\s+(\S+)\s+netmask\s+(\S+)", detail)
    expect(bool(address), "Chosen interface has no IPv4 address")
    ip, raw_mask = address.groups()
    mask = str(ipaddress.IPv4Address(int(raw_mask, 16))) if raw_mask.startswith("0x") else raw_mask
    mac = re.search(r"ether\s+(\S+)", detail)
    gateway = re.search(r"gateway:\s*(\S+)", route.stdout)
    data = {"observed_at": datetime.datetime.now().astimezone().isoformat(), "laptop": laptop,
            "hostname": socket.gethostname(), "ipv4": ip, "subnet_mask": mask,
            "prefix": ipaddress.IPv4Network(f"{ip}/{mask}", strict=False).prefixlen,
            "interface": interface, "mac_address": mac.group(1) if mac else None,
            "gateway": gateway.group(1) if gateway else None,
            "route_output": route.stdout, "ifconfig_output": detail}
    file = ROOT / f"evidence/lan/inventory-laptop{laptop}.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=2))
    print(f"PASS: actual inventory saved to {file}")


def diagnose(config):
    host = config["APP_DOMAIN"]
    print("1. DNS: direct resolver query, then the actual system resolver")
    result = subprocess.run([binary("dig"), "@" + config["DNS_IP"], host, "+time=2", "+tries=1"],
                            text=True, capture_output=True)
    print(result.stdout + result.stderr)
    print(socket.getaddrinfo(host, config["HTTPS_PORT"], socket.AF_INET, socket.SOCK_STREAM))
    print("2. TCP: actual socket pair")
    with socket.create_connection((host, config["HTTPS_PORT"]), timeout=4) as connection:
        print(connection.getsockname(), "->", connection.getpeername())
    print("3. TLS: SAN, trust and handshake validation")
    result = run([binary("openssl"), "s_client", "-connect", f"{host}:{config['HTTPS_PORT']}",
                  "-servername", host, "-verify_hostname", host, "-verify_return_error",
                  "-CAfile", trust_anchor(), "-brief"], input="", text=True, capture_output=True, timeout=12)
    print(result.stdout + result.stderr)
    print("4. HTTP: upstream result")
    status, _, _ = request(app_url(config), secure=True)
    expect(status == 200, f"DNS/TCP/TLS passed but the application returned HTTP {status}")
    print("PASS: all four layers")


def bundle():
    target = ROOT / "scripts/runtime/cn-project.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for directory, folders, files in os.walk(ROOT):
            folders[:] = sorted(name for name in folders if name not in {".git", "runtime", "generated", "__pycache__"})
            for name in sorted(files):
                file = Path(directory) / name
                relative = file.relative_to(ROOT)
                if (name in {"network.env", ".DS_Store"} or name.endswith((".key", ".pem", ".pyc", ".log", ".pid"))
                        or (relative.parts[:2] == ("tls", "certs") and name != ".gitkeep") or file.is_symlink()):
                    continue
                archive.write(file, Path("cn-project") / relative)
    print(f"PASS: source/evidence zip saved to ignored {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Validate the one editable network.env")
    sub.add_parser("shell-env", help="Emit validated shell variables for source <(...) in documentation")
    tls = sub.add_parser("certificate")
    tls.add_argument("--local-ca", action="store_true", help="Optional local CA route requires assignment faculty approval")
    sub.add_parser("trust")
    change = sub.add_parser("set-dns")
    change.add_argument("--service")
    change.add_argument("--server", help="Actual alternate resolver address for the required wrong-DNS failure")
    sub.add_parser("restore-dns")
    control = sub.add_parser("service")
    control.add_argument("name", choices=("dns", "nginx", "backend-a", "backend-b"))
    control.add_argument("action", choices=("start", "stop", "restart", "reload"))
    verify = sub.add_parser("check")
    verify.add_argument("name", choices=("ping", "backends", "dns", "https", "load-balancing", "caching"))
    verify.add_argument("--count", type=int, default=10)
    verify.add_argument("--expect", choices=("both", "A", "B", "unavailable"), default="both")
    verify.add_argument("--strict", action="store_true")
    inv = sub.add_parser("inventory")
    inv.add_argument("--laptop", type=int, choices=(1, 2), required=True)
    inv.add_argument("--interface")
    sub.add_parser("diagnose")
    sub.add_parser("bundle")
    args = parser.parse_args()
    try:
        if args.command == "service":
            service(args.name, args.action)
        elif args.command == "restore-dns":
            restore_client_dns()
        elif args.command == "trust":
            trust_certificate()
        elif args.command == "inventory":
            inventory(args.laptop, args.interface)
        elif args.command == "bundle":
            bundle()
        else:
            config = load_network()
            if args.command == "shell-env":
                for key, value in config.items():
                    if not isinstance(value, list):
                        print(f"export {key}={shlex.quote(str(value))}")
            elif args.command == "validate":
                print("PASS: network.env is consistent with the two-laptop architecture")
            elif args.command == "certificate":
                generate_certificate(config, args.local_ca)
            elif args.command == "set-dns":
                set_client_dns(config, args.service, args.server)
            elif args.command == "check":
                check(config, args.name, args.count, args.expect, args.strict)
            elif args.command == "diagnose":
                diagnose(config)
        return 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
