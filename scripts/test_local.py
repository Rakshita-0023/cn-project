"""Development checks only: no physical Mac count or LAN evidence is implied.

Uses real HTTP, nginx, TLS and dnsmasq on loopback and ephemeral test ports.
Never changes network DNS, Keychain, /etc/hosts, or firewall settings.
"""
import contextlib
import http.client
import io
import os
import json
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from backend.backend_a import CACHE_BODY, CACHE_ETAG, Handler, ThreadingHTTPServer
from _common import load_network
import _common as project


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class BackendInstance:
    def __init__(self, identifier, port=0):
        self.server = ThreadingHTTPServer(("127.0.0.1", port), QuietHandler)
        self.server.backend = identifier
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, path, method="GET", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()


class BackendProcess:
    """Stop an entire backend, including keepalive sockets, as Ctrl+C does."""
    def __init__(self, identifier, port=0):
        self.port = port or free_port()
        harness = ("import sys; from backend.backend_a import Handler, ThreadingHTTPServer; "
                   "s=ThreadingHTTPServer(('127.0.0.1',int(sys.argv[2])),Handler); "
                   "s.backend=sys.argv[1]; s.serve_forever()")
        self.process = subprocess.Popen([sys.executable, "-c", harness, identifier, str(self.port)],
                                        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 5
        while True:
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=.2):
                    break
            except OSError:
                if self.process.poll() is not None or time.monotonic() > deadline:
                    self.stop()
                    raise RuntimeError("Test backend failed to start")
                time.sleep(.05)

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b = BackendInstance("A"), BackendInstance("B")

    def tearDown(self):
        self.a.stop()
        self.b.stop()

    def test_required_endpoints_identify_each_instance(self):
        for instance, identifier in ((self.a, "A"), (self.b, "B")):
            for path in ("/", "/api/status"):
                status, headers, body = instance.request(path)
                self.assertEqual(status, 200)
                self.assertEqual(headers["X-Backend"], identifier)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertEqual(json.loads(body)["backend"], identifier)
                self.assertEqual(json.loads(body)["status"], "ok")
                self.assertEqual(int(headers["Content-Length"]), len(body))
            for path in ("/cache-demo", "/api/cache"):
                status, headers, body = instance.request(path)
                self.assertEqual(status, 200)
                self.assertEqual(headers["X-Backend"], identifier)
                self.assertEqual(body, CACHE_BODY)
        status, _, _ = self.a.request("/unknown")
        self.assertEqual(status, 404)

    def test_cache_is_consistent_across_backends_and_supports_conditional_get(self):
        for instance in (self.a, self.b):
            status, headers, body = instance.request("/cache-demo")
            self.assertEqual(status, 200)
            self.assertEqual(body, CACHE_BODY)
            self.assertEqual(headers["ETag"], CACHE_ETAG)
            self.assertIn("max-age=60", headers["Cache-Control"])
            for validator in (CACHE_ETAG, "W/" + CACHE_ETAG, '"unrelated", ' + CACHE_ETAG, "*"):
                status, headers, body = instance.request("/cache-demo", headers={"If-None-Match": validator})
                self.assertEqual(status, 304)
                self.assertEqual(headers["ETag"], CACHE_ETAG)
                self.assertEqual(body, b"")
            status, _, body = instance.request("/cache-demo", headers={"If-None-Match": '"stale"'})
            self.assertEqual(status, 200)
            self.assertEqual(body, CACHE_BODY)

    def test_head_has_representation_headers_and_no_body(self):
        status, headers, body = self.a.request("/cache-demo", "HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(headers["ETag"], CACHE_ETAG)
        self.assertEqual(int(headers["Content-Length"]), len(CACHE_BODY))
        self.assertEqual(body, b"")


class ConfigurationTests(unittest.TestCase):
    def fixture(self, text):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "network.env"
        path.write_text(text)
        return path

    def test_example_environment_parses_and_aliases_match(self):
        values = load_network(ROOT / "network.env.example")
        self.assertEqual(values["DNS_IP"], values["LAPTOP1_IP"])
        self.assertEqual(values["EDGE_IP"], values["LAPTOP2_IP"])
        self.assertEqual(values["BACKEND_A_PORT"], 3001)
        self.assertEqual(values["BACKEND_B_PORT"], 3002)
        self.assertEqual(values["HTTP_PORT"], 8080)
        self.assertEqual(values["UPSTREAM_DNS"], [])

    def test_missing_runtime_environment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cp network.env.example"):
            load_network(Path(tempfile.gettempdir()) / "cn-does-not-exist-network.env")

    def test_domain_injection_and_non_test_domain_are_rejected(self):
        example = (ROOT / "network.env.example").read_text()
        for bad in ("team.local", "team.test;return", "-team.test"):
            text = example.replace("APP_DOMAIN=app.team1.test", "APP_DOMAIN=" + bad)
            with self.assertRaises(ValueError):
                load_network(self.fixture(text))

    def test_loopback_is_rejected_for_physical_deployment(self):
        example = (ROOT / "network.env.example").read_text()
        actual = load_network(ROOT / "network.env.example")["LAPTOP1_IP"]
        with self.assertRaisesRegex(ValueError, "private LAN"):
            load_network(self.fixture(example.replace(actual, "127.0.0.1")))

    def test_duplicates_unknown_keys_shell_expressions_and_ports_are_rejected(self):
        example = (ROOT / "network.env.example").read_text()
        for text in (example + "\nHTTPS_PORT=9000\n", example + "\nUNEXPECTED=yes\n",
                     example.replace("TEAM_NAME=team1", "TEAM_NAME=$(touch-pwned)"),
                     example.replace("HTTPS_PORT=8443", "HTTPS_PORT=3001"),
                     example.replace("BACKEND_A_PORT=3001", "BACKEND_A_PORT=65536")):
            with self.assertRaises(ValueError):
                load_network(self.fixture(text))

    def test_alias_mismatch_is_rejected(self):
        example = (ROOT / "network.env.example").read_text()
        values = load_network(ROOT / "network.env.example")
        text = example.replace("DNS_IP=" + values["DNS_IP"], "DNS_IP=" + values["LAPTOP2_IP"])
        with self.assertRaisesRegex(ValueError, "DNS_IP must match"):
            load_network(self.fixture(text))

    def test_quoted_values_comments_and_upstream_dns(self):
        example = (ROOT / "network.env.example").read_text()
        example = example.replace("TEAM_NAME=team1", 'TEAM_NAME="team1" # quoted comment')
        # Independent resolver fixture is derived from the supplied example network.
        import ipaddress
        values = load_network(ROOT / "network.env.example")
        router = str(ipaddress.IPv4Address(values["LAPTOP1_IP"]) - 1)
        values = load_network(self.fixture(example + "\nUPSTREAM_DNS=" + router + "\n"))
        self.assertEqual(values["TEAM_NAME"], "team1")
        self.assertEqual(values["UPSTREAM_DNS"], [router])


class ClientDNSStateTests(unittest.TestCase):
    def test_preserves_manual_ipv4_ipv6_settings_across_repeated_changes(self):
        config = load_network(ROOT / "network.env.example")
        with tempfile.TemporaryDirectory() as directory, patch.object(project, "ROOT", Path(directory)), \
                patch.object(project.sys, "platform", "darwin"), patch.object(project, "run") as execute:
            def output(args, **kwargs):
                if args[1] == "-listallnetworkservices":
                    return "Header\nCampus Wi-Fi\n"
                if args[1] == "-listnetworkserviceorder":
                    return "(1) Campus Wi-Fi\n(Hardware Port: Wi-Fi, Device: en0)\n"
                return config["LAPTOP2_IP"] + "\n::1\n"
            with patch.object(project.subprocess, "check_output", side_effect=output):
                project.set_client_dns(config)
                backup = Path(directory) / "dns/runtime/client-dns-backup.json"
                original = backup.read_text()
                project.set_client_dns(config, server=config["LAPTOP2_IP"])
                self.assertEqual(backup.read_text(), original)
                project.restore_client_dns()
                self.assertFalse(backup.exists())
                self.assertEqual(execute.call_args.args[0],
                                 ["sudo", "networksetup", "-setdnsservers", "Campus Wi-Fi", config["LAPTOP2_IP"], "::1"])

    def test_automatic_dns_restores_with_empty_and_failed_restore_keeps_backup(self):
        config = load_network(ROOT / "network.env.example")
        with tempfile.TemporaryDirectory() as directory, patch.object(project, "ROOT", Path(directory)), \
                patch.object(project.sys, "platform", "darwin"), patch.object(project, "run") as execute:
            def output(args, **kwargs):
                if args[1] == "-listallnetworkservices":
                    return "Header\nWi-Fi\n"
                if args[1] == "-listnetworkserviceorder":
                    return "(1) Wi-Fi\n(Hardware Port: Wi-Fi, Device: en0)\n"
                return "There aren't any DNS Servers set on Wi-Fi.\n"
            with patch.object(project.subprocess, "check_output", side_effect=output):
                project.set_client_dns(config)
                backup = Path(directory) / "dns/runtime/client-dns-backup.json"
                execute.side_effect = subprocess.CalledProcessError(1, "networksetup")
                with self.assertRaises(subprocess.CalledProcessError):
                    project.restore_client_dns()
                self.assertTrue(backup.exists())
                execute.side_effect = None
                project.restore_client_dns()
                self.assertEqual(execute.call_args.args[0][-1], "Empty")
                self.assertFalse(backup.exists())

    def test_stop_refuses_an_unrelated_pid(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(project, "ROOT", Path(directory)):
            file = project.service_pid_file("nginx")
            file.parent.mkdir(parents=True)
            file.write_text("")
            self.assertIsNone(project.owned_pid("nginx"))
            self.assertFalse(file.exists())
            file.write_text("12345")
            with patch.object(Path, "read_text", side_effect=FileNotFoundError):
                self.assertIsNone(project.owned_pid("nginx"))
            wrong = subprocess.CompletedProcess([], 0, "unrelated-process", "")
            with patch.object(project.subprocess, "run", return_value=wrong):
                with self.assertRaisesRegex(ValueError, "unrelated process"):
                    project.owned_pid("nginx")


class NetworkIntegrationTests(unittest.TestCase):
    def test_real_nginx_tls_round_robin_caching_and_failures(self):
        for name in ("nginx", "openssl", "curl"):
            if not shutil.which(name):
                self.skipTest(f"Install {name} to run this integration check")
        with tempfile.TemporaryDirectory(prefix="cn phase1 ") as directory:
            runtime = Path(directory) / "nginx/runtime"
            generated, tls = Path(directory) / "nginx/generated", Path(directory) / "tls/certs"
            # Direct renderer fixture, not a deployable LAN configuration.
            # Both processes run on this one host; neither is a physical Mac.
            config = {"TEAM_NAME": "integration", "APP_DOMAIN": "app.integration.test", "API_DOMAIN": "api.integration.test",
                      "LAPTOP1_IP": "127.0.0.1", "LAPTOP2_IP": "127.0.0.1", "DNS_IP": "127.0.0.1", "EDGE_IP": "127.0.0.1",
                      "BACKEND_A_IP": "127.0.0.1", "BACKEND_B_IP": "127.0.0.1", "BACKEND_A_PORT": 3001, "BACKEND_B_PORT": 3002,
                      "HTTP_PORT": free_port(), "HTTPS_PORT": free_port(), "DNS_TTL": 30, "UPSTREAM_DNS": []}
            while config["HTTP_PORT"] == config["HTTPS_PORT"]:
                config["HTTPS_PORT"] = free_port()
            a, b = BackendProcess("A"), BackendProcess("B")
            a_port, b_port = a.port, b.port
            process = None
            try:
                with patch.object(project, "ROOT", Path(directory)):
                    for folder, template in (("dns", "dnsmasq.conf.template"), ("nginx", "nginx.conf.template")):
                        target = Path(directory) / folder
                        target.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(ROOT / folder / template, target / template)
                    project.render_dns(config)
                    project.render_nginx(config)
                    quiet_run = lambda command: subprocess.run(command, check=True, capture_output=True)
                    with patch.object(project, "run", quiet_run), contextlib.redirect_stdout(io.StringIO()):
                        project.generate_certificate(config)
                    self.assertEqual((tls / "server.key").stat().st_mode & 0o777, 0o600)
                    self.assertEqual(set(path.name for path in generated.iterdir()), {"nginx.conf"})
                    with self.assertRaisesRegex(ValueError, "Existing certificate"):
                        project.generate_certificate(config)
                    # Only the local fixture remaps fixed deployment ports to ephemeral ports.
                    def map_ports(text):
                        return text.replace("127.0.0.1:3001", f"127.0.0.1:{a_port}").replace(
                            "127.0.0.1:3002", f"127.0.0.1:{b_port}")
                    config_file = generated / "nginx.conf"
                    config_file.write_text(map_ports(config_file.read_text()))
                    command = project.nginx_args()
                    checked = subprocess.run(command + ["-t"], capture_output=True, text=True)
                    self.assertEqual(checked.returncode, 0, checked.stderr)
                    version = subprocess.run(["nginx", "-V"], capture_output=True, text=True)
                    if "--with-http_v2_module" in version.stderr:
                        project.render_nginx(config, http2=True)
                        config_file.write_text(map_ports(config_file.read_text()))
                        checked = subprocess.run(command + ["-t"], capture_output=True, text=True)
                        self.assertEqual(checked.returncode, 0, checked.stderr)
                    with (runtime / "process.log").open("w") as output:
                        process = subprocess.Popen(command + ["-g", "daemon off;"], stdout=output, stderr=output)
                        deadline = time.monotonic() + 5
                        while True:
                            try:
                                with socket.create_connection(("127.0.0.1", config["HTTPS_PORT"]), timeout=.2):
                                    break
                            except OSError:
                                if time.monotonic() > deadline or process.poll() is not None:
                                    self.fail((runtime / "process.log").read_text())
                                time.sleep(.05)

                        def curl(path="/api/status", extra=(), host="app.integration.test", secure=True, https=True):
                            port = config["HTTPS_PORT"] if https else config["HTTP_PORT"]
                            base = ["curl", "--noproxy", "*", "--http1.1", "-sS", "--max-time", "12",
                                    "--resolve", f"{host}:{port}:127.0.0.1", "-D", "-"]
                            if secure:
                                base += ["--cacert", str(tls / "server.crt")]
                            result = subprocess.run(base + list(extra) + [f"{'https' if https else 'http'}://{host}:{port}{path}"],
                                                    capture_output=True, text=True, timeout=15)
                            return result

                        def response(path="/api/status", extra=(), host="app.integration.test"):
                            result = curl(path, extra, host)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            raw_headers, body = result.stdout.split("\n\n", 1)
                            lines = raw_headers.splitlines()
                            headers = dict((key.lower(), value.strip()) for key, value in
                                           (line.split(":", 1) for line in lines[1:] if ":" in line))
                            return int(lines[0].split()[1]), headers, body

                        seen = []
                        for _ in range(8):
                            status, headers, body = response()
                            self.assertEqual(status, 200)
                            self.assertEqual(headers["x-edge"], "Laptop-2")
                            self.assertEqual(json.loads(body)["backend"], headers["x-backend"])
                            seen.append(headers["x-backend"])
                        self.assertEqual(set(seen), {"A", "B"})
                        self.assertTrue(all(x != y for x, y in zip(seen, seen[1:])), seen)
                        # Exercise the checks used by the public shell scripts with
                        # explicit loopback routing in this development fixture only.
                        actual_curl_args = project.curl_args
                        def local_curl_args(secure=False):
                            command = actual_curl_args(secure)
                            for name in (config["APP_DOMAIN"], config["API_DOMAIN"]):
                                command += ["--resolve", f"{name}:{config['HTTPS_PORT']}:127.0.0.1"]
                            return command
                        checks_config = dict(config, BACKEND_A_PORT=a_port, BACKEND_B_PORT=b_port)
                        with patch.object(project, "curl_args", local_curl_args), contextlib.redirect_stdout(io.StringIO()):
                            for name in ("backends", "https", "load-balancing", "caching"):
                                project.check(checks_config, name, strict=True)
                        status, headers, body = response("/cache-demo")
                        self.assertEqual(status, 200)
                        self.assertEqual(body.encode(), CACHE_BODY)
                        status, headers, body = response("/cache-demo", ["-H", f"If-None-Match: {headers['etag']}"])
                        self.assertEqual(status, 304)
                        self.assertEqual(body, "")
                        self.assertEqual(response(host="api.integration.test")[0], 200)
                        redirect = curl(https=False)
                        self.assertEqual(redirect.returncode, 0, redirect.stderr)
                        self.assertIn("308", redirect.stdout.splitlines()[0])
                        self.assertIn(f"https://app.integration.test:{config['HTTPS_PORT']}/api/status", redirect.stdout)
                        # A correct trust anchor must not hide a hostname mismatch.
                        bad = curl(host="wrong.integration.test")
                        self.assertEqual(bad.returncode, 60, bad.stderr)
                        untrusted = curl(secure=False)
                        self.assertEqual(untrusted.returncode, 60, untrusted.stderr)

                        a.stop()
                        a = None
                        for _ in range(5):
                            status, headers, _ = response()
                            self.assertEqual(status, 200)
                            self.assertEqual(headers["x-backend"], "B")
                        a = BackendProcess("A", a_port)
                        # Real 5-second passive quarantine/recovery, not a fake success.
                        deadline = time.monotonic() + 8
                        recovered = False
                        while time.monotonic() < deadline:
                            if response()[1]["x-backend"] == "A":
                                recovered = True
                                break
                            time.sleep(.5)
                        self.assertTrue(recovered, "Backend A did not return after passive failure timeout")
                        seen = [response()[1]["x-backend"] for _ in range(6)]
                        self.assertEqual(set(seen), {"A", "B"})
                        self.assertTrue(all(x != y for x, y in zip(seen, seen[1:])), seen)
                        a.stop()
                        a = None
                        b.stop()
                        b = None
                        status, headers, body = response()
                        self.assertEqual(status, 502)
                        self.assertIn("unavailable", json.loads(body)["error"])
                        self.assertEqual(headers["cache-control"], "no-store")
                        self.assertIn("upstream=", (runtime / "access.log").read_text())
            finally:
                if process and process.poll() is None:
                    process.send_signal(signal.SIGQUIT)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                if a:
                    a.stop()
                if b:
                    b.stop()

    def test_real_dnsmasq_answers_both_names_with_ttl_over_udp_and_tcp(self):
        try:
            exe = project.binary("dnsmasq")
        except ValueError:
            self.skipTest("Install dnsmasq to run this integration check")
        if not shutil.which("dig"):
            self.skipTest("dig required")
        with tempfile.TemporaryDirectory(prefix="cn dns ") as directory:
            # Loopback test fixture only; there is no fabricated physical laptop.
            config = {"APP_DOMAIN": "app.integration.test", "API_DOMAIN": "api.integration.test", "DNS_IP": "127.0.0.1",
                      "EDGE_IP": "127.0.0.1", "DNS_TTL": 30, "UPSTREAM_DNS": []}
            port = free_port()
            file = Path(directory) / "dnsmasq.conf"
            with patch.object(project, "ROOT", Path(directory)):
                target = Path(directory) / "dns"
                target.mkdir()
                shutil.copy2(ROOT / "dns/dnsmasq.conf.template", target / "dnsmasq.conf.template")
                rendered = project.render_dns(config)
                file.write_text(rendered.read_text().replace("port=53\n", f"port={port}\n"))
            checked = subprocess.run([exe, "--test", "--conf-file=" + str(file)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            with (Path(directory) / "dns.log").open("w") as output:
                process = subprocess.Popen([exe, "--no-daemon", "--conf-file=" + str(file)], stdout=output, stderr=output)
                try:
                    deadline = time.monotonic() + 5
                    while True:
                        try:
                            with socket.create_connection(("127.0.0.1", port), timeout=.2):
                                break
                        except OSError:
                            if time.monotonic() > deadline or process.poll() is not None:
                                self.fail((Path(directory) / "dns.log").read_text())
                            time.sleep(.05)
                    for name in ("app.integration.test", "api.integration.test"):
                        for transport in ([], ["+tcp"]):
                            result = subprocess.run(["dig", "@127.0.0.1", "-p", str(port), name, "A",
                                                     "+noall", "+answer", "+time=2", "+tries=1", *transport],
                                                    capture_output=True, text=True, timeout=5)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            rows = [line.split() for line in result.stdout.splitlines()
                                    if line.startswith(name + ".")]
                            self.assertEqual(len(rows), 1, result.stdout + result.stderr)
                            row = rows[0]
                            self.assertEqual(row[0], name + ".")
                            self.assertEqual(row[1], "30")
                            self.assertEqual(row[3:], ["A", "127.0.0.1"])
                finally:
                    process.terminate()
                    process.wait(timeout=5)


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="cn commands with spaces ")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for folder in ("backend", "dns", "nginx", "tls", "scripts"):
            ignored = ["__pycache__", "runtime", "generated"]
            if folder == "tls":
                ignored.append("certs")
            shutil.copytree(ROOT / folder, self.root / folder,
                            ignore=shutil.ignore_patterns(*ignored))
        # Deployment certificates remain untouched; every test creates its own.
        (self.root / "tls/certs").mkdir()
        shutil.copy2(ROOT / "tls/certs/.gitkeep", self.root / "tls/certs/.gitkeep")
        text = (ROOT / "network.env.example").read_text()
        used = {53}
        for setting, default in (("BACKEND_A_PORT", 3001), ("BACKEND_B_PORT", 3002), ("HTTPS_PORT", 8443)):
            port = free_port()
            while port in used:
                port = free_port()
            used.add(port)
            text = text.replace(f"{setting}={default}", f"{setting}={port}")
        (self.root / "network.env").write_text(text)
        self.config = load_network(self.root / "network.env")

    def command(self, *args, ok=True):
        result = subprocess.run(list(args), cwd=Path(tempfile.gettempdir()),
                                capture_output=True, text=True, timeout=20)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_direct_entries_and_shell_launchers_use_environment_and_clean_pid(self):
        for identifier in ("A", "B"):
            entry = self.root / "backend" / f"backend_{identifier.lower()}.py"
            launcher = self.root / "backend" / f"start_backend_{identifier.lower()}.sh"
            for command in ([sys.executable, str(entry)], [str(launcher)]):
                process = subprocess.Popen(command, cwd=Path(tempfile.gettempdir()),
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                try:
                    port = self.config[f"BACKEND_{identifier}_PORT"]
                    deadline = time.monotonic() + 5
                    while True:
                        try:
                            with socket.create_connection(("127.0.0.1", port), timeout=.2):
                                break
                        except OSError:
                            if process.poll() is not None or time.monotonic() > deadline:
                                self.fail(f"Backend {identifier} entry point failed")
                            time.sleep(.05)
                    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
                    try:
                        connection.request("GET", "/api/status")
                        response = connection.getresponse()
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.getheader("X-Backend"), identifier)
                        self.assertEqual(json.loads(response.read())["backend"], identifier)
                    finally:
                        connection.close()
                    self.command(sys.executable, str(self.root / "scripts/_common.py"),
                                 "service", f"backend-{identifier.lower()}", "stop")
                    process.wait(timeout=5)
                    self.assertFalse((self.root / f"backend/runtime/backend-{identifier.lower()}.pid").exists())
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5)

    def test_rendering_commands_and_start_reject_invalid_nginx(self):
        for name in ("nginx", "openssl"):
            if not shutil.which(name):
                self.skipTest(f"Install {name}")
        try:
            project.binary("dnsmasq")
        except ValueError:
            self.skipTest("Install dnsmasq")
        configure = self.root / "dns/configure_dns.py"
        self.command(sys.executable, str(configure), "--check")
        rendered = self.root / "dns/generated/dnsmasq.conf"
        original = rendered.read_text()
        self.assertIn(f"address=/{self.config['APP_DOMAIN']}/{self.config['EDGE_IP']}", original)
        self.command(sys.executable, str(configure), "--record-laptop", "1", "--check")
        self.assertIn(f"address=/{self.config['APP_DOMAIN']}/{self.config['LAPTOP1_IP']}", rendered.read_text())
        self.command(sys.executable, str(configure), "--check")
        self.assertEqual(rendered.read_text(), original)
        self.command(sys.executable, str(self.root / "nginx/configure_nginx.py"))
        self.command(str(self.root / "tls/generate_certificate.sh"))
        # macOS nginx -t also checks listener addresses. Route this CLI's
        # temporary fixture to loopback, without editing real LAN configuration.
        harness = '''import runpy, sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import _common
config = _common.load_network()
config['EDGE_IP'] = '127.0.0.1'
config['HTTP_PORT'] = int(sys.argv[3])
file = sys.argv[2]
sys.argv = [file, '--check']
with patch.object(_common, 'load_network', return_value=config):
    runpy.run_path(file, run_name='__main__')
'''
        self.command(sys.executable, "-c", harness, str(self.root / "scripts"),
                     str(self.root / "nginx/configure_nginx.py"), str(free_port()))
        file = self.root / "nginx/generated/nginx.conf"
        file.write_text(file.read_text() + "\ninvalid_project_directive;\n")
        result = self.command(str(self.root / "nginx/start_nginx.sh"), ok=False)
        self.assertIn("FAIL:", result.stderr)
        self.assertFalse((self.root / "nginx/runtime/nginx.pid").exists())

    def test_optional_ca_chain_sans_permissions_and_no_silent_rotation(self):
        if not shutil.which("openssl"):
            self.skipTest("Install OpenSSL")
        self.command(str(self.root / "tls/generate_certificate.sh"), "--local-ca")
        certs = self.root / "tls/certs"
        for host in (self.config["APP_DOMAIN"], self.config["API_DOMAIN"]):
            self.command("openssl", "verify", "-CAfile", str(certs / "ca.crt"),
                         "-purpose", "sslserver", "-verify_hostname", host, str(certs / "server.crt"))
        self.command("openssl", "verify", "-CAfile", str(certs / "ca.crt"),
                     "-verify_hostname", "wrong.team1.test", str(certs / "server.crt"), ok=False)
        for key in ("ca.key", "server.key"):
            self.assertEqual((certs / key).stat().st_mode & 0o777, 0o600)
        before = (certs / "server.crt").read_bytes()
        self.command(str(self.root / "tls/generate_certificate.sh"), "--local-ca", ok=False)
        self.assertEqual((certs / "server.crt").read_bytes(), before)
        with patch.object(project, "ROOT", self.root):
            self.assertEqual(project.trust_anchor(), certs / "ca.crt")
            (self.root / "private.log").write_text("temporary runtime log")
            (self.root / "process.pid").write_text("12345")
            project.bundle()
            import zipfile
            with zipfile.ZipFile(self.root / "scripts/runtime/cn-project.zip") as archive:
                names = set(archive.namelist())
                self.assertIn("cn-project/backend/backend_a.py", names)
                self.assertIn("cn-project/nginx/nginx.conf.template", names)
                self.assertIn("cn-project/tls/certs/.gitkeep", names)
                self.assertNotIn("cn-project/network.env", names)
                self.assertNotIn("cn-project/private.log", names)
                self.assertNotIn("cn-project/process.pid", names)
                self.assertFalse(any(name.startswith("cn-project/tls/certs/")
                                     and not name.endswith("/.gitkeep") for name in names))
        self.assertFalse((certs / "server.csr").exists())

    def test_real_project_nginx_start_reload_stop_lifecycle(self):
        if not shutil.which("nginx") or not shutil.which("openssl"):
            self.skipTest("Install nginx and OpenSSL")
        # Runtime lifecycle on loopback only, with no real LAN or DNS changes.
        config = dict(self.config, EDGE_IP="127.0.0.1", HTTP_PORT=free_port())
        while config["HTTP_PORT"] == config["HTTPS_PORT"]:
            config["HTTP_PORT"] = free_port()
        with patch.object(project, "ROOT", self.root), patch.object(project, "load_network", return_value=config):
            quiet_run = lambda args, **kwargs: subprocess.run(args, check=True, capture_output=True, **kwargs)
            with patch.object(project, "run", quiet_run), contextlib.redirect_stdout(io.StringIO()):
                project.generate_certificate(config)
                file = project.render_nginx(config)
                try:
                    # Validation may create an empty PID file on macOS.
                    project.run(project.nginx_args() + ["-t"])
                    project.service("nginx", "start")
                    pid = project.owned_pid("nginx")
                    self.assertIsNotNone(pid)
                    with socket.create_connection(("127.0.0.1", config["HTTPS_PORT"]), timeout=3):
                        pass
                    good = file.read_text()
                    file.write_text(good + "\ninvalid_project_directive;\n")
                    with self.assertRaises(subprocess.CalledProcessError):
                        project.service("nginx", "reload")
                    self.assertEqual(project.owned_pid("nginx"), pid)
                    file.write_text(good)
                    project.service("nginx", "reload")
                    self.assertEqual(project.owned_pid("nginx"), pid)
                finally:
                    project.service("nginx", "stop")
                self.assertIsNone(project.owned_pid("nginx"))


if __name__ == "__main__":
    unittest.main()
