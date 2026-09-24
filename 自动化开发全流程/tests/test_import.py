import unittest

import uads


class PackageImportTest(unittest.TestCase):
    def test_package_imports(self):
        self.assertEqual(uads.__version__, "0.1.0")
