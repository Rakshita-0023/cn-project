import contextlib
import io
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from phase2 import config, firewall, probes, services, tls
from phase2 import network
from test_local import BackendProcess, free_port


def logged_run(command, **kwargs):
    print("+", " ".join(map(str, command)))
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, **kwargs)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    result.check_returncode()
    return result


class SafetyTests(unittest.TestCase):
    def test_cleanup_continues_without_config_and_after_rollback_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(network, "ROOT", Path(directory)), patch.object(firewall, "rollback", side_effect=ValueError("PF unavailable")), patch.object(services, "control") as control, patch.object(config, "local_role", side_effect=ValueError("LAN changed")) as role:
            with self.assertRaisesRegex(ValueError, "PF unavailable"):
                network.cleanup()
            self.assertEqual(control.call_count, len(services.NAMES))
            self.assertTrue(all(call.kwargs == {"check_role": False} for call in control.call_args_list))
            role.assert_not_called()

    def test_failure_demo_restores_backend_even_when_the_probe_fails(self):
        c = config.load(ROOT / "network.env.example")
        with patch.object(config, "local_role", return_value=1), patch.object(services, "owned_pid", return_value=123), patch.object(services, "control") as control, patch.object(probes, "check_https", side_effect=[None, ValueError("injected probe failure")]):
            with self.assertRaisesRegex(ValueError, "injected"):
                network.demo(c, "backend")
            self.assertEqual([call.args[1:] for call in control.call_args_list], [("backend-a", "stop"), ("backend-a", "start")])

    def test_failed_record_publication_restores_original_record_state(self):
        c = config.load(ROOT / "network.env.example")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(config, "ROOT", root), patch.object(network, "ROOT", root), patch.object(config, "local_role", return_value=1), patch.object(probes, "check_https"), patch.object(services, "owned_pid", return_value=123), patch.object(services, "validate"), patch.object(services, "control", side_effect=[ValueError("candidate start failed"), None]), patch.object(config, "render"):
                with self.assertRaisesRegex(ValueError, "candidate"):
                    network.records(c, "standby", 4)
                self.assertEqual(config.record_state(c), {"target": "primary", "ttl": 30})

    def test_diagnostics_continue_to_http_after_dns_and_tcp_fail(self):
        c = config.load(ROOT / "network.env.example")
        with patch.object(probes, "dns", side_effect=ValueError("DNS timeout")), patch.object(probes, "system_addresses", side_effect=ValueError("native DNS timeout")), patch.object(probes.socket, "create_connection", side_effect=OSError("TCP refused")), patch.object(probes, "anchor", return_value=Path("/nonexistent/ca.crt")), patch.object(probes, "check_https") as http:
            with self.assertRaisesRegex(ValueError, "Diagnostics found"):
                probes.diagnose(c)
            self.assertEqual(http.call_count, 2)

    def test_config_defaults_and_rejects_unsafe_values(self):
        c = config.load(ROOT / "network.env.example")
        self.assertEqual(c["DNS_BACKUP_IP"], c["LAPTOP2_IP"])
        self.assertEqual(c["STANDBY_EDGE_IP"], c["LAPTOP1_IP"])
        self.assertEqual(c["FAIL_TIMEOUT"], 5)
        for extra in ("DNS_BACKUP_IP=192.168.1.42", "STANDBY_EDGE_IP=192.168.1.20", "FAIL_TIMEOUT=0", "LAN_INTERFACE=en0/x", "EDGE_USER=foo/bar"):
            with tempfile.TemporaryDirectory() as directory:
                file = Path(directory) / "network.env"
                file.write_text((ROOT / "network.env.example").read_text() + "\n" + extra + "\n")
                with self.assertRaises(ValueError):
                    config.load(file)

    def test_two_resolvers_are_passed_to_existing_backup_mechanism(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(config.common, "ROOT", Path(directory)):
            c = config.load(ROOT / "network.env.example")
            with patch.object(config.common, "wifi_service", return_value="Wi-Fi"), patch.object(config.common, "previous_dns", return_value=["8.8.8.8"]), patch.object(config.common, "run") as run:
                config.common.set_client_dns(c, servers=[c["DNS_IP"], c["DNS_BACKUP_IP"]])
                run.assert_called_once_with(["sudo", "networksetup", "-setdnsservers", "Wi-Fi", c["DNS_IP"], c["DNS_BACKUP_IP"]])
                config.common.set_client_dns(c, servers=[c["DNS_IP"], c["DNS_BACKUP_IP"]])
                saved = json.loads((Path(directory) / "dns/runtime/client-dns-backup.json").read_text())
                self.assertEqual(saved["servers"], ["8.8.8.8"])

    def test_record_state_and_config_snapshots(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(config, "ROOT", Path(directory)):
            c = config.load(ROOT / "network.env.example")
            self.assertEqual(config.record_state(c), {"target": "primary", "ttl": 30})
            output = Path(directory) / "phase2/runtime/record.json"
            config.snapshot_write(output, '{"target":"standby","ttl":3}')
            self.assertEqual(config.record_ip(c, config.record_state(c)), c["STANDBY_EDGE_IP"])
            config.snapshot_write(output, '{"target":"primary","ttl":30}')
            self.assertEqual(len(list((Path(directory) / "phase2/runtime/config-backups").iterdir())), 1)
            config.snapshot_write(output, '{"target":"bad","ttl":30}')
            with self.assertRaises(ValueError):
                config.record_state(c)

    def test_pid_reuse_and_remote_role_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            r = Path(directory)
            (r / "service.pid").write_text("12345")
            with patch.object(services, "runtime", return_value=r), patch.object(services.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "unrelated service", "")):
                with self.assertRaisesRegex(ValueError, "unrelated PID"):
                    services.owned_pid("edge-primary")
            with patch.object(services, "local_role", return_value=1):
                with self.assertRaisesRegex(ValueError, "other Mac"):
                    services.control({}, "edge-primary", "stop")

    def test_firewall_apply_refuses_missing_anchor_without_loading_root_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(firewall, "STATE", Path(directory) / "state.json"), patch.object(firewall, "render"), patch.object(firewall, "pf", side_effect=["", "block all\n"]) as pf, patch.object(firewall.sys, "platform", "darwin"):
                with self.assertRaisesRegex(ValueError, "lack anchor"):
                    firewall.apply({})
                self.assertTrue(all("-a" in call.args or call.args == ("-sr",) for call in pf.call_args_list))

    def test_firewall_refuses_loopback_skip_and_rolls_back_own_anchor_only(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            with patch.object(firewall, "STATE", state), patch.object(firewall, "render"), patch.object(firewall, "pf", side_effect=["", 'anchor "com.apple/*" all\n', "lo0 (skip)\n"]), patch.object(firewall.sys, "platform", "darwin"):
                with self.assertRaisesRegex(ValueError, "lo0"):
                    firewall.apply({})
            state.write_text(json.dumps({"anchor": firewall.ANCHOR, "token": "123"}))
            with patch.object(firewall, "STATE", state), patch.object(firewall, "pf") as pf:
                firewall.rollback()
                self.assertEqual([call.args for call in pf.call_args_list], [("-a", firewall.ANCHOR, "-F", "rules"), ("-a", firewall.ANCHOR, "-F", "Tables"), ("-X", "123")])
                self.assertFalse(state.exists())

    def test_real_pf_syntax_check_without_loading_rules(self):
        if sys.platform != "darwin":
            self.skipTest("PF syntax check requires macOS")
        c = config.load(ROOT / "network.env.example")
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "isolation.pf"
            file.write_text(firewall.rules(c))
            result = logged_run(["/sbin/pfctl", "-n", "-f", file])
            self.assertEqual(result.returncode, 0)

    def test_cli_rejects_invalid_counts_and_runs_from_other_directory(self):
        command = [sys.executable, str(ROOT / "phase2/network.py")]
        for count in ("0", "-1", "101"):
            result = subprocess.run(command + ["test", "https", "--count", count], capture_output=True, text=True, cwd="/tmp")
            self.assertNotEqual(result.returncode, 0)
        result = subprocess.run(command + ["--config", str(ROOT / "network.env.example"), "validate"], capture_output=True, text=True, cwd="/tmp")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS: validated", result.stdout)


class DNSInstance:
    def __init__(self, root, name, ip="10.23.0.20", ttl=3, port=None, upstreams=None):
        self.port = port or free_port()
        self.file = root / (name + ".conf")
        self.output = root / (name + "-process.txt")
        if upstreams is not None:
            text = f"port={self.port}\nlisten-address=127.0.0.1\nbind-interfaces\nno-resolv\nno-hosts\nstrict-order\nlog-queries=extra\n"
            text += "\n".join(f"server=127.0.0.1#{p}" for p in upstreams) + "\n"
        else:
            c = dict(config.load(ROOT / "network.env.example"), DNS_IP="127.0.0.1", DNS_BACKUP_IP="127.0.0.1", EDGE_IP=ip, STANDBY_EDGE_IP="10.23.0.10")
            with patch.object(config, "ROOT", root), patch.object(config, "runtime", side_effect=lambda n: root / (name + "-runtime")):
                file = config.render(c, "dns-primary", {"target": "primary", "ttl": ttl})
                text = file.read_text().replace("port=53\n", f"port={self.port}\n")
        self.file.write_text(text)
        exe = config.common.binary("dnsmasq")
        logged_run([exe, "--test", "--conf-file=" + str(self.file)])
        with self.output.open("w") as output:
            self.process = subprocess.Popen([exe, "--no-daemon", "--conf-file=" + str(self.file)], stdout=output, stderr=output)
        deadline = time.monotonic() + 5
        while True:
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=.2):
                    return
            except OSError:
                if self.process.poll() is not None or time.monotonic() > deadline:
                    self.stop()
                    raise RuntimeError(self.output.read_text())
                time.sleep(.05)

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)

    def query(self, host="app.team1.test", tcp=False):
        return probes.dns("127.0.0.1", host, port=self.port, tcp=tcp)


class DNSIntegrationTests(unittest.TestCase):
    def setUp(self):
        config.common.binary("dnsmasq")
        config.common.binary("dig")
        self.tmp = tempfile.TemporaryDirectory(prefix="cn phase2 dns ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "phase2/templates").mkdir(parents=True)
        shutil.copy2(ROOT / "phase2/templates/dnsmasq.conf.template", self.root / "phase2/templates/dnsmasq.conf.template")

    def instance(self, name, **kwargs):
        instance = DNSInstance(self.root, name, **kwargs)
        self.addCleanup(instance.stop)
        return instance

    def test_both_resolvers_answer_identically_udp_tcp_and_primary_stop(self):
        primary, backup = self.instance("primary"), self.instance("backup")
        for host in ("app.team1.test", "api.team1.test"):
            for tcp in (False, True):
                self.assertEqual(primary.query(host, tcp), ("10.23.0.20", 3))
                self.assertEqual(backup.query(host, tcp), ("10.23.0.20", 3))
        primary.stop()
        with self.assertRaises(ValueError):
            primary.query()
        self.assertEqual(backup.query(), ("10.23.0.20", 3))

    def test_real_forwarding_client_falls_back_after_primary_stops(self):
        primary, backup = self.instance("primary"), self.instance("backup")
        resolver = self.instance("resolver", upstreams=[primary.port, backup.port])
        self.assertEqual(resolver.query()[0], "10.23.0.20")
        primary.stop()
        resolver.process.send_signal(signal.SIGHUP)
        command = ["dig", "@127.0.0.1", "-p", str(resolver.port), "api.team1.test", "A", "+time=1", "+tries=3", "+noall", "+answer"]
        answer = logged_run(command, timeout=7)
        self.assertIn("10.23.0.20", answer.stdout)
        self.assertIn("query[A] api.team1.test", backup.output.read_text())
        print("Verified backup through a real forwarding resolver; this is separate from native macOS resolver behavior.")

    def test_real_ttl_expiry_record_change_and_cache_flush(self):
        primary = self.instance("primary", ttl=3)
        resolver = self.instance("cache", upstreams=[primary.port])
        self.assertEqual(resolver.query(), ("10.23.0.20", 3))
        time.sleep(1.05)
        old_ip, remaining = resolver.query()
        self.assertEqual(old_ip, "10.23.0.20")
        self.assertGreaterEqual(remaining, 1)
        self.assertLess(remaining, 3)
        port = primary.port
        primary.stop()
        primary = self.instance("primary-new", ip="10.23.0.10", port=port, ttl=3)
        self.assertEqual(primary.query(), ("10.23.0.10", 3))
        self.assertEqual(resolver.query()[0], "10.23.0.20")
        time.sleep(remaining + .25)
        self.assertEqual(resolver.query()[0], "10.23.0.10")
        print("Observed old cached A until real TTL expiry, then the new A.")
        # Change back and prove a cache flush takes effect before another TTL.
        primary.stop()
        primary = self.instance("primary-restored", ip="10.23.0.20", port=port, ttl=3)
        self.assertEqual(resolver.query()[0], "10.23.0.10")
        resolver.process.send_signal(signal.SIGHUP)
        time.sleep(.1)
        self.assertEqual(resolver.query()[0], "10.23.0.20")
        print("Observed immediate change after flushing the forwarding resolver cache. Native macOS flush is pending live demonstration.")


class EdgeIntegrationTests(unittest.TestCase):
    def test_two_real_edges_tls_failover_recovery_and_caching(self):
        for name in ("nginx", "openssl", "curl"):
            config.common.binary(name)
        with tempfile.TemporaryDirectory(prefix="cn phase2 edges ") as directory:
            root = Path(directory)
            (root / "phase2/templates").mkdir(parents=True)
            shutil.copy2(ROOT / "phase2/templates/nginx.conf.template", root / "phase2/templates/nginx.conf.template")
            a, b = BackendProcess("A"), BackendProcess("B")
            self.addCleanup(a.stop)
            self.addCleanup(b.stop)
            c = dict(config.load(ROOT / "network.env.example"), EDGE_IP="127.0.0.1", STANDBY_EDGE_IP="127.0.0.1",
                     BACKEND_A_IP="127.0.0.1", BACKEND_B_IP="127.0.0.1", BACKEND_A_PORT=a.port, BACKEND_B_PORT=b.port,
                     FAIL_TIMEOUT=2)
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(config, "ROOT", root))
                stack.enter_context(patch.object(tls, "ROOT", root))
                stack.enter_context(patch.object(config, "runtime", side_effect=lambda n: root / "runtime" / n))
                stack.enter_context(patch.object(config.common, "run", logged_run))
                tls.create_ca(c)
                ca_key = root / "phase2/tls/ca.key"
                self.assertEqual(ca_key.stat().st_mode & 0o777, 0o600)
                with self.assertRaisesRegex(ValueError, "already exists"):
                    tls.create_ca(c)
                keys, endpoints = [], {}
                for edge in ("edge-primary", "edge-standby"):
                    tls.csr(c, edge)
                    folder = root / "phase2/tls" / edge
                    keys.append((folder / "server.key").read_bytes())
                    tls.sign(c, folder / "server.csr", folder / "server.crt")
                    tls.verify(c, edge)
                    with self.assertRaisesRegex(ValueError, "already exists"):
                        tls.sign(c, folder / "server.csr", folder / "server.crt")
                    edge_config = dict(c, HTTP_PORT=free_port(), HTTPS_PORT=free_port())
                    file = config.render(edge_config, edge, {"target": "primary", "ttl": 30})
                    command = [config.common.binary("nginx"), "-p", str(root / "runtime" / edge) + "/", "-c", str(file)]
                    logged_run(command + ["-t"])
                    logfile = stack.enter_context((root / (edge + "-process.txt")).open("w"))
                    process = subprocess.Popen(command + ["-g", "daemon off;"], stdout=logfile, stderr=logfile)
                    stack.callback(self.stop_nginx, process)
                    self.wait_port(edge_config["HTTPS_PORT"], process)
                    endpoints[edge] = edge_config
                self.assertNotEqual(keys[0], keys[1], "Each edge must keep its own distinct private key")
                for edge, ec in endpoints.items():
                    seen = set()
                    for _ in range(6):
                        status, headers, _ = probes.https(ec, target="127.0.0.1")
                        self.assertEqual(status, 200)
                        self.assertEqual(headers["x-edge"], edge)
                        seen.add(headers["x-backend"])
                    self.assertEqual(seen, {"A", "B"})
                    self.assertEqual(probes.https(ec, target="127.0.0.1", host=ec["API_DOMAIN"])[0], 200)
                    status, headers, _ = probes.https(ec, target="127.0.0.1", path="/cache-demo")
                    self.assertEqual(status, 200)
                    self.assertIn("max-age=60", headers["cache-control"])
                    status, _, body = probes.https(ec, target="127.0.0.1", path="/cache-demo", extra=("-H", "If-None-Match: " + headers["etag"]))
                    self.assertEqual((status, body), (304, ""))
                    with self.assertRaisesRegex(ValueError, "curl failed"):
                        probes.https(ec, target="127.0.0.1", host="wrong.team1.test")
                a_port = a.port
                a.stop()
                for ec in endpoints.values():
                    for _ in range(4):
                        self.assertEqual(probes.https(ec, target="127.0.0.1")[1]["x-backend"], "B")
                a = BackendProcess("A", a_port)
                self.addCleanup(a.stop)
                for edge, ec in endpoints.items():
                    deadline = time.monotonic() + 7
                    while probes.https(ec, target="127.0.0.1")[1]["x-backend"] != "A":
                        self.assertLess(time.monotonic(), deadline, f"{edge} did not recover A")
                        time.sleep(.25)
                    self.assertEqual({probes.https(ec, target="127.0.0.1")[1]["x-backend"] for _ in range(6)}, {"A", "B"})
                    print(f"PASS: {edge} passive failover and recovered round robin")
                a.stop()
                b.stop()
                for ec in endpoints.values():
                    status, headers, body = probes.https(ec, target="127.0.0.1")
                    self.assertEqual(status, 502)
                    self.assertIn("unavailable", body)
                    self.assertEqual(headers["cache-control"], "no-store")
                # These loopback edges use distinct ports on one Mac. Actual
                # same-port DNS-based two-Mac traffic migration is a live test.
                print("Both independent edge templates validate TLS under the same CA. Two-Mac DNS traffic cutover remains a live test.")

    @staticmethod
    def wait_port(port, process):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2):
                    return
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("nginx exited; inspect process output")
                time.sleep(.05)
        raise RuntimeError("nginx did not listen")

    @staticmethod
    def stop_nginx(process):
        if process.poll() is None:
            process.send_signal(signal.SIGQUIT)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


class ServiceIntegrationTests(unittest.TestCase):
    def test_listener_inspection_rejects_wrong_socket_pid_and_inspection_errors(self):
        c = dict(config.load(ROOT / "network.env.example"), BACKEND_A_IP="127.0.0.1", BACKEND_A_PORT=3001)
        for output in ("p123\nn127.0.0.1:3002\n", "p456\nn127.0.0.1:3001\n", "p123\nn*:3001\n", ""):
            with patch.object(services, "owned_pid", return_value=123), patch.object(services.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, "")):
                self.assertFalse(services.backend_listening(c, "backend-a", 123))
        with patch.object(services, "owned_pid", side_effect=[123, None]), patch.object(services.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "p123\nn127.0.0.1:3001\n", "")):
            self.assertFalse(services.backend_listening(c, "backend-a", 123))
        with patch.object(services, "owned_pid", return_value=123), patch.object(services.subprocess, "run", return_value=subprocess.CompletedProcess([], 2, "", "permission denied")):
            with self.assertRaisesRegex(ValueError, "Cannot inspect"):
                services.backend_listening(c, "backend-a", 123)

    def test_missing_backend_listener_still_times_out_without_network_probe(self):
        c = config.load(ROOT / "network.env.example")
        with patch.object(services, "owned_pid", return_value=123), patch.object(services, "backend_listening", return_value=False), patch.object(services.time, "monotonic", side_effect=[0, 0, 7]), patch.object(services.time, "sleep"), patch.object(services.socket, "create_connection") as connect:
            with self.assertRaisesRegex(ValueError, "did not become ready"):
                services.wait_ready(c, "backend-a")
            connect.assert_not_called()

    def test_real_backend_start_conflict_restart_and_owned_stop(self):
        c = dict(config.load(ROOT / "network.env.example"), BACKEND_A_IP="127.0.0.1", BACKEND_A_PORT=free_port())
        with tempfile.TemporaryDirectory(prefix="cn phase2 service ") as directory:
            with patch.object(services, "runtime", side_effect=lambda name: Path(directory) / name), patch.object(services, "local_role", return_value=1), patch.object(services.socket, "create_connection", side_effect=PermissionError("simulated PF UID block")) as connect:
                try:
                    services.control(c, "backend-a", "start")
                    original = services.owned_pid("backend-a")
                    self.assertTrue(original)
                    services.control(c, "backend-a", "start")
                    self.assertEqual(services.owned_pid("backend-a"), original)
                    with self.assertRaisesRegex(ValueError, "cannot bind"):
                        services.check_ports(c, "backend-a")
                    services.control(c, "backend-a", "restart")
                    self.assertNotEqual(services.owned_pid("backend-a"), original)
                    response = config.common.request(f"http://127.0.0.1:{c['BACKEND_A_PORT']}/api/status")
                    self.assertEqual(response[0], 200)
                    self.assertEqual(response[1]["x-backend"], "A")
                finally:
                    with patch.object(services, "local_role", side_effect=ValueError("LAN changed")):
                        services.control({}, "backend-a", "stop", check_role=False)
                self.assertIsNone(services.owned_pid("backend-a"))
                connect.assert_not_called()
