"""Live checks with bounded timeouts and explicit assertions; no synthetic results."""
import json
import re
import socket
import ssl
import subprocess
import sys
import time

from .config import common, record_ip, record_state
from .tls import anchor


def system_addresses(c):
    # Bound native resolver calls as well as TCP/TLS calls. getaddrinfo itself
    # has no Python socket timeout and may otherwise stall on a dead resolver.
    code = "import json,socket,sys; print(json.dumps(sorted({r[4][0] for r in socket.getaddrinfo(sys.argv[1],int(sys.argv[2]),socket.AF_INET)})))"
    output = subprocess.check_output([sys.executable, "-c", code, c["APP_DOMAIN"], str(c["HTTPS_PORT"])], text=True, stderr=subprocess.STDOUT, timeout=20)
    return set(json.loads(output))


def dns(server, domain, port=53, tcp=False):
    command = [common.binary("dig"), "@" + server, "-p", str(port), domain, "A",
               "+time=1", "+tries=1", "+noall", "+answer", "+comments"]
    if tcp:
        command.append("+tcp")
    result = subprocess.run(command, capture_output=True, text=True, timeout=5)
    print("+ " + " ".join(command))
    print(result.stdout + result.stderr, end="")
    if result.returncode or "status: NOERROR" not in result.stdout:
        raise ValueError(f"DNS {server}:{port} did not return NOERROR")
    rows = [line.split() for line in result.stdout.splitlines() if line.startswith(domain + ".")]
    answers = [(row[-1], int(row[1])) for row in rows if len(row) >= 5 and row[3] == "A"]
    common.expect(len(answers) == 1, f"Expected exactly one A answer from {server}")
    return answers[0]


def https(c, target=None, path="/api/status", host=None, extra=()):
    host = host or c["APP_DOMAIN"]
    routed = ["--resolve", f"{host}:{c['HTTPS_PORT']}:{target}"] if target else []
    return common.request(f"https://{host}:{c['HTTPS_PORT']}{path}", extra=("--cacert", str(anchor()), *routed, *extra), show=True)


def check_dns(c):
    expected = record_ip(c, record_state(c))
    ttl = record_state(c)["ttl"]
    for key in ("DNS_IP", "DNS_BACKUP_IP"):
        for host in (c["APP_DOMAIN"], c["API_DOMAIN"]):
            for tcp in (False, True):
                ip, observed_ttl = dns(c[key], host, tcp=tcp)
                common.expect(ip == expected and observed_ttl == ttl,
                              f"{key}: expected {expected}, TTL {ttl}; saw {ip}, TTL {observed_ttl}. Synchronize records on both Macs.")
    print("PASS: identical records and TTL from both resolvers over UDP and TCP")


def check_https(c, wanted="both", target=None, count=10):
    seen = set()
    expected_edge = ("edge-primary" if target == c["EDGE_IP"] else "edge-standby") if target else None
    for _ in range(count):
        status, headers, body = https(c, target)
        if wanted == "unavailable":
            common.expect(status == 502 and "unavailable" in json.loads(body).get("error", ""), "Expected explicit HTTP 502")
            continue
        common.expect(status == 200, f"Application returned {status}")
        backend = headers.get("x-backend")
        common.expect(backend in ("A", "B") and json.loads(body).get("backend") == backend, "Missing/inconsistent backend identity")
        if expected_edge:
            common.expect(headers.get("x-edge") == expected_edge, f"Expected {expected_edge} via pinned routing")
        seen.add(backend)
    if wanted != "unavailable":
        common.expect(seen == ({"A", "B"} if wanted == "both" else {wanted}), f"Expected {wanted}; observed {seen}")
    print(f"PASS: HTTPS validated, {count} requests, observed {sorted(seen)}")


def check_isolation(c):
    # Starting as root would invalidate the ordinary-client requirement.
    import os
    import pwd
    common.expect(os.geteuid() not in (0, pwd.getpwnam(c["EDGE_USER"]).pw_uid), "Run as the normal client user, without sudo")
    for letter in ("A", "B"):
        address = (c[f"BACKEND_{letter}_IP"], c[f"BACKEND_{letter}_PORT"])
        try:
            with socket.create_connection(address, timeout=3):
                raise ValueError(f"ISOLATION FAILED: ordinary client reached backend {address}")
        except (OSError, TimeoutError) as e:
            print(f"Direct backend {address} blocked/refused: {e}")
    # Failed direct requests alone could just mean stopped services. Both edges
    # must prove A and B are healthy through authenticated HTTPS.
    check_https(c, target=c["EDGE_IP"])
    check_https(c, target=c["STANDBY_EDGE_IP"])
    print("PASS: ordinary client blocked; both edges can reach both healthy backends. Repeat on peer Mac.")


def backup_after_stop(c):
    # Explicitly require primary unavailable; a warmed system cache is no proof.
    try:
        dns(c["DNS_IP"], c["APP_DOMAIN"])
    except ValueError:
        pass
    else:
        raise ValueError("Primary DNS still answers: stop dns-primary on Mac 1 before this test")
    for host in (c["APP_DOMAIN"], c["API_DOMAIN"]):
        common.expect(dns(c["DNS_BACKUP_IP"], host)[0] == record_ip(c, record_state(c)), "Backup answer mismatch")
    # Run the explicit cache-flush command immediately before this test, and
    # capture port 53. OS resolver server order is adaptive, not guaranteed.
    started = time.monotonic()
    addresses = system_addresses(c)
    common.expect(record_ip(c, record_state(c)) in addresses, f"System resolver returned {addresses}")
    print(f"System resolver succeeded after {time.monotonic()-started:.3f}s; correlate with the backup's query log/packet capture.")
    check_https(c, count=8, wanted="both")


def observe(c, seconds):
    if not 1 <= seconds <= 300:
        raise ValueError("Observation window must be 1..300 seconds")
    for _ in range(seconds):
        resolved = sorted(system_addresses(c))
        print(f"time={time.time():.3f} system A={resolved}", flush=True)
        status, headers, _ = https(c)
        common.expect(status == 200, f"HTTP {status}")
        print(f"time={time.time():.3f} X-Edge={headers.get('x-edge')}", flush=True)
        time.sleep(1)


def diagnose(c):
    issues = []
    expected = record_ip(c, record_state(c))
    def probe(label, fn):
        print(f"\n[{label}]", flush=True)
        try:
            fn()
            print("PASS: " + label)
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            issues.append((label, str(e)))
            print("FAIL: " + str(e))
    for key in ("DNS_IP", "DNS_BACKUP_IP"):
        def lookup(key=key):
            ip, ttl = dns(c[key], c["APP_DOMAIN"])
            common.expect(ip == expected, f"Expected {expected}, got {ip}; TTL={ttl}")
        probe("DNS " + key, lookup)
    def system_dns():
        actual = system_addresses(c)
        print("System resolver:", actual)
        common.expect(actual == {expected}, "System DNS differs from target; inspect caches, VPN, MDM, secure DNS and scoped resolver")
    probe("DNS system", system_dns)
    for target in (c["EDGE_IP"], c["STANDBY_EDGE_IP"]):
        def tcp(target=target):
            with socket.create_connection((target, c["HTTPS_PORT"]), timeout=3) as s:
                print(s.getsockname(), "->", s.getpeername())
        probe("TCP " + target, tcp)
        def tls(target=target):
            context = ssl.create_default_context(cafile=str(anchor()))
            with socket.create_connection((target, c["HTTPS_PORT"]), timeout=3) as raw:
                with context.wrap_socket(raw, server_hostname=c["APP_DOMAIN"]) as s:
                    print(s.version(), s.cipher(), s.getpeercert().get("subjectAltName"))
        probe("TLS " + target, tls)
        probe("HTTP/backends " + target, lambda target=target: check_https(c, target=target, count=6))
    print("\nDirect backend client checks are expected to fail after isolation; use nginx upstream logs to distinguish firewall from stopped apps.")
    if issues:
        raise ValueError("Diagnostics found: " + "; ".join(f"{label}: {error}" for label, error in issues))
