# Backend readiness under PF isolation

The CLI runs under the ordinary user. PF correctly blocks that user's direct
backend TCP connection, including the old readiness probe. nginx workers run
under the authorized UID and can still serve A/B. The timeout could therefore
be a false negative after a successful backend restart.

The backend readiness check now uses lsof to inspect TCP LISTEN sockets of the
verified owned PID. It requires the exact configured IPv4 address and port,
checks PID ownership before and after inspection, and sends no network traffic.
Unexpected lsof failures propagate; absent/wrong listeners still time out. An
already-running backend is checked without restarting it. DNS/edge readiness
probes and PF policy are unchanged. Listener readiness is distinct from HTTP
health, which is checked through the authorized nginx edges.

## Apply on each deployed Mac

Copy only the corrected phase2/services.py from Rakshita's updated checkout to
Lakshya (for example AirDrop as Downloads/services.py). Do not overwrite runtime
configuration, keys or generated files, and do not stop/restart any service.
Rakshita's checkout already contains the fix.

On Lakshya, from his actual project directory:

```sh
cd ~/Downloads/cn-project
cp -p phase2/services.py "phase2/services.py.before-readiness-$(date +%Y%m%d-%H%M%S)"
python3 -m py_compile ~/Downloads/services.py
cp ~/Downloads/services.py phase2/services.py.new
mv phase2/services.py.new phase2/services.py
python3 phase2/network.py service backend-b start
python3 phase2/network.py test isolation
```

On Rakshita, from her updated checkout:

```sh
cd ~/Downloads/cn-project-main
python3 phase2/network.py service backend-a start
python3 phase2/network.py test isolation
```

`start` checks an existing owned backend's listener and leaves its PID unchanged.
If no owned backend is running, it starts one. To perform a strictly read-only
check instead, on EACH Mac from its project directory:

```sh
python3 - <<'PY'
from phase2.config import load, local_role
from phase2.services import owned_pid, backend_listening
c = load()
name = 'backend-a' if local_role(c) == 1 else 'backend-b'
pid = owned_pid(name)
if pid is None or not backend_listening(c, name, pid):
    raise SystemExit('FAIL: owned backend listener not ready')
print(f'PASS: {name}, owned PID {pid}, exact listener ready; no network probe or restart')
PY
python3 phase2/network.py test isolation
```

Do not roll back/relax PF to make readiness pass. Do not restart nginx, DNS or
Python backends just to apply this manager-only source change. Local imports of
this file occur in new management CLI processes. Running services keep running.

## Verification scope

The real lifecycle regression forces socket.create_connection to raise a
PF-style PermissionError, then starts/checks/restarts/stops a temporary backend
using the new local listener inspection. Additional cases reject wrong ports,
wildcard listeners, wrong PIDs, process disappearance, inspection errors and
missing listeners. Existing PID-reuse safety tests remain in the full suite.
Actual enforcement on the two deployed Macs remains a live acceptance check;
no system firewall rules were changed by these regression tests.

During this fix the agent's current en0 IP was 10.7.12.26, while network.env
still describes the earlier 10.7.28.208 deployment. The existing IP-role guard
correctly refused a live CLI start check; no address/configuration was changed.
Check the actual deployed IPs before using the live verification commands.
