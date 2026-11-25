# Phase 2 configuration bundle

The original [Phase 1 configuration bundle](../CONFIGURATION_BUNDLE.md), DNS/nginx
templates, backend sources and TLS launchers are retained. Phase 2 does not
silently replace their generated files, PIDs, certificates or keys.

| Artifact | Purpose |
|---|---|
| `network.env.example` | Original safe example; `init` fills actual current IPs, team and additional aliases |
| `scripts/_common.py` | Existing safe parser and DNS backup/restore; accepts Phase 2 keys and a DNS server list |
| `phase2/config.py` | Extended validation, role mapping, exact record state, snapshots and rendering |
| `phase2/templates/dnsmasq.conf.template` | Identical exact app/API records on primary and backup; configurable TTL; no DHCP |
| `phase2/templates/nginx.conf.template` | Primary/standby edge, round robin, passive failure quarantine/retry, explicit worker identity/source bind |
| `phase2/firewall.py` | Scoped PF rules, preflight, rollback and enable-token ownership |
| `phase2/services.py` | Owned-process control, conflict detection, readiness and role verification |
| `phase2/backend_runner.py` | Reuses Phase 1 HTTP implementation with explicit LAN bind/port |
| `phase2/tls.py` | Independent edge keys/CSRs, CA signing, certificate/key/hostname verification |
| `phase2/probes.py`, `phase2/network.py` | DNS/TCP/TLS/HTTP checks, live tests, migration, recovery, diagnostic logs |
| `Makefile` | Repeatable start, stop, setup, health, tests, failure demos and packaging |

Optional Phase 2 settings in `network.env`:

```dotenv
# Set these to the ACTUAL matching IPs when adding them manually:
# DNS_BACKUP_IP=<LAPTOP2_IP>
# STANDBY_EDGE_IP=<LAPTOP1_IP>
LAN_INTERFACE=en0
EDGE_USER=_www
FAIL_TIMEOUT=5
```

Missing backup/standby aliases default to their laptop's IP. Existing required
Phase 1 aliases and `.test` team/name checks remain enforced. `DNS_TTL` defaults
to 30 seconds; `FAIL_TIMEOUT` allows 1..60 seconds; ports may not overlap.
The environment file is parsed as data, never sourced by the Python CLI.

`make render` creates local-role configs; `python3 phase2/network.py render --all`
renders both DNS/edge variants for inspection. Generated output is ignored under
`phase2/generated/`; changed files have content-addressed backups in
`phase2/runtime/config-backups/`. All paths are regenerated per Mac. Source
templates are the portable configuration bundle; rendered paths from another
Mac must not be reused as-is.

Project service PIDs/logs and nginx worker temp paths live under
`/private/tmp/cn-phase2-<normal-user-uid>/<service>/`. This avoids opening a private
home/Downloads directory to `_www`. The nginx master reads its certificate/key
as root; workers use only their assigned temp directories and inherited logs.
Only those two temp directories are chowned to the worker account.

DNS cutover state is `phase2/runtime/record.json`, separate from `EDGE_IP`, which
always denotes the original edge. `records --target standby --ttl 30` changes
both names on the local resolver and verifies it. Run it on both Macs; `test dns`
rejects mismatches. `records --target primary --ttl 30` is the rollback.

DNS host records use explicit per-record TTL and `local-ttl`; those settings
and dnsmasq's cache/forward behavior are documented in the
[dnsmasq manual](https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html).
The nginx retries are limited to two upstream attempts and safe read-only project
requests, using the
[proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_next_upstream).

The CA/key/CSR paths and public-only transfer commands are in
[the fresh-start guide](../../phase2/README.md). TLS private material is ignored
by Git and excluded from the submission archive. Existing Phase 1 trust material
is retained. Certificate trust, system DNS and PF installation require admin
access; all local automated tests use temporary material and high ports.

For exact default example renders see [config-examples](config-examples/README.md).
For current machine specifics generate the configs and save sanitized copies
after both live inventories have been recorded. Do not put a private key in the
report, evidence folder or archive.

## Final QA configuration review

Current intended deployment: Rakshita 10.7.12.26 (primary DNS/A/standby edge),
Lakshya 10.7.7.242 (backup DNS/B/primary edge). See
[current-configuration/README.md](current-configuration/README.md) for portable,
current-address review specimens of both DNS/edge configurations and PF policy.
They were rendered without loading them or changing live/generated configs;
they do not certify the remote Mac's actual configuration. Generic team1
config-examples/ remain explicitly examples. Source templates and successful
historical logs remain preserved. Backend readiness now uses owned-listener
inspection because the ordinary CLI user's backend TCP probes conflict with PF;
application health is verified through nginx.

The latest passive acceptance failed on backup DNS and primary-edge service
paths. Configuration review is not a live readiness PASS. Peer configuration,
trust and client enforcement evidence remain to be collected; see the root
SUBMISSION_CHECKLIST.md. PF rollback is demonstrated in the saved 16:15:51 log;
no new policy, trust installation or DNS change was performed by submission QA.
