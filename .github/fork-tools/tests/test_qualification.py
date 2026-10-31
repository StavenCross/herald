import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('qualification', Path(__file__).resolve().parents[1] / 'qualification.py')
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


class QualificationTest(unittest.TestCase):
    def test_permission_increase_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'permission'):
            q.permissions({'finish-args': ['--filesystem=home']})
        q.permissions({'finish-args': sorted(q.ALLOWED)})

    def test_exported_permission_increase_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'permission'):
            q.metadata_permissions('[Context]\nshared=network;ipc;\nfilesystems=host;\n')
        q.metadata_permissions('[Context]\nshared=network;ipc;\nsockets=x11;\ndevices=dri;\n')

    def test_private_paths_and_tokens_are_rejected_without_printing_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'AGENTS.md').write_text('private')
            with self.assertRaisesRegex(ValueError, 'AGENTS.md'):
                q.scan(root)
            (root / 'AGENTS.md').unlink()
            token = 'ghp_' + 'X' * 36
            (root / 'settings.json').write_text(token)
            with self.assertRaises(ValueError) as error:
                q.scan(root)
            self.assertNotIn(token, str(error.exception))

    def test_credential_across_read_boundary_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'payload').write_bytes(b' ' * (1024 * 1024 - 10) + b'ghp_' + b'X' * 36)
            with self.assertRaisesRegex(ValueError, 'credential'):
                q.scan(root)

    def test_exported_bus_access_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'permission'):
            q.metadata_permissions('[Session Bus Policy]\norg.freedesktop.secrets=talk\n')

    def test_archive_contents_are_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(root / 'app.jar', 'w') as archive:
                archive.writestr('local-docs/notes.md', 'private')
            with self.assertRaisesRegex(ValueError, 'private path'):
                q.scan(root)

    def test_runtime_selection_preserves_locked_dependencies(self):
        manifest = {'finish-args': list(q.ALLOWED), 'runtime-version': '26.08',
                    'modules': [{'sources': [{'type': 'git', 'commit': 'old'}, {'sha512': 'keep'}]}]}
        out = q.select(manifest, 'a' * 40, 'master', '27.08')
        self.assertEqual(out['modules'][0]['sources'][0]['commit'], 'a' * 40)
        self.assertEqual(out['modules'][0]['sources'][1], {'sha512': 'keep'})
        self.assertEqual(out['runtime-version'], '27.08')
        with self.assertRaises(ValueError):
            q.select(manifest, 'bad', 'master', '../../bad')

    def test_ordinary_package_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'LICENSE').write_text('Public license')
            q.scan(root)
