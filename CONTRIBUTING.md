# Contributing and commit attribution

## Keep changes focused

Use one commit per coherent change. Separate networking service behavior, PF
policy, tests, evidence, and documentation when the changes can be reviewed
independently. Do not manufacture extra commits by touching unchanged Phase 1
or Phase 2 files. Already-published history is not split, amended, rebased or
force-pushed without explicit team approval.

Examples of appropriate subjects for actual changes:

- `fix(dns): correct backup resolver record generation`
- `fix(services): inspect owned backend listeners under PF isolation`
- `fix(firewall): preserve scoped rollback ownership`
- `test(ha): verify backend recovery after passive quarantine`
- `docs: clarify two-Mac setup and contributor responsibilities`
- `evidence: add verified reciprocal-client acceptance output`

## Use the real human identity

Check identity in the actual checkout before committing:

```sh
git config --show-origin --get user.name
git config --show-origin --get user.email
```

Use repository-local identity settings on your own Mac, with YOUR name and an
email connected to YOUR GitHub account (or GitHub-provided noreply email):

```sh
git config --local user.name 'YOUR HUMAN NAME'
git config --local user.email 'YOUR GITHUB-ASSOCIATED EMAIL'
```

Do not change another person's global identity, impersonate a teammate, add
assistant authors/co-authors, invent collaboration, backdate commits or add
unnecessary generated-message footers. For genuine shared work, obtain the
co-author's approval of the exact name/email before using a `Co-authored-by`
trailer. A README credit is useful but does not itself change Git authorship.
Commit authorship, signature verification and GitHub's cached Contributors
presentation are separate facts; verify the commit's linked account through
GitHub, and do not promise immediate graph updates.

## Validate and publish safely

```sh
git fetch origin
git status --short --branch
git log --oneline origin/main..HEAD
make test-local
```

Local regressions use temporary loopback processes and test certificates. Do not
stop/restart live services, alter PF/DNS/trust, replace deployed keys or inject
faults as a contribution check. Preserve real historical evidence and describe
live failures honestly. Missing peer tests or faculty evaluation stay pending.

Stage explicit reviewed paths, inspect the cached diff and run:

```sh
git diff --cached --check
python3 scripts/check_publication.py --history
git diff --cached --stat
git diff --cached
```

The checker inspects the actual index, including already-tracked files. Never
stage keys, credentials, raw PF references, environment backups, generated
runtime state, unrelated captures or caches. Gitignore does not protect a
tracked file that was later overwritten with private data. Redacted evidence
must record its transformation and public hashes; raw local originals remain
private. Do not normalize original packet or transcript bytes to hide failures.

Before a normal push, inspect remote divergence and preserve teammates' work.
Stop on unexpected divergence/conflicts instead of resetting or force-pushing.
After pushing, verify remote HEAD, human author/linked GitHub account, and a
clean working tree. Contributors UI statistics may update separately from the
underlying commits. See [GitHub's contributor guidance](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors)
and [co-author guidance](https://docs.github.com/en/pull-requests/how-tos/commit-changes/creating-a-commit-with-multiple-authors).
