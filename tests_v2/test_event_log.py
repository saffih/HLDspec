import unittest
import tempfile
from pathlib import Path

from hldspec.event_log import HldspecEvent, append_event, read_events, make_event_id


def _make_event(event_id: str = "test-id", machine: str = "TestMachine") -> HldspecEvent:
    return HldspecEvent(
        event_id=event_id,
        timestamp=1000.0,
        machine=machine,
        from_state="STATE_A",
        to_state="STATE_B",
        event="some_event",
    )


class TestAppendEvent(unittest.TestCase):
    def test_creates_file_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "subdir" / "events.jsonl"
            self.assertFalse(log_path.exists())
            append_event(log_path, _make_event())
            self.assertTrue(log_path.exists())


class TestReadEvents(unittest.TestCase):
    def test_returns_empty_list_if_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = read_events(Path(tmp) / "nonexistent.jsonl")
            self.assertEqual(result, [])

    def test_round_trips_single_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "events.jsonl"
            event = _make_event("evt-001")
            append_event(log_path, event)
            result = read_events(log_path)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].event_id, "evt-001")
            self.assertEqual(result[0].machine, "TestMachine")
            self.assertEqual(result[0].from_state, "STATE_A")
            self.assertEqual(result[0].to_state, "STATE_B")

    def test_round_trips_multiple_events_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "events.jsonl"
            for i in range(3):
                append_event(log_path, _make_event(f"evt-{i:03d}", machine=f"Machine{i}"))
            result = read_events(log_path)
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0].event_id, "evt-000")
            self.assertEqual(result[1].event_id, "evt-001")
            self.assertEqual(result[2].event_id, "evt-002")

    def test_malformed_lines_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "events.jsonl"
            append_event(log_path, _make_event("good-event"))
            # Append a malformed line
            with log_path.open("a") as f:
                f.write("not valid json\n")
            append_event(log_path, _make_event("good-event-2"))
            result = read_events(log_path)
            # Two good events, malformed line skipped
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0].event_id, "good-event")
            self.assertEqual(result[1].event_id, "good-event-2")


class TestMakeEventId(unittest.TestCase):
    def test_returns_non_empty_string(self):
        result = make_event_id("MyMachine", "MY_STATE")
        self.assertIsInstance(result, str)
        self.assertTrue(result)

    def test_contains_machine_name(self):
        result = make_event_id("ProjectMachine", "NO_WORKSPACE")
        self.assertIn("ProjectMachine", result)

    def test_contains_from_state(self):
        result = make_event_id("ProjectMachine", "NO_WORKSPACE")
        self.assertIn("NO_WORKSPACE", result)


if __name__ == "__main__":
    unittest.main()
