# Final submission checklist - 24 November 2026

**Status: packaged for review, NOT fully ready for final acceptance.**
The latest safe full acceptance run failed; do not replace this with earlier or
separately passing results. No services/settings were changed by final QA.

## Verified complete

- [x] Section 9 source/configuration/report deliverables exist and are packaged.
- [x] Current documented topology: Rakshita 10.7.12.26; Lakshya 10.7.7.242.
- [x] Rakshita current /19 inventory and route observation; latest ping 4/4.
- [x] Historical live DNS failover, A/B balancing, TLS verification, ETag/304,
  backend A stop/recovery, migration/rollback and post-IP-change isolation logs.
- [x] 38/38 local regressions recorded (24 Nov 15:46); not rerun as live evidence.
- [x] Genuine exported DNS query frame 16 and matching response frame 17,
  transaction 0x1a47, saved in evidence/phase2/pcaps/01-dns-query-response.png,
  .txt and .tsv. Original query-only image preserved under pcaps/originals/.
- [x] Clean 72-packet pcapng: DNS responses, TCP SYN/SYN-ACK/ACK at frames
  18/19/20, ClientHello/ServerHello at 21/24, client port 61350 to 8443.
- [x] Existing 02/03 images visibly show the handshake sequences, with original
  capture client port 61667. Their frame numbering differs from saved exports.
- [x] Genuine command exports organized by topic with published/source hashes (PF reference values redacted)
  in evidence/phase2/exports/provenance.json. No artificial UI screenshots.
- [x] All 11 Section 8 demo steps mapped in docs/phase2/DEMO.md.
- [x] Original captures preserved. Truncated pcap is partial only, excluded from
  the clean submission ZIP together with unrelated background TLS imagery.
- [x] Final PDF generated with repository workflow and visually reviewed.

## Missing evidence / acceptance blockers

- [ ] **Current full acceptance:** evidence/phase2/runs/20261124-165637-991096-test.txt
  is FAIL. Backup DNS 10.7.7.242:53 timed out; native HTTPS lookup and pinned
  primary-edge 8443 timed out despite ping succeeding. This does not establish
  the root cause or authorize a restart. Both direct backend failures alone
  do not prove isolation while healthy edge responses cannot be verified.
- [ ] Lakshya's own current mask/prefix, gateway, interface, MAC, reverse route,
  reverse ping, DNS-client settings and complete reciprocal acceptance log.
- [ ] Independent peer trust-install evidence; actual CA approval if the faculty
  requires approval for the local-CA route in Section 6.2 E.
- [ ] Precisely timed native TTL expiry relative to BOTH record changes. Existing
  observer proves transition; peer update timestamp is absent. Local cache lab
  separately proves expiry/flush, not browser/macOS timing.
- [ ] Repeat cutover at the current Rakshita IP if required: saved migration was
  demonstrated at 10.7.28.208. Both current edges later worked, but this is not
  a saved new-IP standby-target cutover run.
- [ ] Phase 2 plaintext Certificate packet: current captures show TLS 1.3 with
  encrypted Certificate; collect a validated TLS 1.2 trace if required.
  Historical Phase 1 TLS 1.2 screenshots provide supporting evidence only.
- [ ] Phase 2 loopback capture for co-located paths (not a separate assignment
  checkbox, but needed to substantiate any claimed same-host packet path).
- [ ] Section 6.3 live wrong-configured-resolver, wrong-DNS-record, both-backends
  down/502 and wrong-port demonstrations with recovery evidence. Backend A
  failover is saved. Local tests cover both-down/502 but are not live proof.
- [ ] Video/form submission and historical Phase 1 checkpoint acceptance are
  not established by files. Keep existing historical success claims labelled
  team-reported rather than promoting them to newly verified results.

## Exact safe collection commands (no setting changes or restarts)

From Rakshita's project: `cd ~/Downloads/cn-project-main`.
From Lakshya's extracted updated project: `cd ~/Downloads/cn-project`.
If their actual directory differs, use the actual project root.
On EACH Mac:

```sh
bash scripts/collect_acceptance.sh
source <(python3 phase2/network.py env)
scutil --dns > evidence/phase2/qa/scutil-dns.txt
networksetup -getdnsservers Wi-Fi > evidence/phase2/qa/client-dns.txt
route -n get "$LAPTOP1_IP" > evidence/phase2/qa/route-to-mac1.txt
route -n get "$LAPTOP2_IP" > evidence/phase2/qa/route-to-mac2.txt
ping -c 4 "$LAPTOP1_IP" > evidence/phase2/qa/ping-to-mac1.txt
ping -c 4 "$LAPTOP2_IP" > evidence/phase2/qa/ping-to-mac2.txt
python3 phase2/network.py tls verify
```

The inventory command records interface/mask/MAC/gateway; the self-ping is not
counted as reciprocal LAN proof. Copy Lakshya's generated collection folder,
inventory and peer settings into evidence/phase2/peer-lakshya/. Do not copy keys
or overwrite Rakshita's logs. If checks fail, run `make diagnose` and preserve
its output. Investigate peer listeners/status locally; any restoration needing
settings changes or restarts requires an authorized maintenance window.

To export exact saved capture evidence (Wireshark installed on the Mac):

```sh
open -a Wireshark evidence/phase2/pcaps/dns-tcp-tls.pcapng
```

Filter `frame.number == 16 || frame.number == 17` for matching DNS, `tcp.stream == 0`
for TCP/TLS; Decode As TLS for 8443 if necessary. Save genuine screenshots or
exports, without changing packet contents.

For a fresh visible TLS 1.2 certificate trace, only in an approved capture window:

```sh
source <(python3 phase2/network.py env)
sudo tcpdump -i "$LAN_INTERFACE" -s 0 -U -w evidence/phase2/qa/tls12-new.pcap 'tcp port 8443'
# In another Terminal at the project root:
source <(python3 phase2/network.py env)
curl --noproxy '*' --tlsv1.2 --tls-max 1.2 --cacert phase2/tls/ca.crt -v "https://$APP_DOMAIN:$HTTPS_PORT/api/status"
# Ctrl+C tcpdump to finalize the file, then inspect/validate it.
```

Do not overwrite existing files; choose a new suffix for repeated collection.
Capturing packets requires administrator permission; no capture was started by QA.
Use lo0 in a separate capture if collecting local paths.

## Requires an authorized live faculty demonstration

- [ ] Extension F: evaluator supplies fault; record symptoms, first failed layer,
  hypothesis, discriminating check, repair and actual recovery outputs.
- [ ] Individual viva, both students; explain DNS versus TCP/TLS/HTTP, socket
  ports, packet numbers, encrypted payload, caching, UID isolation and edge SPOF.
- [ ] Perform all 11 demo steps. Steps 8/9 include stop/restart, flush, record
  migration and possible firewall work: do NOT run these as passive QA.
- [ ] Complete missing Section 6.3 scenarios only with explicit permission. Use
  the exact fault/recovery cards in docs/phase2/TROUBLESHOOTING.md and preserve
  before/fault/after logs; do not inject both-backend or DNS faults unattended.
- [ ] For controlled TTL/migration, follow phase2/README.md stage 5 on both Macs,
  log both record-change timestamps, start observer before changes, and save
  flush/recovery outputs. Existing commands are maintenance/demo operations.

## Submission contents / Section 9 map

- Architecture: docs/phase2/ARCHITECTURE.md, architecture.svg/png, request flow.
- Configuration: docs/phase2/CONFIGURATION_BUNDLE.md, source templates, reviewed
  current-address specimens (labelled review-only), Phase 1 templates and TLS notes.
- Source: backend/, phase2/, scripts/, Makefile; original launchers retained.
- Evidence: evidence/ with genuine topic exports, logs, clean pcapng and screenshot
  provenance; historical images explicitly historical.
- Report: docs/phase2/FINAL_REPORT.md and output/pdf/phase2-final-report.pdf.
- Final presentation: docs/phase2/DEMO.md (11 steps), VIVA.md, this checklist.
- Section 10: A/B/D resilience evidence exists with scope limits; C/E evidence
  exists with peer/current-run gaps; faculty F and individual viva remain live
  evaluation items. No marks or full readiness are inferred from packaging.

See submission/README.md and the dated submission package's MANIFEST.sha256 after packaging.

### Capture commands during an authorized faculty fault window

After the evaluator introduces each missing fault (not automatically by QA),
open a recorded shell with a unique filename and collect actual observations:

```sh
mkdir -p evidence/phase2/qa
script -q "evidence/phase2/qa/faculty-fault-$(date +%Y%m%d-%H%M%S).txt" /bin/zsh
source <(python3 phase2/network.py env)
dig @"$DNS_IP" "$APP_DOMAIN" A +time=2 +tries=1
dig @"$DNS_BACKUP_IP" "$APP_DOMAIN" A +time=2 +tries=1
make diagnose
curl --noproxy '*' --cacert phase2/tls/ca.crt --connect-timeout 4 --max-time 10 -v "https://$APP_DOMAIN:$HTTPS_PORT/api/status"
# After the authorized repair, repeat the commands and capture recovery.
exit
```

For wrong configured resolver additionally save `scutil --dns` and
`networksetup -getdnsservers Wi-Fi` before/after. For a wrong DNS record save the
actual wrong A answer plus its attempted HTTPS destination. For both-backends
stopped, save validated TLS and the actual 502, then restored A/B. For a wrong
port, the evaluator must supply an observed unused destination port; save the
exact URL/port and refusal/timeout, then the configured port succeeding. A wrong
parameter probe alone must not be labelled a system DNS configuration change.
