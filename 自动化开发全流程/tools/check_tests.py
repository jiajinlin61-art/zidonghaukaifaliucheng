"""Run unittest discovery and fail when a project has no collected tests."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import unittest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("start", nargs="?", default="tests")
    args = parser.parse_args()
    sys.path.insert(0, str(Path.cwd()))
    suite = unittest.defaultTestLoader.discover(args.start, pattern="test*.py")
    count = suite.countTestCases()
    if count == 0:
        print("test discovery failed: zero tests collected")
        return 1
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
