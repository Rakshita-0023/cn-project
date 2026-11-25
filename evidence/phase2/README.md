# Phase 2 evidence index

Only executed commands and real test observations belong here. No synthetic
screenshots, packet captures or two-Mac success claims have been generated.

| File / directory | Meaning |
|---|---|
| `phase1-baseline.txt` | Original 19-test local regression run before implementation |
| `local-tests.txt`, `local-tests.json` | Latest combined suite, per-case statuses and real output |
| `attempt1-local-tests.txt`, `.json` | Preserved initial run with DNS retry and nginx recovery timing failures |
| `focused-debug-tests.txt` | Intermediate focused debugging run; retains its failed DNS check |
| `dns-retry-debug.txt` | Executed corrected DNS fallback test |
| `service-lifecycle-check.txt` | Executed new backend lifecycle/conflict check |
| `current-mac-inventory.txt` | Actual current Mac 1 observation; JSON also in `evidence/lan/` |
| `runs/*.txt`, `runs/results.jsonl` | Actual operational CLI logs and command exit results |
| `ttl-lab.txt`, `.json` | Standalone real forwarding-cache TTL/flush run when `make ttl-lab` is executed |
| `live/` | Add actual two-Mac captures, screenshots and signed-off results here |

A PASS for rendering/setup/validation records that command's success, not a live
deployment result. Mock-based safety tests are labeled by their case names;
they are not firewall or OS-DNS enforcement evidence. DNS/nginx integration tests
use real local processes. `pfctl -n` verifies syntax without loading rules.

Complete the pending live matrix in `docs/phase2/TEST_RESULTS.md`, referencing
actual filenames, times, both host identities and observed packet numbers.
Keep failure and recovery evidence together. Historical screenshots under the
original evidence directories are Phase 1 artifacts, not Phase 2 proof.

## Final QA update

Use [topic exports](exports/README.md) to find evidence within 30 seconds and
[the submission checklist](../../SUBMISSION_CHECKLIST.md) for remaining gaps.
The latest genuine complete acceptance is FAIL at 16:56:37, 24 November; earlier
passing runs are historical. `pcaps/01-dns-query-response.png` is now a clearly
labelled genuine tshark export of matching frames 16/17; the old image survives
under pcaps/originals/. Raw export text/TSV and capture-validation JSON provide
provenance. Phase 1 historical TLS 1.2 screenshots are separate from current
TLS 1.3 evidence. No live service or setting was changed during final QA.

Public copies of four PF logs redact enable-reference values; original private
logs are not replaced. All other output observations and outcomes are retained.
See ../../GITHUB_AUDIT.md and exports/provenance.json.
