# Faculty challenge: diagnose, explain, restore

Run `make diagnose`. It checks both explicit DNS resolvers, native system DNS,
TCP to both edges, TLS with hostname/CA verification, then HTTP and backend
identities. It continues independent checks after failures and returns nonzero
if any layer fails. Resolver, TCP, curl and subprocess waits are bounded.
Normal direct backend access should fail **after** isolation; use trusted edge
requests and nginx logs to inspect upstreams.

Say what succeeded, what failed, your hypothesis, and the next discriminating
test. DNS success is not application success. TCP success is not TLS trust.
An HTTP 502 means the edge accepted the request but could not obtain a usable
upstream response. A blocked direct backend can be correct policy.

## Repeatable fault cards

Use project-owned service names only, take one fault at a time, and record a
healthy baseline first. The first four service scenarios can be injected with
the shown command and restored without editing working config files.

| Fault | Injection / test | Expected first failure | Recovery / verification |
|---|---|---|---|
| Primary DNS service stopped | Mac 1: `service dns-primary stop`; flush both clients; `test backup` | Explicit primary DNS fails; backup/native lookup should recover with retries | `service dns-primary start`; `test dns` |
| Both DNS services stopped | Also Mac 2: `service dns-backup stop`; flush and attempt native lookup | DNS; existing cached connections may survive | Start both DNS services; `test dns`, `test https` |
| Backend A stopped | Mac 1: `service backend-a stop`; `test balancing --expect B` | Direct A is unavailable; edge requests should keep returning 200 from B | `service backend-a start`; allow passive expiry, `test balancing` |
| Both backends stopped | Also Mac 2: `service backend-b stop`; `test balancing --expect unavailable` | DNS/TCP/TLS can succeed; application returns explicit 502 | Start both; retry until A/B reappear; `test caching` |
| Active edge stopped | Mac 2: `service edge-primary stop`; `diagnose` | DNS returns a valid address; active edge TCP fails while standby still answers pinned probes | Start primary; or deliberately migrate both DNS servers to healthy standby; `test migration` |
| Wrong resolver queried | `dig @127.0.0.1 -p 9 "$APP_DOMAIN" +time=1 +tries=1` after confirming port 9 is unused | Query timeout/refusal, not proof that project DNS is broken | Query both configured DNS addresses; no settings were changed |
| Wrong destination port | Inspect `lsof -nP -iTCP -sTCP:LISTEN`; enter an observed unused port; curl the domain at that port | TCP fails even though DNS works | Return to configured `HTTPS_PORT`; `test https` |
| TLS hostname mismatch | curl with `--resolve wrong.codexers.test:$HTTPS_PORT:$EDGE_IP --cacert phase2/tls/ca.crt` and URL `https://wrong.codexers.test:$HTTPS_PORT/api/status` | TLS hostname validation fails despite reachable nginx | Use configured app/API name; no key/config change is needed |
| Missing/wrong public CA | Repeat HTTPS using an unrelated CA file in `--cacert` | TLS chain validation fails; TCP remains reachable | Use `phase2/tls/ca.crt`; compare public CA fingerprints; `tls verify` |
| Wrong/stale DNS target | Faculty changes record or client cache retains earlier edge | Explicit DNS and native lookup differ, or TCP reaches an unexpected host | Restore using `records --target primary --ttl 30` on both; flush and `test migration` |
| Firewall bypass/misorder | `test isolation` succeeds in a direct backend connection | Isolation check deliberately fails | Inspect `firewall status`, worker UID, both-host installation, lo0 skip and global early quick rules; rollback if diagnosis cannot safely proceed |

Every `service ...` above means `python3 phase2/network.py service ...`.
Tests likewise use `python3 phase2/network.py test ...`. Use the actual configured
team domain when it differs from codexers. A controlled wrong-parameter probe
demonstrates a layer failure without mutating system-wide DNS or TLS material.

## Recovery order

1. Confirm current LAN addresses and peer reachability. Correct `network.env`
   before regenerating anything if DHCP changed addresses.
2. Restore local backend, DNS and edge processes on their owning Macs. Retain
   private keys and existing evidence. Use `make status` and runtime logs.
3. Verify explicit UDP/TCP answers on both resolvers, then native DNS. Check
   `scutil --dns`, network service DNS, scoped resolver, VPN/MDM/secure DNS.
4. Validate certificate/key/SANs with `tls verify`; recheck system time if dates
   fail. Do not use curl `-k` as a recovery step.
5. Restore records on both to the intended edge; wait for the previous TTL or
   flush caches. Check normal HTTPS and both backends through the edge.
6. Run isolation on both ordinary client accounts and `make test-live`, then
   repeat the selected failure and recovery evidence.

For immediate firewall restoration, `make rollback` removes only project rules
and releases only the project token. The root ruleset is never reloaded. If the
project rollback record is corrupt, inspect it and the recorded token instead
of disabling PF globally. For DNS restoration use `restore-dns` and, if installed,
`scoped-dns restore`. `make cleanup` attempts all recorded restorations even if
one fails, then reports remaining errors. Original DNS backups are removed only
after a successful system restoration.

## Live challenge record (complete during evaluation)

| Field | Actual observation |
|---|---|
| Time, evaluator and injected fault | PENDING LIVE |
| Last known good state | PENDING LIVE |
| First failed layer and exact output | PENDING LIVE |
| Successful independent checks | PENDING LIVE |
| Hypothesis and discriminating test | PENDING LIVE |
| Repair and why it addresses that layer | PENDING LIVE |
| Recovery checks and evidence path | PENDING LIVE |

Local debugging already found that a single DNS request with no retries can
time out before fallback, and a fixed sleep can sample nginx before quarantine
expires. The tests now exercise client retries and bounded recovery polling.
Original failure outputs are retained under `evidence/phase2/attempt1-*` and
`focused-debug-tests.txt`; only later executed passing tests count as verified.
