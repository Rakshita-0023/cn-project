#!/usr/bin/env python3
"""Phase 2 operations. All commands run from any directory and log actual output."""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
import re
import shutil
import shlex
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase2 import config, firewall, probes, services, tls

ROOT = config.ROOT


class Tee:
    def __init__(self, console, file):
        self.console, self.file = console, file

    def write(self, value):
        self.console.write(value)
        self.file.write(value)
        self.file.flush()
        return len(value)

    def flush(self):
        self.console.flush()
        self.file.flush()


def flush_dns():
    config.common.expect(sys.platform == "darwin", "macOS DNS flush requires macOS")
    config.common.run(services.admin(["dscacheutil", "-flushcache"]))
    config.common.run(services.admin(["killall", "-HUP", "mDNSResponder"]))
    print("Flushed native macOS DNS caches. Browser caches/DoH and long-lived connections may behave separately.")


def scoped_dns(c, action):
    zone = c["APP_DOMAIN"].split(".", 1)[1]
    target = Path("/etc/resolver") / zone
    backup = ROOT / "dns/runtime/phase2-scoped-backup.json"
    if action == "set":
        if backup.exists():
            raise ValueError("Scoped resolver backup already exists; restore before setting again")
        content = f"# cn-phase2 managed resolver\nnameserver {c['DNS_IP']}\nnameserver {c['DNS_BACKUP_IP']}\ntimeout 2\n"
        state = {"path": str(target), "before": target.read_text() if target.exists() else None,
                 "installed_sha256": hashlib.sha256(content.encode()).hexdigest()}
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(json.dumps(state, indent=2))
        backup.chmod(0o600)
        staging = ROOT / "dns/runtime/phase2-scoped-resolver"
        staging.write_text(content)
        config.common.run(services.admin(["mkdir", "-p", "/etc/resolver"]))
        config.common.run(services.admin(["install", "-m", "644", staging, target]))
        print(f"Configured scoped resolver for {zone} with BOTH DNS servers; backup retained at {backup}")
    else:
        if not backup.exists():
            print("No scoped resolver changes recorded")
            return
        state = json.loads(backup.read_text())
        config.common.expect(state["path"] == str(target), "Scoped resolver backup path mismatch")
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != state["installed_sha256"]:
            raise ValueError("Scoped resolver changed since installation; refusing to overwrite another change")
        if state["before"] is None:
            if target.exists():
                config.common.run(services.admin(["rm", str(target)]))
        else:
            staging = ROOT / "dns/runtime/phase2-scoped-original"
            staging.write_text(state["before"])
            config.common.run(services.admin(["install", "-m", "644", staging, target]))
        backup.unlink()
        print("PASS: original scoped resolver restored")


def records(c, target, ttl):
    # Both edges are validated before DNS can direct users to either one.
    address = c["EDGE_IP"] if target == "primary" else c["STANDBY_EDGE_IP"]
    probes.check_https(c, target=address, count=6)
    state = {"target": target, "ttl": ttl if ttl is not None else config.record_state(c)["ttl"]}
    config.common.expect(1 <= state["ttl"] <= 65535, "TTL must be 1..65535")
    file = ROOT / "phase2/runtime/record.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    before = file.read_text() if file.exists() else None
    local_dns = "dns-primary" if config.local_role(c) == 1 else "dns-backup"
    was_running = bool(services.owned_pid(local_dns))
    try:
        config.snapshot_write(file, json.dumps(state, indent=2) + "\n")
        services.validate(c, local_dns)
        if was_running:
            services.control(c, local_dns, "restart")
            answer = probes.dns(c["DNS_IP" if local_dns == "dns-primary" else "DNS_BACKUP_IP"], c["APP_DOMAIN"])
            config.common.expect(answer == (address, state["ttl"]), "Running DNS did not publish the requested record/TTL")
    except BaseException:
        if before is None:
            file.unlink(missing_ok=True)
        else:
            config.snapshot_write(file, before)
        config.render(c, local_dns)
        if was_running:
            services.control(c, local_dns, "restart")
        raise
    print(f"LOCAL DNS set to {address}, TTL={state['ttl']}. Run the SAME records command on the OTHER Mac, then test dns.")
    print("The peer is not changed remotely. Do not stop the old edge before both DNS records agree and the previous TTL has expired.")


def caching(c):
    status, headers, _ = probes.https(c, path="/cache-demo")
    config.common.expect(status == 200 and "max-age=60" in headers.get("cache-control", ""), "Missing HTTP cache headers")
    etag = headers.get("etag")
    config.common.expect(bool(etag), "Missing ETag")
    status, _, body = probes.https(c, path="/cache-demo", extra=("-H", "If-None-Match: " + etag))
    config.common.expect(status == 304 and not body, "Expected empty 304 response")
    print("PASS: shared cache representation and ETag/304")


def test(c, name, wanted, count):
    if name == "dns":
        probes.check_dns(c)
    elif name in ("https", "balancing"):
        probes.check_https(c, wanted=wanted, count=count)
        if name == "https":
            status, _, _ = probes.https(c, host=c["API_DOMAIN"])
            config.common.expect(status == 200, "API domain did not return HTTP200")
    elif name == "caching":
        caching(c)
    elif name == "backup":
        probes.backup_after_stop(c)
    elif name == "isolation":
        probes.check_isolation(c)
    elif name == "migration":
        probes.check_dns(c)
        probes.check_https(c, target=c["EDGE_IP"])
        probes.check_https(c, target=c["STANDBY_EDGE_IP"])
        # An unpinned request proves the native resolver/client path.
        status, headers, _ = probes.https(c)
        config.common.expect(status == 200 and headers.get("x-edge") == "edge-" + config.record_state(c)["target"],
                             "System-resolved request has not moved to the configured edge yet; wait for TTL or flush caches")
        print("PASS: system-resolved HTTPS reaches current DNS target; both edges validate TLS")
    elif name == "all":
        failures = []
        for item in ("dns", "https", "balancing", "caching", "migration", "isolation"):
            try:
                test(c, item, "both", count)
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                failures.append(item + ": " + str(error))
        config.common.expect(not failures, "; ".join(failures))


def demo(c, scenario):
    config.common.expect(config.local_role(c) == 1, "Run automatic failure demos on Mac 1; Mac 2 must remain online")
    name = "backend-a" if scenario == "backend" else "dns-primary"
    config.common.expect(services.owned_pid(name), f"Start {name} before the demo; its original running state must be known")
    if scenario == "backend":
        probes.check_https(c, target=c["EDGE_IP"])
    else:
        probes.check_dns(c)
    try:
        services.control(c, name, "stop")
        if scenario == "backend":
            probes.check_https(c, wanted="B", target=c["EDGE_IP"])
        else:
            flush_dns()
            probes.backup_after_stop(c)
    finally:
        services.control(c, name, "start")
    if scenario == "backend":
        print("Probing for passive backend recovery", flush=True)
        deadline = time.monotonic() + c["FAIL_TIMEOUT"] + 5
        while probes.https(c, target=c["EDGE_IP"])[1].get("x-backend") != "A":
            config.common.expect(time.monotonic() < deadline, "Backend A did not recover within the bounded observation window")
            time.sleep(.5)
        probes.check_https(c, target=c["EDGE_IP"])
    else:
        probes.check_dns(c)
    print("PASS: failure demonstrated and original service restored")


def cleanup():
    # Rollback must work after DHCP changes or a lost network.env. Every service
    # still requires the absolute project command/config and owned PID checks.
    errors = []
    actions = [firewall.rollback]
    if (ROOT / "dns/runtime/client-dns-backup.json").exists():
        actions.append(config.common.restore_client_dns)
    scoped = ROOT / "dns/runtime/phase2-scoped-backup.json"
    if scoped.exists():
        def restore_scoped():
            state = json.loads(scoped.read_text())
            path = Path(state["path"])
            config.common.expect(path.parent == Path("/etc/resolver") and re.fullmatch(r"[a-z0-9][a-z0-9-]*\.test", path.name), "Invalid saved project resolver path")
            scoped_dns({"APP_DOMAIN": "app." + path.name}, "restore")
        actions.append(restore_scoped)
    actions.extend(lambda name=name: services.control({}, name, "stop", check_role=False) for name in reversed(services.NAMES))
    for action in actions:
        try:
            action()
        except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
            errors.append(str(error))
    config.common.expect(not errors, "; ".join(errors))
    print("PASS: project services stopped and recorded PF/DNS changes restored. Certificates and evidence retained; see trust removal instructions.")


def execute(a):
    if a.command == "init":
        return config.init(a.role, a.peer_ip, a.interface, a.output)
    if a.command == "bundle":
        return config.common.bundle()
    if a.command == "firewall" and a.action == "rollback":
        return firewall.rollback()
    if a.command == "restore-dns":
        return config.common.restore_client_dns()
    if a.command == "flush-dns":
        return flush_dns()
    if a.command == "cleanup":
        return cleanup()
    c = config.load(a.config)
    if a.command == "validate":
        print(json.dumps(c, indent=2))
        print("PASS: validated Phase 2 configuration")
    elif a.command == "setup":
        if a.install:
            config.common.run([config.common.binary("brew"), "install", "nginx", "dnsmasq", "openssl"])
        for name, flag in (("python3", "--version"), ("nginx", "-v"), ("dnsmasq", "--version"), ("openssl", "version"), ("curl", "--version"), ("dig", "-v")):
            config.common.run([config.common.binary(name), flag])
        print("PASS: dependencies found; setup changed no client DNS, trust, services or firewall")
    elif a.command == "render":
        names = ("dns-primary", "dns-backup", "edge-primary", "edge-standby") if a.all else config.services(config.local_role(c))
        for name in names:
            if not name.startswith("backend-"):
                print(config.render(c, name))
        firewall.render(c)
    elif a.command in ("start", "stop", "status"):
        names = config.services(config.local_role(c))
        if a.command == "stop":
            names = tuple(reversed(names))
        stopped = []
        for name in names:
            if services.control(c, name, a.command) is False:
                stopped.append(name)
        if a.command == "status":
            config.common.expect(not stopped, "Stopped services: " + ", ".join(stopped))
    elif a.command == "service":
        return services.control(c, a.name, a.action)
    elif a.command == "inventory":
        return config.common.inventory(config.local_role(c), c["LAN_INTERFACE"])
    elif a.command == "set-dns":
        return config.common.set_client_dns(c, a.service, servers=[c["DNS_IP"], c["DNS_BACKUP_IP"]])
    elif a.command == "scoped-dns":
        return scoped_dns(c, a.action)
    elif a.command == "records":
        return records(c, a.target, a.ttl)
    elif a.command == "firewall":
        if a.action == "render":
            firewall.render(c)
        elif a.action == "check":
            firewall.pf("-n", "-a", firewall.ANCHOR, "-f", str(firewall.render(c)))
        elif a.action == "apply":
            firewall.apply(c)
        elif a.action == "status":
            firewall.pf("-a", firewall.ANCHOR, "-vvsr")
    elif a.command == "tls":
        if a.action == "ca":
            config.common.expect(config.local_role(c) == 2, "Keep the CA signing key on Mac 2")
            tls.create_ca(c)
        elif a.action == "csr":
            edge = "edge-standby" if config.local_role(c) == 1 else "edge-primary"
            tls.csr(c, edge)
        elif a.action == "sign":
            config.common.expect(a.csr and a.out, "tls sign requires --csr FILE --out FILE")
            config.common.expect(config.local_role(c) == 2, "Sign on Mac 2; transfer only public CSR/certificate material")
            tls.sign(c, a.csr, a.out)
        elif a.action == "verify":
            tls.verify(c, "edge-standby" if config.local_role(c) == 1 else "edge-primary")
        elif a.action == "trust":
            tls.openssl("x509", "-in", tls.anchor(), "-noout", "-fingerprint", "-sha256")
            config.common.run(services.admin(["security", "add-trusted-cert", "-d", "-r", "trustRoot", "-k", "/Library/Keychains/System.keychain", tls.anchor()]))
    elif a.command == "test":
        test(c, a.name, a.expect, a.count)
    elif a.command == "demo":
        demo(c, a.scenario)
    elif a.command == "observe":
        probes.observe(c, a.seconds)
    elif a.command in ("health", "diagnose"):
        probes.diagnose(c)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", help="Alternative network.env path (render/validation only recommended)")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--role", type=int, choices=(1, 2), required=True)
    init.add_argument("--peer-ip", required=True)
    init.add_argument("--interface")
    init.add_argument("--output")
    for name in ("env", "validate", "start", "stop", "status", "health", "diagnose", "flush-dns", "restore-dns", "inventory", "bundle", "cleanup"):
        sub.add_parser(name)
    setup = sub.add_parser("setup")
    setup.add_argument("--install", action="store_true")
    render = sub.add_parser("render")
    render.add_argument("--all", action="store_true")
    control = sub.add_parser("service")
    control.add_argument("name", choices=services.NAMES)
    control.add_argument("action", choices=("start", "stop", "restart", "status"))
    dns = sub.add_parser("set-dns")
    dns.add_argument("--service")
    scoped = sub.add_parser("scoped-dns")
    scoped.add_argument("action", choices=("set", "restore"))
    rec = sub.add_parser("records")
    rec.add_argument("--target", choices=("primary", "standby"), required=True)
    rec.add_argument("--ttl", type=int)
    pf = sub.add_parser("firewall")
    pf.add_argument("action", choices=("render", "check", "apply", "status", "rollback"))
    tls_parser = sub.add_parser("tls")
    tls_parser.add_argument("action", choices=("ca", "csr", "sign", "verify", "trust"))
    tls_parser.add_argument("--csr")
    tls_parser.add_argument("--out")
    verify = sub.add_parser("test")
    verify.add_argument("name", choices=("dns", "https", "balancing", "caching", "backup", "isolation", "migration", "all"))
    verify.add_argument("--expect", choices=("both", "A", "B", "unavailable"), default="both")
    verify.add_argument("--count", type=int, default=10)
    failure = sub.add_parser("demo")
    failure.add_argument("scenario", choices=("backend", "dns"))
    observe = sub.add_parser("observe")
    observe.add_argument("--seconds", type=int, default=45)
    return p


def main(argv=None):
    a = parser().parse_args(argv)
    if a.command == "env":
        # Machine-readable stdout for source <(...), with no log preamble.
        try:
            for key, value in config.load(a.config).items():
                if not isinstance(value, list):
                    print(f"export {key}={shlex.quote(str(value))}")
            return 0
        except (ValueError, OSError) as error:
            print(f"FAIL: {error}", file=sys.stderr)
            return 1
    if hasattr(a, "count") and not 1 <= a.count <= 100:
        parser().error("--count must be 1..100")
    # Running the whole CLI as root changes runtime paths and client identity.
    if os.geteuid() == 0:
        print("Run this CLI as your normal user; it invokes sudo only for individual privileged operations.", file=sys.stderr)
        return 1
    stamp = datetime.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    directory = ROOT / "evidence/phase2/runs"
    directory.mkdir(parents=True, exist_ok=True)
    logfile = directory / f"{stamp}-{a.command}.txt"
    status = "PASS"
    with logfile.open("w") as output:
        with contextlib.redirect_stdout(Tee(sys.stdout, output)), contextlib.redirect_stderr(Tee(sys.stderr, output)):
            print("Observed at:", datetime.datetime.now().astimezone().isoformat())
            print("Command:", " ".join(sys.argv if argv is None else argv))
            try:
                # Capture subprocess output as well as Python output. sudo uses
                # /dev/tty for its password prompt; no password is logged here.
                original_run = config.common.run
                def logged_run(command, **kwargs):
                    print("+ " + shlex.join(map(str, command)), flush=True)
                    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, **kwargs)
                    print(result.stdout + result.stderr, end="", flush=True)
                    result.check_returncode()
                    return result
                config.common.run = logged_run
                try:
                    execute(a)
                finally:
                    config.common.run = original_run
            except (ValueError, KeyError, OSError, subprocess.SubprocessError) as e:
                print(f"FAIL: {e}", file=sys.stderr)
                status = "FAIL"
            print(f"Command result: {status}")
    with (directory / "results.jsonl").open("a") as output:
        output.write(json.dumps({"observed_at": stamp, "command": a.command, "status": status, "log": logfile.name}) + "\n")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
