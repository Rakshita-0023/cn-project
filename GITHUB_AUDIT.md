# Final GitHub publication audit - 25 November 2026

Repository: https://github.com/Rakshita-0023/cn-project - default branch **main**.
The original deployment folder is a downloaded copy without `.git`. A clean
checkout of remote main was used for publication so that existing history and
private deployment material remain intact.

## Baseline and contributor preservation

Remote baseline: `e25a51e758f7d529e049ec98b82c841f50cc7e6e` (Add Codexers team
enrollment details). Five Phase 1 commits and 60 originally tracked files were
inspected; origin advertised only main. Before changes, HEAD and origin/main
matched. No remote-tracked file was missing in the local deployment copy.
Shared-file differences were the expected Phase 2 additions to scripts/_common.py,
README, ARCHITECTURE, configuration index and .gitignore. Phase 1 backend source,
templates and launchers were unchanged. All remote-only content was preserved;
no force push, reset, rebase or history rewrite was used. Unpublished files on
Lakshya's Mac cannot be inferred from GitHub and still require his confirmation.

## Security/privacy review

All 80 historical blobs were checked for private-key, GitHub-token and numeric
PF enable-reference patterns: none found. No committed credential was identified;
pattern checks are supplemented by image/capture review and are not a proof that
every possible secret format is detectable. The unrelated background-TLS image
was already present in old commits. It is removed from the new public tree,
while its local original and prior Git history are preserved. If the team wants
that old image removed from history for privacy, that requires a separate,
explicitly authorized history-cleanup decision; it was not done here.

Private keys/cert runtime directories, environment backups, rollback records,
PID files, generated/runtime directories, caches, unrelated background traffic,
partial raw capture, superseded original DNS image, ZIPs and machine-bound CSR
handoff artifacts are excluded. Public portable configuration examples, relevant
original screenshots and the clean 72-packet project capture are retained.
`.gitignore` also guards future raw firewall logs; already tracked files still
require index scanning before publication.

Four genuine public log copies redact ONLY numeric PF enable-reference values:

- `evidence/phase2/exports/pf-rollback.txt`
- `evidence/phase2/runs/20261124-152122-910379-firewall.txt`
- `evidence/phase2/runs/20261124-161551-165339-firewall.txt`
- `evidence/phase2/runs/20261124-162147-089930-firewall.txt`

Raw local originals remain in the private deployment archive. Public export
hashes reflect published bytes, with the redaction scope recorded in provenance.
Statuses, timestamps, observations and non-sensitive command content are not
changed. These are redacted command exports, not manufactured successes.

## Deliverables and safe validation

The root README maps architecture, configuration, source, evidence, report and
all 11 demo steps. Original Phase 1 instructions are retained in
[docs/PHASE1_RUNBOOK.md](docs/PHASE1_RUNBOOK.md). The final PDF remains a concise
report; screenshots/exports are in evidence. Certificate keys and live settings
are intentionally absent from a fresh clone; the fresh-start guide documents
dependency installation, current-IP initialization and public CSR transfer.

Publication regression suite: **38/38 PASS**, zero failures/errors/skips,
executed 2026-11-25T14:09:51.200728+05:30. Real temporary loopback processes and test TLS
material were isolated from the deployed services. Tests did not change live
DNS, PF, trust, deployed keys or service state. The latest publication test JSON
and text are in evidence/phase2/local-tests.*. Historical live results are indexed
separately; no new live acceptance or fault demo was run for Git publication.

Index/path/secret scan: `python3 scripts/check_publication.py --history`.
Static Python/shell checks, Git diff/integrity checks, internal-link review,
clean-capture protocol/size/hash verification and PDF rendering/visual review
are publication gates. Stage only explicit reviewed file paths; no blind
`git add .` is used. Remote HEAD is re-fetched immediately before a normal push;
a changed remote baseline or non-fast-forward rejection must be resolved safely
rather than overwritten. Actual final commit/push verification is reported in
the completion response, not guessed or self-referenced inside this commit.

## Readiness limits

**Source publication is distinct from faculty acceptance.** The latest saved
live acceptance remains FAIL at 24 Nov 16:56:37. Backup DNS and primary-edge
service paths timed out despite peer ping replies. Historical A-E successes
remain correctly labelled. Extension F, individual viva, reciprocal-client
acceptance, peer inventory, precise native TTL timing and missing live Phase 1
failure evidence remain listed in [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md).
Publishing the source does not authorize live repairs or certify those items.

Git attributes preserve literal evidence whitespace (including empty TSV fields)
and treat PDF/image/capture deliverables as binary. Review-only config specimens
have normalized final newlines; raw command observations are not reformatted.

## Contribution presentation follow-up - 25 November 2026

The published baseline 8927dc0 was clean; no outstanding networking/PF/source
changes remained to split. It is preserved, not retroactively rewritten.
The team confirmed Lakshya's genuine DNS, Backend B, nginx, integration, PF,
HA/migration and live-testing contributions. CONTRIBUTORS.md maps this work
without claiming sole file/line authorship or manufacturing peer evidence.

New focused changes:

- `88953472e4b99a3131dc00d93890304d1bb0de4f`: contribution workflow/identity guidance, authored and committed by Rakshita.
- `ccf767959eefc624e4019749d5962656d773deb2`: reviewed contribution record and README profile links, authored by
  Lakshya with Rakshita as integrating committer. Lakshya's content and author-email
  approval were explicitly relayed by Rakshita before committing. This is a real
  new documentation contribution, not a reassignment of historical code authors.
- A separate validation commit records this follow-up audit and the genuine
  38/38 local regression result observed 2026-11-25T16:20:18.171542+05:30.

No empty/fake phase-specific commits, backdating, history rewriting or automated
assistant author/co-author trailers are used. GitHub already linked public commits
using the approved email to Lakshyalamba; the new repository commit's linked
author is verified after normal push. Contributors statistics may refresh
separately; no UI refresh is assumed from README credit alone. This follow-up
did not alter live services, DNS/PF settings or the historical live-readiness
limitations recorded in SUBMISSION_CHECKLIST.md.
