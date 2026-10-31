#!/usr/bin/env python3
"""Run upstream's build/lint and JNI checks locally without duplicating commands."""
import argparse
from pathlib import Path
import subprocess
import yaml


def commands(workflow):
    names = ('Test, build and lint', "R8 kept WebRTC's JNI classes")
    steps = workflow['jobs']['build']['steps']
    selected = []
    for name in names:
        matches = [step for step in steps if step.get('name') == name]
        if len(matches) != 1 or not isinstance(matches[0].get('run'), str):
            raise ValueError('Upstream CI changed; review check selection: ' + name)
        if '${{' in matches[0]['run']:
            raise ValueError('Cannot evaluate Actions expressions in local check: ' + name)
        selected.append((name, matches[0]['run']))
    return selected


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.repo.resolve()
    workflow = yaml.safe_load((repo / '.github/workflows/ci.yml').read_text())
    selected = commands(workflow)
    for name, command in selected:
        print(name, flush=True)
        subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', command], cwd=repo, check=True)
    subprocess.run([str(repo / 'gradlew'), '--no-daemon', '--max-workers=2',
                    ':desktopApp:compileKotlinJvm'], cwd=repo, check=True)
    tests = repo / 'packaging/flatpak/tests'
    if tests.is_dir():
        subprocess.run(['python3', '-m', 'unittest', 'discover', '-s', str(tests), '-v'],
                       cwd=repo, check=True)
