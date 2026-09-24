import unittest

from installer.content import merge_json, merge_managed_block


class InstallerContentTests(unittest.TestCase):
    def test_merge_json_preserves_unknown_fields(self):
        self.assertEqual(
            merge_json('{"custom":{"keep":true}}', {"behavior": "auto"}),
            '{\n  "custom": {\n    "keep": true\n  },\n  "behavior": "auto"\n}\n',
        )

    def test_merge_managed_block_replaces_only_owned_region(self):
        result = merge_managed_block(
            "user before\n\n<!-- start -->\nold\n<!-- end -->\n\nuser after\n",
            "<!-- start -->\nnew\n<!-- end -->",
            "<!-- start -->",
            "<!-- end -->",
        )
        self.assertIn("user before", result)
        self.assertIn("user after", result)
        self.assertIn("new", result)
        self.assertNotIn("old", result)

    def test_merge_managed_block_rejects_incomplete_region(self):
        with self.assertRaises(ValueError):
            merge_managed_block("<!-- start -->\nold", "new", "<!-- start -->", "<!-- end -->")


if __name__ == "__main__":
    unittest.main()
