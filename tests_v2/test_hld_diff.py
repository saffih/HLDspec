import unittest

from hldspec import hld_diff
from hldspec import hld_marking as hm

BASE = """# HLD

## HLD-001 - Purpose

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW

### Purpose
Alpha.

## HLD-002 - Engine

HLD-ID: HLD-002
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: LOW

### Purpose
Beta.
"""


class DiffTests(unittest.TestCase):
    def test_no_change(self):
        diff = hld_diff.diff_hlds(BASE, BASE)
        self.assertFalse(diff.any_change)

    def test_added_anchor(self):
        new = BASE + "\n## HLD-003 - New\n\nHLD-ID: HLD-003\nHLD-ROLE: x\nHLD-STATUS: active\nHLD-RISK: LOW\n\n### Purpose\nGamma.\n"
        diff = hld_diff.diff_hlds(BASE, new)
        self.assertEqual(diff.added, ["HLD-003"])
        self.assertEqual(diff.deleted, [])

    def test_changed_anchor(self):
        new = BASE.replace("Beta.", "Beta changed.")
        diff = hld_diff.diff_hlds(BASE, new)
        self.assertEqual(diff.changed, ["HLD-002"])

    def test_deleted_anchor(self):
        new = BASE.split("## HLD-002")[0]
        diff = hld_diff.diff_hlds(BASE, new)
        self.assertEqual(diff.deleted, ["HLD-002"])

    def test_moved_anchor_same_hash(self):
        # Insert a blank line before HLD-002 so its line range shifts but text is identical.
        new = BASE.replace("## HLD-002 - Engine", "\n## HLD-002 - Engine")
        diff = hld_diff.diff_hlds(BASE, new)
        self.assertIn("HLD-002", diff.moved)
        self.assertNotIn("HLD-002", diff.changed)


if __name__ == "__main__":
    unittest.main()
