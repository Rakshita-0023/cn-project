**Current QA status:** see [submission checklist](../../SUBMISSION_CHECKLIST.md). Setup, restart, fault, flush, migration and firewall stages below are maintenance procedures requiring an authorized window; do not run them as passive submission QA.

# Live deployment: 24 November 2026

This dated runbook supersedes pending-peer-IP statements in the 23 November
report. Run each block in order. Mac 2 needs the UPDATED delivery zip from this
chat, not the original GitHub Phase 1 download. It extracts as `cn-project`.
This existing-deployment handoff requires Rakshita's current PUBLIC CSR copied to `phase2/handoff/rakshita-standby.csr` on Mac 2. It is not bundled in Git. Never generate a new key merely to repeat the handoff; fresh clones should follow phase2/README.md instead.

| Mac | IP | Final roles |
|---|---|---|
| Rakshita / 1 | 10.7.12.26 | primary DNS :53, A :3001, standby edge :8443 |
| Lakshya / 2 | 10.7.7.242 | backup DNS :53, B :3002, primary edge :8443 |

Rakshita's observed mask is 255.255.224.0 (/19), gateway 10.7.0.1, interface en0.
Both IPs fall in 10.7.0.0/19 from her subnet view; her route to Lakshya is direct
over en0. Lakshya's own mask and reverse route remain to be inspected below.
Do not change routes or force a subnet mask merely to match this table.

## 1. Lakshya: initialize, check reverse path, issue certificates

Extract the updated archive in Downloads first. Paste:

```sh
cd ~/Downloads/cn-project
mkdir -p phase2/handoff
# Copy Mac 1 current public server.csr here as rakshita-standby.csr before signing.
ifconfig en0
ipconfig getoption en0 subnet_mask
route -n get 10.7.12.26
ping -c 4 10.7.12.26
python3 phase2/network.py init --role 2 --peer-ip 10.7.12.26 --interface en0
make setup
make inventory
python3 phase2/network.py tls ca
python3 phase2/network.py tls csr
python3 phase2/network.py tls sign --csr phase2/tls/edge-primary/server.csr --out phase2/tls/edge-primary/server.crt
python3 phase2/network.py tls sign --csr phase2/handoff/rakshita-standby.csr --out phase2/handoff/standby-server.crt
cp phase2/tls/ca.crt phase2/handoff/ca.crt
python3 phase2/network.py tls verify
openssl x509 -in phase2/tls/ca.crt -noout -fingerprint -sha256
```

If Wi-Fi is not en0, use its actual device in the checks and init. If a runtime
config already exists, init refuses to overwrite it: review it instead. Install
missing dependencies with `python3 phase2/network.py setup --install` then retry
`make setup`. Use Homebrew OpenSSL 3, not old LibreSSL.

AirDrop ONLY `phase2/handoff/ca.crt` and `standby-server.crt` to Rakshita's
Downloads. Compare CA fingerprints on both screens. Keep ca.key on Lakshya and
both edge private keys on their originating Macs. Fresh TLS creation commands
refuse existing material; reuse existing successful outputs on subsequent runs.

## 2. Rakshita: install returned PUBLIC certificates

In the historical deployed folder, IP config, standby CSR and Backend A were already prepared. A fresh clone does not contain those keys or runtime state; follow the fresh-start guide first. After receiving the two files under the exact names below:

```sh
cd ~/Downloads/cn-project-main
python3 phase2/network.py validate
openssl x509 -in ~/Downloads/ca.crt -noout -fingerprint -sha256
test ! -e phase2/tls/ca.crt && install -m 644 ~/Downloads/ca.crt phase2/tls/ca.crt
test ! -e phase2/tls/edge-standby/server.crt && install -m 644 ~/Downloads/standby-server.crt phase2/tls/edge-standby/server.crt
python3 phase2/network.py tls verify
python3 phase2/network.py tls trust
make render
make start
make status
```

Do not paste subsequent stages until certificate verification and startup pass.
Commands invoke sudo individually; enter passwords only in your own Terminal.
Do not run the whole Python CLI with sudo.

## 3. Lakshya: start his local roles

```sh
cd ~/Downloads/cn-project
python3 phase2/network.py tls trust
make render
make start
make status
```

If a listener conflicts, inspect it with `lsof -nP -iTCP -sTCP:LISTEN`. Stop only
verified old project processes with their original Phase 1 stop commands. Do not
kill unrelated nginx/dnsmasq instances. Startup preserves conflicting services.

## 4. Both: DNS and HTTPS acceptance (after both Macs started)

Use the corresponding `cd` above first, then paste on EACH Mac:

```sh
source <(python3 phase2/network.py env)
python3 phase2/network.py test dns
python3 phase2/network.py set-dns
python3 phase2/network.py flush-dns
scutil --dns
python3 phase2/network.py test https
python3 phase2/network.py test balancing
python3 phase2/network.py test caching
```

If direct DNS succeeds while native resolution fails under MDM, run the reversible
`python3 phase2/network.py scoped-dns set`, flush again, then retest HTTPS.
Without UPSTREAM_DNS, Internet DNS may be unavailable during this private demo.
The exact app URL is https://app.codexers.test:8443 and API is
https://api.codexers.test:8443. No curl -k is needed or permitted as proof.

## 5. Backup DNS: coordinate both Macs

Rakshita, Terminal 1:

```sh
python3 phase2/network.py service dns-primary stop
```

Now BOTH Macs:

```sh
python3 phase2/network.py flush-dns
python3 phase2/network.py test backup
```

Confirm an actual query appears in Mac 2's DNS log or packet capture. Then
Rakshita MUST restore primary, even if a client check fails:

```sh
python3 phase2/network.py service dns-primary start
python3 phase2/network.py test dns
make demo-backend
```

`make demo-backend` automatically stops A, requires B-only HTTPS responses,
restores A in a finally block, and polls until A/B balancing resumes. Lakshya
can run `test balancing --expect B` during a longer manually coordinated A-stop
window, then repeat normal balancing after restoration.

## 6. BOTH: rehearse rollback BEFORE installing isolation

No firewall policy has been applied by the agent. On EACH Mac:

```sh
python3 phase2/network.py firewall check
python3 phase2/rollback_rehearsal.py
```

Require PASS. This performs actual privileged load/flush of an EMPTY project
anchor through the real rollback function, checks that root rules are unchanged,
and leaves PF enable state alone. PF enable-token release has unit coverage;
it is not exercised by this empty-anchor rehearsal. Installation is now gated
on a matching local rehearsal marker. Do not copy that runtime marker between
Macs. A test failure means STOP, preserve output, and do not install policy.

Keep a second Terminal ready with `python3 phase2/network.py firewall rollback`.
Only after successful rehearsal on BOTH Macs, install on EACH:

```sh
make firewall
```

Rakshita then runs:

```sh
python3 phase2/network.py service backend-a restart
```

Lakshya then runs:

```sh
python3 phase2/network.py service backend-b restart
```

Now EACH ordinary client user runs:

```sh
python3 phase2/network.py test isolation
python3 phase2/network.py firewall status
make test-live
```

Both direct backends must be blocked while both edges still show healthy A/B.
Loopback/global quick rules/MDM may prevent enforcement. Roll back with
`make rollback` if checks fail; do not label syntax success as isolation proof.
Both hosts need UID egress guards because clients share the edge hosts' IPs.

## 7. Standby migration and TTL

Rakshita starts an observer BEFORE changing records:

```sh
python3 phase2/network.py observe --seconds 60
```

In separate terminals run on Lakshya FIRST, then Rakshita:

```sh
python3 phase2/network.py records --target standby --ttl 30
```

After both changes, EACH Mac:

```sh
python3 phase2/network.py test dns
```

Observe the real native cache behavior and X-Edge transition. Keep the primary
edge alive through the old TTL. Then EACH Mac:

```sh
python3 phase2/network.py flush-dns
python3 phase2/network.py test migration
```

Expected after native refresh: X-Edge edge-standby, validated TLS, A/B responses.
To restore, on Lakshya FIRST then Rakshita:

```sh
make restore
python3 phase2/network.py flush-dns
python3 phase2/network.py test migration
```

## 8. Final recovery

On BOTH Macs, `make cleanup` independently attempts project PF rollback, saved
DNS/scoped-resolver restoration and owned service shutdown, even after IP changes.
Retain certificates for reuse; remove project trust explicitly only when retiring
this CA (`sudo security remove-trusted-cert -d phase2/tls/ca.crt`).

## Audited test status (supersedes the original continuation checklist)

Historical live DNS failover, physical HA, TLS, balancing, caching, isolation
and old-address migration/rollback are evidenced in FINAL_REPORT.md. The real
PF rollback at 16:15:51 and corrected readiness at 16:16 are saved. A rehearsal
transcript itself is absent; a later successful apply passed the local gate.
Latest local suite: 38/38. Current full acceptance at 16:56:37 is FAIL on backup
DNS/native lookup/primary-edge service paths; no corrective live changes were
made by final QA. Peer mask/inventory and reciprocal-client tests remain missing.
Use ../../SUBMISSION_CHECKLIST.md rather than treating this setup runbook as
proof of current readiness. Its maintenance blocks must not be run passively.
