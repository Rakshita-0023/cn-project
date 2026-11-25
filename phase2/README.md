**Current QA status:** see [submission checklist](../SUBMISSION_CHECKLIST.md). Setup, restart, fault, flush, migration and firewall stages below are maintenance procedures requiring an authorized window; do not run them as passive submission QA.

# Phase 2: fresh startup on two Macs

Run these commands from the repository root as your normal user. The CLI invokes
`sudo` for individual privileged operations. It never needs a root shell. Python
3.9+, nginx, dnsmasq, OpenSSL 3, curl and dig are required on **both** Macs.
The existing backend code and all Phase 1 launchers remain available.

## 1. Establish the LAN and review configuration

Connect both Macs to a network that allows peer traffic. Exchange the output of
`ipconfig getifaddr en0`; substitute the actual interface if Wi-Fi is different.
On Rakshita's Mac (Mac 1):

```sh
printf 'Lakshya current LAN IPv4: '; read -r PEER_IP
python3 phase2/network.py init --role 1 --peer-ip "$PEER_IP"
```

On Lakshya's Mac (Mac 2):

```sh
printf 'Rakshita current LAN IPv4: '; read -r PEER_IP
python3 phase2/network.py init --role 2 --peer-ip "$PEER_IP"
```

`init` detects this Mac's IP/default interface and writes `network.env` only if it
does not exist. If it already exists, review/edit it, or explicitly back it up
before running init; never delete a working runtime config blindly. The same
two laptop addresses and role aliases must match on both Macs. `LAN_INTERFACE`
is local to each Mac. Defaults: `codexers`, `app.codexers.test`,
`api.codexers.test`, DNS TTL 30, HTTP 8080, HTTPS 8443, backends 3001/3002.

On both:

```sh
python3 phase2/network.py validate
make setup
make inventory
source <(python3 phase2/network.py env)
./scripts/test_ping.sh
```

If dependencies are absent, run `python3 phase2/network.py setup --install`.
It uses `brew install nginx dnsmasq openssl`; it does not enable Homebrew services.
Use Homebrew OpenSSL 3 in PATH if Apple's LibreSSL is selected. Wireshark is
installed separately with `brew install --cask wireshark` if needed.

The saved inventory on 24 Nov 2026 records `10.7.12.26/19`, gateway
`10.7.0.1`, interface `en0`. This is evidence, not a future address reservation.
Lakshya's deployment address is `10.7.7.242`; his complete inventory remains uncollected. Old Phase 1 addresses must not
be reused without checking. Changing LANs requires reviewing IPs, regenerating
configs and restarting services. DNS certificates use names, so an IP-only
change does not require new certificates.

## 2. Prepare TLS without moving private keys

Phase 2 uses a new project CA and a separate key on each edge. It does not replace
Phase 1 certificates or keys. On **Mac 2**:

```sh
python3 phase2/network.py tls ca
python3 phase2/network.py tls csr
python3 phase2/network.py tls sign --csr phase2/tls/edge-primary/server.csr --out phase2/tls/edge-primary/server.crt
python3 phase2/network.py tls verify
```

On **Mac 1**:

```sh
python3 phase2/network.py tls csr
```

Transfer Mac 1's **public** `phase2/tls/edge-standby/server.csr` to Mac 2 as
`phase2/tls/standby.csr` using AirDrop or an authenticated transfer. On **Mac 2**:

```sh
python3 phase2/network.py tls sign --csr phase2/tls/standby.csr --out phase2/tls/standby-server.crt
```

Copy **only** Mac 2's public `phase2/tls/ca.crt` to the same path on Mac 1, and
`phase2/tls/standby-server.crt` to Mac 1 as `phase2/tls/edge-standby/server.crt`.
Verify the CA SHA-256 fingerprint agrees on both screens. `ca.key` stays on Mac 2;
each `server.key` stays on its originating Mac. On **both**:

```sh
python3 phase2/network.py tls verify
python3 phase2/network.py tls trust
```

Do not repeat CA/CSR/sign commands against existing output files. They refuse
overwrites. After a restart reuse the existing certificates. A fresh local CA
may need faculty approval under the assignment's TLS policy; Phase 1 material
is retained if the evaluator asks for the original route. CLI HTTPS tests use
the explicit public CA and still validate hostname, dates and chain.

## 3. Start the local roles

Resolve port conflicts first. If the original project services are running,
stop them using their existing verified-PID commands, only on the owning Mac:

```sh
# Mac 1, only when Phase 1 services are actually running:
python3 scripts/_common.py service dns stop
python3 scripts/_common.py service backend-a stop
# Mac 2, only when Phase 1 services are actually running:
python3 scripts/_common.py service nginx stop
python3 scripts/_common.py service backend-b stop
```

Do not stop unrelated Homebrew, institutional or user services automatically.
On **both** Macs:

```sh
make render
make start
make status
python3 phase2/network.py set-dns
python3 phase2/network.py flush-dns
python3 phase2/network.py test dns
python3 phase2/network.py test https
python3 phase2/network.py test balancing
python3 phase2/network.py test caching
```

Mac 1 starts primary DNS, A, standby nginx. Mac 2 starts backup DNS, B, primary
nginx. nginx workers use `_www`; root is used only for its master process and
DNS binding. `start` validates syntax, rejects occupied listeners, and checks
readiness. A partial start leaves successfully started project services visible
in `status` for diagnosis; `stop` stops only verified Phase 2 PIDs.

`set-dns` preserves original manual IPv4/IPv6 or DHCP settings and lists **both**
DNS servers. Without `UPSTREAM_DNS`, these resolvers answer project names only;
ordinary Internet lookups may stop during the demo. An optional independent
approved upstream can be added to `network.env` on both Macs. Never use either
project laptop as an upstream of the other: that can create a DNS loop.

If MDM/VPN overrides network-service DNS, inspect `scutil --dns`. For the existing
Phase 1 managed-Mac workaround, use the reversible two-resolver version:

```sh
python3 phase2/network.py scoped-dns set
python3 phase2/network.py flush-dns
scutil --dns
dscacheutil -q host -a name "$APP_DOMAIN"
```

It backs up any existing `/etc/resolver/codexers.test` file and restores it
exactly later. Ordinary `dig` does not use macOS scoped resolution; explicit
`dig @server` and native application lookup prove different paths. DNS server
selection is adaptive; primary-first response order and instant failover are
not guaranteed.

## 4. Apply service isolation on both Macs

Keep a second terminal open with `make rollback` ready. First close old direct
backend sessions. On **both**, then restart the local backend:

```sh
python3 phase2/network.py firewall check
make firewall
# Mac 1:
python3 phase2/network.py service backend-a restart
# Mac 2:
python3 phase2/network.py service backend-b restart
```

On **both**, as the ordinary client user:

```sh
python3 phase2/network.py test isolation
python3 phase2/network.py firewall status
make test-live
```

The rule permits outgoing backend connections only for the nginx worker UID.
Inbound backend requests are limited to the two edge hosts. Both Macs need the
outbound guard because each is also a client and an edge. Any process under
the worker UID shares that permission; keep that account reserved for nginx.
Privileged root users are outside this demonstration's threat model.

The live check must reject direct access to **both** healthy backends while
**both** edges still demonstrate A/B responses. A stopped backend alone cannot
pass it. PF must filter loopback; the apply command refuses a detected `lo0`
skip flag and refuses to replace a missing institutional root anchor. Existing
PF states are not globally flushed; restarting the backends drops their old
connections. A broader early `quick` rule can bypass this anchor: the live test
is the acceptance gate, even if syntax passes. See [the isolation limitations](../docs/phase2/ARCHITECTURE.md).

## 5. Demonstrate resilience and migration

With both Macs online, on **Mac 1**:

```sh
make demo-backend
make demo-dns
```

Each saves actual output and uses `finally` to restart the failed component.
The DNS demo flushes this Mac's native caches. On Mac 2, repeat native lookup
while primary DNS is stopped and capture its backup DNS query. For a longer
manual window use `service dns-primary stop`, then `test backup`, then
`service dns-primary start`; use a second terminal for restoration.

For a fully automated unprivileged DNS caching experiment:

```sh
make ttl-lab
```

It uses real dnsmasq servers, a real caching forwarding resolver, high loopback
ports and a 3-second TTL. It proves stale cache -> TTL expiry -> changed answer,
and cache flush -> immediate change. It does not claim native macOS cache proof.

For native caching and controlled DNS migration, warm the name and keep the
old edge running. Start `observe --seconds 45` on Mac 1, then in another terminal
change DNS on **Mac 2 first, then Mac 1**:

```sh
# Client terminal BEFORE changing records:
python3 phase2/network.py observe --seconds 45
# On BOTH Macs, first Mac 2 then Mac 1:
python3 phase2/network.py records --target standby --ttl 30
python3 phase2/network.py test dns
```

Record updates change app **and** API together. Each command validates the
destination edge, saves the previous generated config, restarts only its local
DNS if running, and verifies publication. It does not silently change the peer.
There is a brief split-answer window between commands, so keep both edges up.
After updating both, direct DNS queries show new answers immediately; native
cached clients can retain old answers until the **previous** TTL expires.
Observe actual behavior; macOS/browser caches and persistent connections may
vary. Then run on the client:

```sh
python3 phase2/network.py flush-dns
python3 phase2/network.py test migration
```

To demonstrate immediate flush rather than TTL expiry, repeat cutover/rollback,
warm the old answer first, and flush before its TTL expires. Do not lower TTL
at cutover and expect already-cached longer TTLs to shrink. Roll back on **both**:

```sh
make restore
```

Wait out the previous TTL or flush, then `test migration`. DNS-based cutover is
controlled migration; it is not an automatic edge health monitor.

## 6. Evidence, faculty demo and shutdown

Use [the exact 11-step demonstration](../docs/phase2/DEMO.md),
[fault/recovery guide](../docs/phase2/TROUBLESHOOTING.md), and
[viva notes](../docs/phase2/VIVA.md). Every CLI operation writes actual output
under `evidence/phase2/runs/` with a result index. A successful **render/setup**
operation is not a passed network test. `make test-local` writes test-case JSON
and text output. Save live captures/screenshots separately; none are synthesized.

On **both** at the end:

```sh
make cleanup
```

Cleanup attempts PF rollback, recorded client/scoped DNS restoration and local
service shutdown independently. It retains keys, configs and evidence. If needed
run `python3 phase2/network.py flush-dns` after restoration. Explicit certificate
trust removal, when retiring the demo CA, is:

```sh
sudo security remove-trusted-cert -d phase2/tls/ca.crt
```

This removes project CA trust; a public certificate may remain listed in Keychain.
Do not remove unrelated trust. For emergency PF rollback, `make rollback` works
without `network.env`; it releases only this project's enable token and removes
only `com.apple/cn-phase2`. It never disables PF globally or reloads `/etc/pf.conf`.

`make bundle` creates `scripts/runtime/cn-project.zip` with source, reports and
evidence, excluding runtime/generated directories, machine config and private
keys. Copy that archive to the submission destination after checking live
evidence. The original deployment folder was a downloaded copy without Git history. This public checkout has normal Git history; local edits/packaging alone still do not push changes.
