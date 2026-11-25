# File changes and delivery map

The original deployment folder was downloaded without `.git`. The GitHub audit uses a clean checkout of the existing remote history, preserving both source and private deployment material; see GITHUB_AUDIT.md at the project root.

## Existing files edited

| File | Exact change |
|---|---|
| `README.md` | Added Phase 2 entry points and links; kept the complete original Phase 1 instructions/history |
| `ARCHITECTURE.md` | Added a link to the updated topology; retained the original architecture |
| `.gitignore` | Ignore Phase 2 generated/runtime/TLS material and temporary PDF QA output |
| `scripts/_common.py` | Accept five optional Phase 2 configuration keys; allow a validated list of client DNS servers while preserving original backup/restore behavior; exclude temporary artifact QA directories from the zip |

The backend source, original DNS/nginx templates, test suite, TLS launchers and
existing screenshots remain unchanged. Phase 2 backend launch reuses the same
HTTP implementation.

## New implementation files

- `Makefile`: operations, tests, failure demos, restoration and packaging.
- `phase2/__init__.py`: package marker.
- `phase2/config.py`: extended validation, IP detection, role mapping, atomic snapshots, DNS state and rendering.
- `phase2/services.py`: PID ownership, port conflicts, local-role checks, service start/stop/restart/readiness.
- `phase2/backend_runner.py`: explicit configured backend LAN bind, preserving the original application behavior.
- `phase2/tls.py`: CA, independent edge CSR/key, public-only signing, SAN/chain/key verification.
- `phase2/firewall.py`: UID-aware PF rule renderer, root-anchor/loopback preflight, scoped installation and rollback.
- `phase2/probes.py`: real DNS, native resolution, TCP, TLS, HTTP, isolation, migration and diagnostic assertions.
- `phase2/network.py`: CLI, Makefile backend, logged operations, failure recovery, scoped resolver, record publication and cleanup.
- `phase2/templates/dnsmasq.conf.template`: primary/backup exact names and TTL.
- `phase2/templates/nginx.conf.template`: active/standby edge, TLS, identity header and passive HA.
- `phase2/tests/__init__.py`, `test_phase2.py`, `run_tests.py`: new safety/integration cases and actual test-result export.
- `phase2/build_report.py`: generates results index and printable report from executed tests (optional ReportLab dependency).

## New deliverables and evidence

- `phase2/README.md`: complete fresh-start and shutdown guide, with exact commands per Mac.
- `docs/phase2/ARCHITECTURE.md`, `architecture.svg`, `architecture.png`: role/IP inventory, request flow, failure boundaries and visual topology.
- `docs/phase2/CONFIGURATION_BUNDLE.md`, `config-examples/`: source/config inventory and clearly labeled rendered examples.
- `docs/phase2/FINAL_REPORT.md`: implementation changes, validation, limitations and one learning paragraph per extension.
- `docs/phase2/TEST_RESULTS.md`: actual per-case results and pending live acceptance template.
- `docs/phase2/DEMO.md`: all 11 Section 8 steps and Phase 2 capture commands.
- `docs/phase2/TROUBLESHOOTING.md`: repeatable faults, diagnosis and restoration.
- `docs/phase2/VIVA.md`: individual preparation across the entire system.
- `docs/phase2/CHANGES.md`: this exact file map.
- `evidence/lan/inventory-laptop1.json`: genuine current local inventory.
- `evidence/phase2/`: original baseline, final tests/JSON, failed/debugging runs, TTL lab, dependency checks and actual CLI logs; `README.md` indexes them.
- `output/pdf/phase2-final-report.pdf`: visually reviewed printable report.
- `scripts/runtime/cn-project.zip`: packaged source, public configuration/report artifacts and actual evidence; runtime directories and private material excluded.

Full archive membership is inspected during packaging. No `.key`, `.pem`,
machine-specific `network.env`, PID files, generated/runtime directories or
temporary PDF images are included. New Phase 2 live captures/screenshots and
the faculty challenge result remain for the team to collect.

## Final submission QA additions

Current delivery uses `make submission`, `scripts/prepare_submission.py`, a dated
submission directory and `output/submission/cn-project-phase2-submission.zip`.
The earlier `scripts/runtime/cn-project.zip` is a historical package. New QA
files: root SUBMISSION_CHECKLIST.md, scripts/collect_acceptance.sh (read-only),
scripts/export_submission_evidence.py, topic exports/provenance, corrected DNS
image/raw export with original preserved, final-qa-verification.json, and
current-configuration/ review specimens. Working service/configuration modules
were not changed by final QA. Latest acceptance FAIL remains in the report.
