import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'policy.py'


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.commit('app.txt', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        spec = importlib.util.spec_from_file_location('policy', SCRIPT)
        self.policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.policy)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def commit(self, name, value):
        p = self.repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value)
        self.git('add', name)
        self.git('commit', '-qm', 'Fixture')

    def test_feature_from_upstream_is_clean(self):
        self.commit('app.txt', 'feature')
        self.policy.check_contribution(self.repo, self.base, 'HEAD')

    def test_deleted_fork_file_still_rejected_from_history(self):
        name = '.github/workflows/fork-sync.yml'
        self.commit(name, 'private automation')
        self.git('rm', name)
        self.git('commit', '-qm', 'Remove automation')
        with self.assertRaisesRegex(ValueError, 'fork-sync'):
            self.policy.check_contribution(self.repo, self.base, 'HEAD')

    def test_deleted_unicode_fork_file_still_rejected(self):
        name = '.github/workflows/fork-café.yml'
        self.commit(name, 'automation')
        self.git('rm', name)
        self.git('commit', '-qm', 'Remove automation')
        with self.assertRaisesRegex(ValueError, 'Fork-only'):
            self.policy.check_contribution(self.repo, self.base, 'HEAD')

    def test_sync_preserves_automation_and_integrates_upstream(self):
        self.commit('.github/workflows/fork-sync.yml', 'automation')
        self.git('branch', 'fork-master')
        self.git('checkout', '-q', '-b', 'upstream', self.base)
        self.commit('app.txt', 'new upstream')
        self.git('checkout', '-q', 'fork-master')
        self.assertTrue(self.policy.sync(self.repo, 'upstream'))
        self.assertEqual((self.repo / 'app.txt').read_text(), 'new upstream')
        self.assertEqual((self.repo / '.github/workflows/fork-sync.yml').read_text(), 'automation')
        self.assertFalse(self.policy.sync(self.repo, 'upstream'))

    def test_sync_rejects_unexpected_feature_without_modifying_head(self):
        self.commit('app.txt', 'unapproved fork feature')
        before = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'app.txt'):
            self.policy.sync(self.repo, self.base)
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)

    def test_conflict_aborts_without_changing_branch(self):
        name = '.github/workflows/fork-sync.yml'
        self.commit(name, 'fork version')
        before = self.git('rev-parse', 'HEAD')
        self.git('branch', 'fork-master')
        self.git('checkout', '-q', '-b', 'upstream', self.base)
        self.commit(name, 'upstream version')
        self.git('checkout', '-q', 'fork-master')
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.policy.sync(self.repo, 'upstream')
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_untracked_files_refuse_sync(self):
        (self.repo / 'untracked').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'clean'):
            self.policy.sync(self.repo, self.base)


if __name__ == '__main__':
    unittest.main()
