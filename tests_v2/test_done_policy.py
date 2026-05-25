"""Tests for DoneStatus done-means-verified policy."""
import unittest
from hldspec.done_policy import DoneStatus


class TestDoneStatus(unittest.TestCase):

    def test_gate_verified_is_complete(self):
        self.assertTrue(DoneStatus.is_complete(DoneStatus.GATE_VERIFIED))

    def test_release_ready_is_complete(self):
        self.assertTrue(DoneStatus.is_complete(DoneStatus.RELEASE_READY))

    def test_tested_is_not_complete(self):
        self.assertFalse(DoneStatus.is_complete(DoneStatus.TESTED))

    def test_implemented_is_not_complete(self):
        self.assertFalse(DoneStatus.is_complete(DoneStatus.IMPLEMENTED))


if __name__ == "__main__":
    unittest.main()
