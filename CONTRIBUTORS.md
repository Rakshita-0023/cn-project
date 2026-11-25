# Contributors and project responsibilities

Private Network Service Platform - Codexers. Both people contributed to the
project; Git author statistics alone do not describe the team's deployment work.

## Rakshita - [@Rakshita-0023](https://github.com/Rakshita-0023)

Mac 1: primary DNS, Backend A, standby nginx and client/evidence collection.
The published Git history through 8927dc0 records Rakshita as the author of
all six commits. The source-publication audit and submission preparation are
documented in GITHUB_AUDIT.md. This recorded author history is preserved.

## Lakshya - [@Lakshyalamba](https://github.com/Lakshyalamba)

The team confirmed the following genuine work on 25 November 2026:

| Contribution | Corresponding repository areas |
|---|---|
| Backup DNS configuration and DNS failover testing | phase2/templates/dnsmasq.conf.template; phase2/config.py; phase2/probes.py; DNS-failover evidence exports |
| Backend B deployment and backend redundancy testing | backend/backend_b.py; phase2/backend_runner.py; phase2/services.py; backend failover/recovery evidence |
| Primary nginx reverse proxy and load balancing configuration | nginx/nginx.conf.template; phase2/templates/nginx.conf.template; nginx setup/runbooks; balancing evidence |
| Two-Mac network integration and connectivity testing | architecture and deployment documents; inventory/connectivity procedures and evidence |
| PF isolation configuration and troubleshooting | phase2/firewall.py; phase2/rollback_rehearsal.py; PF configuration specimens; isolation/rollback evidence |
| Phase 2 HA, controlled edge migration and live verification | phase2/network.py; phase2/probes.py; deployment/demo procedures; HA/migration/TTL evidence |

This table maps confirmed work to its implementation and evidence locations.
It does not assert that one person solely wrote every listed file, assign
unverified line ownership, or create missing peer-side test evidence. Existing
logs retain their actual host, result and timestamp; the deployment acceptance
gaps and pending faculty challenge remain in SUBMISSION_CHECKLIST.md.

## Historical authorship and future changes

Commit 8927dc0 combined many already-completed changes when the deployment folder
was first published from a downloaded copy. This contribution record explains
team responsibilities without changing that commit's author or splitting its
published history. Any retrospective author correction/history rewrite requires
separate approval and a verified commit-by-commit contribution mapping.

Future commits must identify the real human author. Co-author trailers are used
only for genuine shared authorship, with each person's approval of the name and
GitHub-associated email used. No automated assistant is added as an author or
co-author. See CONTRIBUTING.md for the commit and validation workflow.

Lakshya reviewed and approved this contribution record and its new documentation
author attribution on 25 November 2026, as relayed by Rakshita. That approval
does not retroactively reassign earlier source commits or certify missing tests.
