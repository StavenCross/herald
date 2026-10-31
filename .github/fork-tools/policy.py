#!/usr/bin/env python3
"""Fork maintenance only: safe upstream merges and contribution isolation."""
import argparse
from pathlib import Path
import subprocess


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def fork_only(path):
    return (path.startswith('.github/fork-tools/') or
            path.startswith('.github/workflows/fork-'))


def changed(repo, base, head):
    output = git(repo, 'diff', '--name-only', '-z', base, head)
    return [p for p in output.split('\0') if p]


def check_contribution(repo, upstream, head):
    # Checking history also catches an automation file added then deleted later.
    history = git(repo, 'log', '-m', '--format=', '--name-only', '-z', upstream + '..' + head)
    paths = {p for p in history.split('\0') if p}
    paths.update(changed(repo, git(repo, 'merge-base', upstream, head), head))
    bad = sorted(p for p in paths if fork_only(p))
    if bad:
        raise ValueError('Fork-only files in contribution history: ' + ', '.join(repr(p) for p in bad))
    print('Contribution contains no fork-only automation.')


def sync(repo, upstream):
    if git(repo, 'status', '--porcelain'):
        raise ValueError('Synchronization requires a clean checkout.')
    base = git(repo, 'merge-base', 'HEAD', upstream)
    unexpected = [p for p in changed(repo, base, 'HEAD') if not fork_only(p)]
    if unexpected:
        raise ValueError('Unexpected fork changes; manual review required: ' + ', '.join(unexpected))
    before = git(repo, 'rev-parse', 'HEAD')
    result = subprocess.run(['git', '-C', str(repo), 'merge', '--no-edit', upstream],
                            capture_output=True, text=True)
    if result.returncode:
        # This checkout was proven clean; abort only the merge attempted here.
        subprocess.run(['git', '-C', str(repo), 'merge', '--abort'], check=True)
        raise ValueError('Upstream merge conflict; no update published.\n' + result.stdout + result.stderr)
    unexpected = [p for p in changed(repo, upstream, 'HEAD') if not fork_only(p)]
    if unexpected:
        raise ValueError('Merged tree differs outside fork automation: ' + ', '.join(unexpected))
    return git(repo, 'rev-parse', 'HEAD') != before


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['sync', 'contribution'])
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--upstream', required=True)
    parser.add_argument('--head', default='HEAD')
    args = parser.parse_args()
    if args.mode == 'sync':
        print('Upstream integrated.' if sync(args.repo, args.upstream) else 'Already up to date.')
    else:
        check_contribution(args.repo, args.upstream, args.head)
