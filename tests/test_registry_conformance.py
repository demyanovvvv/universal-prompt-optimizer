import unittest

from registry_conformance import check


class RegistryConformanceTests(unittest.TestCase):
    def test_registry_and_adapters_are_aligned(self):
        self.assertEqual(check(), [])


if __name__ == "__main__":
    unittest.main()
