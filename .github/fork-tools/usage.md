# Personal fork automation

These files belong only to StavenCross/kyllene. They are not upstream contributions.

Fork upstream sync checks Giton22/kyllene master at 00:17, 06:17, 12:17 and 18:17
UTC, and supports manual runs. GitHub may delay schedules or disable them after
60 days without repository activity. A no-change run does not rebuild the app.
The manual validate option runs application checks even without upstream changes.

The policy allows master to differ only under `.github/fork-tools/` and
`.github/workflows/fork-*`. It tests a normal merge locally, then uses GitHub's
fork-sync API and verifies the resulting tree. Conflicts, unexpected app changes,
concurrent updates or insufficient token permissions fail visibly. It never
force-pushes, resets feature branches, changes releases or installs applications.
The API update is not an atomic compare-and-swap: a concurrent update can cause
a reported failure after synchronization has occurred; inspect the remote before retrying.
A separate read-only job tests the resulting SHA; a failed test does not revert
upstream synchronization. Checks run in the same workflow because updates made
with GITHUB_TOKEN do not normally trigger another push workflow.

Start contributions from Giton22 master or a documented clean feature parent,
never fork master. Open a PR in this fork to run CI before proposing the tested
head upstream. Do not merge feature PRs into fork master. After an upstream
squash merge, move only the child's own commits onto current upstream.

Fork contribution isolation runs trusted master policy on Git history only; it
never executes PR code. It rejects fork-only files even if later deleted. It
runs on fork PRs and manually for a named branch. It cannot prevent a human from
bypassing this process and opening an upstream PR directly.

Local checks (requires Python/PyYAML, JBR 25 and Android SDK per CONTRIBUTING):

```sh
python3 .github/fork-tools/checks.py --repo /path/to/contribution-worktree
python3 .github/fork-tools/policy.py contribution --repo /path/to/contribution-worktree --upstream origin/master --head HEAD
python3 -m unittest discover -s .github/fork-tools/tests -v
```

Run these scripts from the maintenance checkout, not by copying them into a
feature branch. The check runner reads upstream CI's actual build/lint/JNI
commands and adds desktop compilation and available packaging contracts. It does
not substitute for the Linux workflow's offline package build or Bazzite's real
GUI, portal, hardware and voice acceptance. Keep those results tied to exact SHAs.
