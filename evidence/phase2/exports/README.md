# Genuine evidence exports: quick navigation

These are actual saved command outputs, copied from runs/ (PF enable-reference values are redacted in public copies only). Their
original source filenames and published SHA-256 hashes are in provenance.json. They are exports,
not newly executed tests or artificial screenshots. Original timestamps, old IPs,
intermediate failures and warnings are intentionally retained.

| Required evidence | Export / packet artifact | Scope |
|---|---|---|
| DNS resolution | dns-resolution.txt; ../pcaps/01-dns-query-response.png/.txt/.tsv | Both resolver UDP/TCP answers; real matching DNS pair |
| HTTP headers / validated HTTPS | https-headers.txt; tls-verification.txt | Actual curl headers and SAN/CA checks |
| A/B balancing | load-balancing.txt | Ten real responses; both X-Backend values |
| ETag/304 caching | etag-304-caching.txt | Cache-Control, real ETag and empty 304 |
| Firewall isolation | firewall-isolation-current-ip.txt | Direct A/B fail; both healthy edges serve A/B; Rakshita client only |
| Backend HA | backend-failover-recovery.txt | A/B -> B-only -> A/B; earlier Rakshita IP |
| DNS failover | dns-failover.txt | Primary unavailable, backup answers, native lookup and HTTPS work |
| TTL and migration | ttl-migration-observer.txt; standby-migration.txt; migration-rollback.txt | Live transition and rollback; exact peer cutover timestamp absent |
| PF rollback | pf-rollback.txt | Actual scoped rule/table removal and reference release |
| Current acceptance | latest-acceptance-FAIL.txt | Genuine final QA test-all FAIL; never treated as PASS |
| TCP handshake | ../pcaps/02-tcp-handshake.png; clean pcapng stream 0 | SYN/SYN-ACK/ACK; screenshot port 61667, export port 61350 |
| TLS handshake | ../pcaps/03-tls-handshake.png; clean pcapng frames 21/24 | TLS 1.3 hello messages; not a plaintext Certificate trace |

The clean capture and current images are in ../pcaps/. The original DNS
query-only image is preserved in ../pcaps/originals/ but superseded for evaluation.
The larger pcap is partial; final-qa-verification.json records parsing errors.
No screenshot pages were appended to the final report. All missing evidence and
exact collection steps are in ../../../SUBMISSION_CHECKLIST.md.
