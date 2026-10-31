import importlib.util
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('checks', ROOT / 'fork-tools/checks.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class CheckSelectionTest(unittest.TestCase):
    def test_actual_upstream_commands_preserved_in_order(self):
        workflow = yaml.safe_load((ROOT / 'workflows/ci.yml').read_text())
        selected = checks.commands(workflow)
        self.assertIn(':androidApp:assembleDev', selected[0][1])
        self.assertIn(':wearApp:lintDebug', selected[0][1])
        self.assertIn('Lorg/jni_zero/', selected[1][1])

    def test_upstream_step_rename_fails_closed(self):
        with self.assertRaises(ValueError):
            checks.commands({'jobs': {'build': {'steps': []}}})

    def test_actions_expression_is_not_executed_as_shell(self):
        steps = [{'name': 'Test, build and lint', 'run': 'echo ${{ secrets.KEY }}'},
                 {'name': "R8 kept WebRTC's JNI classes", 'run': 'true'}]
        with self.assertRaisesRegex(ValueError, 'Actions expressions'):
            checks.commands({'jobs': {'build': {'steps': steps}}})
