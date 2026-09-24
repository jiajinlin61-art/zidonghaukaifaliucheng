from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.environment_check import inspect_environment


class EnvironmentCheckTest(unittest.TestCase):
    def test_current_and_stale_editable_paths(self):
        root=Path(__file__).resolve().parents[1]
        for origin,expected in [(root/'src/uads/__init__.py',False),
                                (root/'moved-away/uads/__init__.py',True),
                                (None,True)]:
            def find(name):
                return SimpleNamespace(origin=str(origin)) if name=='uads' and origin else (
                    SimpleNamespace(origin='yaml') if name=='yaml' else None)
            with patch('tools.environment_check.importlib.util.find_spec',side_effect=find), patch(
                    'tools.environment_check.subprocess.run',return_value=SimpleNamespace(returncode=0)):
                issues=inspect_environment(root)
                self.assertEqual(any('editable' in item for item in issues),expected)
