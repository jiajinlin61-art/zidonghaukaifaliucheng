import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "tools/check_tests.py"


class TestEntryPointTest(unittest.TestCase):
    def test_empty_pass_and_failed_suites(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            fixture = target / "test_fixture.py"
            for body, expected in [
                (None, 1),
                ("import unittest\nclass Example(unittest.TestCase):\n    def test_case(self): self.assertTrue(True)\n", 0),
                ("import unittest\nclass Example(unittest.TestCase):\n    def test_case(self): self.fail('expected failure')\n", 1),
            ]:
                with self.subTest(expected=expected, body=body):
                    if body is not None:
                        fixture.write_text(body, encoding="utf-8")
                    result = subprocess.run([sys.executable, "-B", str(RUNNER), str(target)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                    if body is None:
                        self.assertIn("zero tests", result.stdout)
