"""Project-specific process ownership, validation, start, stop and recovery."""
import os
import signal
import socket
import subprocess
import sys
import time

from .config import ROOT, common, generated, local_role, render, runtime, services, worker_uid

NAMES = ("dns-primary", "dns-backup", "backend-a", "backend-b", "edge-primary", "edge-standby")


def owned_pid(name):
    file = runtime(name) / "service.pid"
    if not file.exists():
        return None
    raw = file.read_text().strip()
    if not raw:  # nginx -t may create an empty file
        return None
    if not raw.isdigit() or int(raw) < 2:
        raise ValueError(f"Invalid PID file: {file}")
    pid = int(raw)
    result = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True)
    if result.returncode or not result.stdout.strip():
        return None
    command = result.stdout.strip()
    if name.startswith("backend-"):
        valid = str(ROOT / "phase2/backend_runner.py") in command and f"--name {name}" in command
    else:
        valid = str(generated(name)) in command and ("dnsmasq" if name.startswith("dns-") else "nginx") in command
    if not valid:
        raise ValueError(f"Refusing to signal unrelated PID {pid} in {file}: {command}")
    return pid


def admin(command):
    return (["sudo"] if os.geteuid() else []) + list(map(str, command))


def endpoint(c, name):
    if name.startswith("dns-"):
        return c["DNS_IP" if name == "dns-primary" else "DNS_BACKUP_IP"], 53
    if name.startswith("edge-"):
        return c["EDGE_IP" if name == "edge-primary" else "STANDBY_EDGE_IP"], c["HTTPS_PORT"]
    letter = name[-1].upper()
    return c[f"BACKEND_{letter}_IP"], c[f"BACKEND_{letter}_PORT"]


def check_ports(c, name):
    ip, port = endpoint(c, name)
    ports = [port, c["HTTP_PORT"]] if name.startswith("edge-") else [port]
    for port in ports:
        for kind in ([socket.SOCK_STREAM, socket.SOCK_DGRAM] if name.startswith("dns-") else [socket.SOCK_STREAM]):
            with socket.socket(socket.AF_INET, kind) as s:
                # SO_REUSEADDR permits a clean restart during TIME_WAIT, but
                # cannot share an active TCP listener. UDP is checked without it.
                if kind == socket.SOCK_STREAM:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.bind((ip, port))
                except OSError as e:
                    if (
                        os.geteuid() != 0
                        and port < 1024
                        and isinstance(e, PermissionError)
                    ):
                        # Privileged port: let the sudo-started service bind it.
                        continue
                    raise ValueError(f"{name}: cannot bind {ip}:{port}: {e}; inspect lsof, preserve existing Phase 1 services") from e


def nginx_command(name):
    return [common.binary("nginx"), "-p", str(runtime(name)) + "/", "-c", str(generated(name))]


def validate(c, name):
    file = render(c, name)
    if name.startswith("dns-"):
        common.run([common.binary("dnsmasq"), "--test", "--conf-file=" + str(file)])
    else:
        common.run(nginx_command(name) + ["-t"])


def backend_listening(c, name, pid):
    """Inspect the owned process's exact TCP listener without making traffic.

    PF intentionally denies the normal CLI user's backend connections. lsof
    reads local socket metadata, so this works without granting that user any
    network permission. Application health is tested separately through nginx.
    """
    if owned_pid(name) != pid:
        return False
    ip, port = endpoint(c, name)
    result = subprocess.run(
        [common.binary("lsof"), "-nP", "-a", "-p", str(pid),
         "-iTCP", "-sTCP:LISTEN", "-Fn"],
        capture_output=True, text=True, timeout=2)
    if result.returncode not in (0, 1) or result.stderr.strip():
        raise ValueError(f"Cannot inspect {name} listener with lsof: {result.stderr.strip() or result.returncode}")
    fields = result.stdout.splitlines()
    return (result.returncode == 0 and f"p{pid}" in fields
            and f"n{ip}:{port}" in fields and owned_pid(name) == pid)


def wait_ready(c, name):
    ip, port = endpoint(c, name)
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        pid = owned_pid(name)
        if pid:
            if name.startswith("backend-"):
                if backend_listening(c, name, pid):
                    print(f"PASS: {name} owned PID {pid} listening {ip}:{port} (local socket inspection; HTTP health via nginx)")
                    return
            else:
                try:
                    with socket.create_connection((ip, port), timeout=.3):
                        print(f"PASS: {name} listening {ip}:{port}, PID {pid}")
                        return
                except OSError:
                    pass
        time.sleep(.1)
    raise ValueError(f"{name} did not become ready; inspect {runtime(name)}. Any started process is retained for diagnosis; use service stop.")


def control(c, name, action, check_role=True):
    if name not in NAMES:
        raise ValueError("Unknown project service")
    if not check_role and action != "stop":
        raise ValueError("Only owned-process shutdown may bypass a changed LAN role")
    if check_role and name not in services(local_role(c)):
        raise ValueError(f"{name} belongs on the other Mac; detected addresses prevent remote-role mistakes")
    pid = owned_pid(name)
    if action == "status":
        print(f"{name}: {'running PID ' + str(pid) if pid else 'STOPPED'}")
        return bool(pid)
    if action in ("stop", "restart") and pid:
        command = ["kill", "-QUIT" if name.startswith("edge-") else "-TERM", str(pid)]
        common.run(admin(command) if not name.startswith("backend-") else command)
        deadline = time.monotonic() + 10
        while owned_pid(name) and time.monotonic() < deadline:
            time.sleep(.1)
        if owned_pid(name):
            raise ValueError(f"{name} did not stop; retained its PID and logs")
        pid = None
    if action == "stop":
        print(f"PASS: {name} stopped")
        return
    if pid:
        if name.startswith("backend-"):
            wait_ready(c, name)
            return
        print(f"PASS: {name} already running PID {pid}")
        return
    check_ports(c, name)
    r = runtime(name)
    r.mkdir(parents=True, exist_ok=True)
    if name.startswith("backend-"):
        ip, port = endpoint(c, name)
        command = [sys.executable, str(ROOT / "phase2/backend_runner.py"), "--name", name, "--host", ip, "--port", str(port)]
        with (r / "process.log").open("a") as output:
            child = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=output, start_new_session=True)
        (r / "service.pid").write_text(str(child.pid))
    else:
        validate(c, name)
        if name.startswith("edge-"):
            worker_uid(c)
            common.run(admin(["chown", c["EDGE_USER"], r / "client_temp", r / "proxy_temp"]))
            common.run(admin(nginx_command(name)))
        else:
            common.run(admin([common.binary("dnsmasq"), "--conf-file=" + str(generated(name))]))
    wait_ready(c, name)
