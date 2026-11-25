# Private Network Service Platform

Phase 2 final report - Codexers - 24 November 2026

Rakshita and Lakshya Choudhary (team Codexers).
Two physical macOS laptops with combined roles. This report replaces the
23 November deployment-pending snapshot with an audit of saved 24 November
command logs, the latest local regression results and existing packet evidence.
All times below are India Standard Time (UTC+05:30).

## 1. Deployment outcome and evidence scope

Final QA status: **not fully ready for submission acceptance**. The safe,
non-destructive full acceptance run at 16:56:37 on 24 November is FAIL [E13].
Primary DNS answered, but backup DNS timed out, native HTTPS lookup timed out,
and a pinned connection to the primary edge's 8443 timed out. The peer still
answered ping 4/4. This identifies current service-path failures, not their root
cause. No DNS/firewall settings or running services were changed to fix them.
Earlier live successes below remain valid historical evidence, not a present
full readiness claim. SUBMISSION_CHECKLIST.md records the remaining gates.

The two-Mac platform was deployed and exercised over the LAN. Saved logs show
identical DNS records over UDP/TCP, native DNS fallback with primary DNS stopped,
trusted domain HTTPS, both backend identities, ETag/304 caching, backend HA,
controlled standby-edge migration and rollback, and firewall isolation from
Rakshita's ordinary client account. An IP change interrupted the configuration;
subsequent logs show service recovery at the new address and restored isolation.
The deployment audit suite records 38/38 passing tests, zero failures/errors/skips,
at 15:46:05 on 24 November. This suite is supporting local evidence, not a
substitute for the live command results.

Completed below means demonstrated in the saved logs for the stated host and
address configuration. The saved operational logs identify Rakshita's checkout;
they exercise both physical edges/backends but do not independently document
all commands from Lakshya's client account. Reciprocal client acceptance should
not be inferred from a successful test on Rakshita. Extension F's actual
faculty-injected challenge remains pending. No live services, DNS or firewall
settings were changed while preparing this report.

## 2. Final topology and configuration

Mac 1/Rakshita uses **10.7.12.26**: primary DNS UDP/TCP 53, Backend A TCP 3001,
standby nginx HTTPS 8443 and HTTP redirect 8080. Mac 2/Lakshya uses
**10.7.7.242**: backup DNS 53, Backend B 3002, primary nginx HTTPS 8443 and
HTTP redirect 8080. Both edges balance to A/B. Both DNS servers publish
app.codexers.test and api.codexers.test, normally pointing to Mac 2, with TTL 30.

Rakshita's 16:14 inventory records en0, mask 255.255.224.0 (/19), gateway
10.7.0.1 and address 10.7.12.26 [E10]. Both addresses lie in 10.7.0.0/19 from
this inventory's subnet view. Her earlier deployment address
was 10.7.28.208; historical live tests below retain that address and their actual
timestamps. A saved current Mac 2 subnet/mask inventory and reverse-ping log
are not present in this evidence set. Mac 2's IP is corroborated by DNS answers,
HTTPS upstream/edge tests and packet captures.

Each edge keeps a separate private key signed by the project CA. The saved
standby certificate verification checks both SANs, chain, key match and key
permissions; certificate validity is 24 Nov 2026 to 22 Feb 2027 [E01]. The local
trust command succeeded at 14:55:58. Validated HTTPS requests test both physical
edges without curl -k; a browser padlock screenshot or Mac 2 Keychain-install
transcript is not separately saved. The architecture diagram is retained with
current addresses. Backend HTTP remains plaintext behind the TLS edge.

Phase 1 backend behavior and existing artifacts remain preserved. Phase 2 adds
separate generated configs, role-specific process ownership checks, record state,
TLS material and scoped rollback records. Current generated paths are local to
each Mac and must be regenerated after a LAN address change.

## 3. Actual extension and application results

The matrix summarizes saved observations; evidence IDs resolve in Section 7.

| Area | Saved observation | Evidence | Status / scope |
|---|---|---|---|
| A: backup DNS | Primary stopped; primary queries failed, backup answered; native resolver succeeded in 3.373s; eight HTTPS requests returned A/B; primary restored | E03 | Completed from Rakshita's client at earlier IP; peer-client repeat not evidenced |
| B: TTL | TTL 30 returned by both resolvers; native observer changed primary to standby; local real caching lab proved stale answer, expiry and flush | E04, E05 | Live transition and flush completed; exact native cache lifetime and browser-cache timing not established |
| C: isolation | Direct A timed out and direct B was refused; both physical edges still served A/B. After IP recovery, policy reapplied and same acceptance passed | E06, E11 | Completed from Rakshita at both addresses; Lakshya client transcript not saved |
| D: backend HA | Before stop A/B; A stopped, ten HTTPS requests B-only; A restored and A/B resumed | E07 | Completed live before IP change; later new-IP A/B availability verified |
| E: migration | Both DNS records changed to standby; native HTTPS reached standby; records restored and native HTTPS returned to primary | E04, E05 | Completed at earlier Mac 1 address; new-IP standby readiness verified, separate cutover rerun not saved |
| TLS / balancing | Hostname/CA validation succeeded; ten-request samples contained A/B; both pinned edges verified | E01, E02, E09, E11 | Completed in saved client logs; browser/peer trust screenshots not supplied |
| HTTP caching | Cache-Control public max-age=60; actual ETag sent back; HTTP 304 with empty body | E02, E09 | Completed live, including after IP recovery |
| F: faculty challenge | Toolkit, repeatable faults, and real deployment troubleshooting exist | E08-E11 | Actual faculty-injected fault and individual evaluation remain pending |

DNS baseline at 15:06:13 returned identical records over UDP and TCP. Initial
native HTTPS timed out despite explicit DNS success. Installing the reversible
scoped resolver at 15:09:48 and flushing at 15:10:12 was followed by passing
HTTPS, balancing and caching at 15:10:49-55 [E02]. This demonstrates why explicit
dig success and native macOS application resolution are separate checks; the
logs do not independently identify the precise institutional override mechanism.

For backup DNS, primary service stopped at 15:15:18, caches were flushed and
backup acceptance passed at 15:15:33 [E03]. HTTPS also passed while primary
remained stopped. Primary restarted at 15:16:21 and both-resolver checks passed.
This is stronger evidence than a warm cached HTTPS request alone. The later
packet capture confirms backup DNS traffic but is not the same outage window.

The native observer collected 60 samples from approximately 15:25:52 to
15:27:03. The last observed primary lookup was 15:26:30.056 and the first
standby lookup was 15:26:31.266, accompanied by X-Edge changing to edge-standby.
Mac 1's local record-update log begins at 15:27:10; the earlier peer-side
cutover time is not saved. Therefore the observer proves a live transition,
but cannot establish exactly 30 seconds of cache retention after cutover.
Migration acceptance passed at 15:27:50 after flush, and rollback acceptance
passed at 15:29:41 after restoring primary records [E04, E05]. The independent
3-second forwarding-cache lab records actual expiry and immediate flush effects.

## 4. IP-change recovery and PF troubleshooting

The original privileged-port preflight rejected DNS port 53 before the
sudo-started daemon could bind it (14:56:10). A later DNS start succeeded at
15:03:17. The current manager defers unprivileged permission errors on low ports
to the privileged service's real bind rather than assuming the port is occupied.
Native DNS timeout and scoped-resolver recovery are documented above.

At 15:21:53 the backend restart command reported not ready after isolation,
although both nginx edges served A/B at 15:22:09. The CLI's ordinary-user TCP
probe was being denied by the intended PF UID restriction. The fix uses lsof
to inspect the verified owned PID's exact listening IPv4 address and port,
revalidating ownership before/after inspection without opening backend traffic.
Missing/wrong listeners and inspection failures remain errors. The local
38-test suite includes a real lifecycle test with socket connections forced to
raise PermissionError. At 16:16:08 the new readiness check successfully confirmed
Backend A on 10.7.12.26:3001 [E08]. No PF exception was added for the CLI user.

At 15:45 and 16:11 the IP-role guard rejected stale configuration after the
address changed. The 16:14 inventory confirms 10.7.12.26; rendering at 16:14:31
regenerated local configurations. At 16:15:51 the real PF rollback cleared only
the project anchor's rules/tables and released its recorded enable reference.
The log says pf disabled after release; this is a reference-count outcome, not
an unconditional global pfctl -d operation [E10]. Primary DNS, Backend A and
standby nginx then restarted successfully on the new IP at 16:16:08-09.

The scoped-resolver set command at 16:16:29 refused to replace an outstanding
backup. Subsequent native HTTPS nevertheless succeeded; the logs do not show
that failed command rewriting the scoped file. In the same test-all run DNS,
HTTPS, A/B balancing, caching and current-target migration checks passed, but
isolation failed because direct A access was possible after PF rollback [E09].
That aggregate run is recorded as FAIL and is not relabeled successful.

PF syntax passed at 16:20:27. Apply at 16:20:30 was refused because the local
rollback-rehearsal marker did not match the changed-IP rules. At 16:21:47 apply
succeeded, the status log showed active project rules, and isolation passed
with both healthy edges [E11]. The intervening rehearsal transcript is not saved;
only the gate's refusal and later successful apply are directly evidenced.
There is no complete saved test-all PASS after the IP change: its non-isolation
checks passed at 16:16, and isolation passed separately at 16:21. Earlier complete
test-all runs did pass at 15:22 and 15:30 [E06].

## 5. Verified Wireshark evidence and limits

Existing screenshots were visually inspected and both capture files were read
with the installed Wireshark capinfos/tshark tools. Machine-readable results,
file sizes, SHA-256 hashes, parser errors and matching frame samples are saved
in evidence/phase2/pcaps/verification.json; the repeated final QA validation is in final-qa-verification.json. Original captures were not rewritten.

The clean dns-tcp-tls.pcapng contains 72 Ethernet packets on en0, from 15:48:49
to 15:56:35. Frames 17 and 72 are app.codexers.test DNS responses from
10.7.7.242 to 10.7.12.26, A=10.7.7.242, TTL=30. Stream 0 frames 18/19/20 show
the TCP connection from client port 61350 to edge 8443; frame 21 is ClientHello
with the project SNI and frame 24 is ServerHello. Two project ClientHellos and
53 project-port TCP packets are decoded. Frame numbers belong to this saved
export and differ from the screenshots' original larger capture [E12].

The larger dns-tcp-tls.pcap has 1,512 readable packets and a truncated final
packet: tshark exits 14 and capinfos also reports a cut-short file. Its readable
prefix contains 48 project DNS packets, including 13 responses with TTL 30,
and 56 project SNI ClientHellos. It is partial supporting evidence, not a clean
complete capture. Preserve it as-is; the clean pcapng is the preferred artifact.

Final QA replaced 01-dns-query-response.png with a clearly labelled genuine
tshark export from the unchanged clean capture, not a simulated Wireshark UI.
It shows query frame 16 and matching response frame 17, transaction 0x1a47,
response-to=16, answer 10.7.7.242 and TTL 30. The raw .txt/.tsv and original
query-only screenshot under pcaps/originals/ preserve provenance. 02-tcp-handshake.png shows SYN/SYN-ACK/ACK for client port
61667 to 8443, followed by project ClientHello. 03-tls-handshake.png shows
project TLS 1.3 ClientHello/ServerHello, ChangeCipherSpec and encrypted records.
Neither saved capture decodes a plaintext Certificate message on port 8443.
TLS 1.3 encrypts that part of the handshake; certificate validation is supported
by OpenSSL/curl logs, not by a claimed visible Certificate packet. A separately
saved validated TLS 1.2 certificate trace remains an evidence gap if required.
No saved Phase 2 loopback capture is present. The truncated pcap and superseded query-only image remain in the private deployment archive, not the public Git tree; the clean pcapng and corrected export are published.

## 6. Learning summaries


### A - Backup DNS resolver

DNS redundancy requires more than running another process: clients must know
both server addresses and both services must return consistent records. A warm
cache can hide a DNS outage, so a successful HTTPS request alone does not prove
backup resolution. The local experiment showed that retry policy affects when
fallback occurs. The live stop-and-flush test additionally verified native resolution and HTTPS
through the backup. Packet captures independently show backup DNS answers,
although they were recorded later than that outage test. Application availability remains a separate path after lookup.

### B - DNS TTL and controlled record change

A record update changes what a DNS server answers immediately, while a cache
can legitimately retain the previous answer until its original TTL expires.
The real forwarding-cache experiment observed that stale answer, a decreasing
remaining TTL, the new answer after expiry, and immediate change after a cache
flush. This explains why planned migration needs a lowered TTL in advance.
The live native observer also recorded the old-to-new edge transition. Its
missing peer cutover timestamp prevents an exact native cache lifetime claim;
existing connections are not moved by a DNS cache flush.

### C - Service isolation

Combining clients and edges on two Macs exposes a limitation of source-IP
allowlists: the client and nginx can have the same address. Effective socket
ownership provides an additional boundary, so the project permits upstream
connections from the nginx worker identity and is designed to block ordinary
client attempts on both hosts; saved reciprocal peer-client proof is missing. Correct evaluation must cover loopback and pre-existing states,
and must show that the backends are healthy through the edge. Scoped changes
and a retained rollback token avoid treating global firewall replacement as
an acceptable classroom shortcut.

### D - High-availability failover

A healthy client-to-edge TLS session can survive failure of a separate upstream
connection. Passive nginx checks use actual request failures to quarantine a
backend, retry another candidate and later probe recovery through traffic.
Both edge templates demonstrated B-only service in local integration tests;
the live primary-edge demo also recorded B-only service and resumed A/B after
A returned. In local tests, both stopped backends produced an explicit 502;
a live both-backends-down transcript remains missing.
This improves backend availability while leaving active-edge failure as a
separate problem.

### E - Controlled edge migration

A standby edge must have compatible application behavior and a certificate
trusted for the same names before DNS can direct clients to it. Independent
edge private keys signed by one CA meet that identity requirement without
moving private keys between Macs. Controlled cutover updates both resolvers,
keeps the old edge serving during the cached-answer window, and observes the
actual edge identity. The saved live tests verify native two-Mac traffic cutover and rollback during
the earlier IP configuration. After IP recovery both edges again served A/B;
a repeat standby-target cutover at the new address is not separately logged.
Controlled migration remains distinct from automatic edge failover.

### F - Faculty-injected troubleshooting

Systematic diagnosis asks which layer last succeeded and chooses a test that
separates competing explanations. An explicit DNS query can work while native
resolution fails; TCP can connect while certificate validation fails; and TLS
can succeed before an upstream 502. The toolkit continues independent checks
to expose those distinctions and bounds external waits. Repeatable fault cards
pair an injection with expected observations, restoration and retesting. The
actual faculty fault must be explained from collected output rather than
guessed from a single symptom.


## 7. Evidence ledger and remaining evaluation items

All E01-E11 paths below are relative to evidence/phase2/runs/. Filenames retain
the actual date/time of execution. Earlier addresses are intentional historical
evidence, not the final deployment address.

E01 - 20261124-145548-586670-tls.txt; 20261124-145558-137733-tls.txt.
Certificate verification and local trust installation.

E02 - 20261124-150613-143356-test.txt;
20261124-150948-444444-scoped-dns.txt;
20261124-151049-397414-test.txt; 20261124-151052-325065-test.txt;
20261124-151055-241606-test.txt. DNS, native recovery, HTTPS, balancing, caching.

E03 - 20261124-151518-479169-service.txt;
20261124-151533-198736-flush-dns.txt; 20261124-151533-343105-test.txt;
20261124-151621-158612-service.txt; 20261124-151621-311822-test.txt.
Primary outage, backup/native success and restoration.

E04 - 20261124-152552-400567-observe.txt;
20261124-152710-509876-records.txt; 20261124-152729-228569-test.txt.
Native edge transition and synchronized record verification. Supporting local
cache experiment: evidence/phase2/ttl-lab.txt and ttl-lab.json.

E05 - 20261124-152750-502402-flush-dns.txt;
20261124-152750-651619-test.txt; 20261124-152914-750367-records.txt;
20261124-152941-638235-flush-dns.txt; 20261124-152941-791907-test.txt.
Standby migration and primary rollback acceptance.

E06 - 20261124-152209-414145-test.txt;
20261124-152214-889199-test.txt; 20261124-153043-650845-test.txt.
Earlier-address isolation and complete test-all passes.

E07 - 20261124-151627-955479-demo.txt. Live backend A stop, B-only service,
A restoration and resumed balancing.

E08 - 20261124-152153-726912-service.txt;
20261124-161608-769330-service.txt. False readiness timeout and corrected new-IP
owned-listener check. Regression evidence: evidence/phase2/local-tests.json,
local-tests.txt and readiness-fix-tests.txt (38/38 full suite).

E09 - 20261124-161629-362298-scoped-dns.txt;
20261124-161629-588130-test.txt. Scoped-backup guard and new-IP test-all with
passing application checks but failed isolation.

E10 - 20261124-161147-714962-inventory.txt;
20261124-161400-738289-inventory.txt; 20261124-161431-132621-render.txt;
20261124-161551-165339-firewall.txt;
20261124-161608-640297-service.txt; 20261124-161609-212881-service.txt.
IP-change guard, current inventory, scoped PF rollback and service recovery.

E11 - 20261124-162030-493568-firewall.txt;
20261124-162048-519481-test.txt; 20261124-162147-089930-firewall.txt;
20261124-162147-224640-firewall.txt; 20261124-162147-295750-test.txt.
Rehearsal gate, failed isolation before policy, successful apply and latest
isolation PASS on the current address.

E12 - evidence/phase2/pcaps/: dns-tcp-tls.pcapng, dns-tcp-tls.pcap,
01-dns-query-response.png, 02-tcp-handshake.png, 03-tls-handshake.png,
verification.json. See Section 5 for exact scope and capture-integrity caveats.

E13 - 20261124-165637-991096-test.txt (under evidence/phase2/runs/), plus
evidence/phase2/qa/current-inventory-check.txt. Latest genuine complete test-all
FAIL and same-QA primary/peer network observations. Topic exports and their
source/published provenance are indexed in evidence/phase2/exports/README.md.

Remaining evaluation work: the actual faculty-injected fault (Extension F),
individual viva, independent saved acceptance from Lakshya's client, current
Mac 2 inventory, and any required TLS 1.2/loopback packet evidence. A fresh full
acceptance run and repeat standby cutover at the new IP would consolidate the
separately passing recovery checks. Submission video/form completion is not
established by the saved logs. These are specific remaining evidence/evaluation
items; DNS, HA, TLS, caching and the documented migration are no longer described
as an unstarted deployment.

## References

CN_Project_Doc.pdf Sections 6-10 defines the assignment. Configuration and
technical references are retained in CONFIGURATION_BUNDLE.md and ARCHITECTURE.md.
The report's results come from the evidence ledger above; local test fixtures,
old-address live tests, post-change tests and packet artifacts remain distinct.

Public publication note: only PF enable-reference values are redacted in four
historical public logs. The originals remain in the private deployment archive;
observations and outcomes are not changed. Public export hashes reflect the
published bytes. The 25 November source-publication regression audit is recorded
separately in GITHUB_AUDIT.md; it does not change the last live acceptance result.
