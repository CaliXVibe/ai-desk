"""Two users, one bot write, the other partition stays empty."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo.night_desk import ingest
from demo.store import DeskStore

A = "demo@atlas.local"
B = "other@atlas.local"
SAMPLE = (ROOT / "examples" / "sample-job.txt").read_text(encoding="utf-8")
NOW = datetime(2026, 9, 12, 18, 0, tzinfo=timezone.utc)


class IsolationTests(unittest.TestCase):
    def test_both_desks_start_empty(self) -> None:
        store = DeskStore()
        self.assertEqual(store.counts(A), {"mail": 0, "files": 0, "calendar": 0})
        self.assertEqual(store.counts(B), {"mail": 0, "files": 0, "calendar": 0})

    def test_bot_write_for_a_leaves_b_empty(self) -> None:
        store = DeskStore()
        artifacts = ingest(SAMPLE, target_user=A, now=NOW)
        store.write_artifacts(A, artifacts["mail"], artifacts["file"], artifacts["calendar"])

        desk_a = store.desk(A)
        self.assertEqual(len(desk_a["mail"]), 1)
        self.assertEqual(len(desk_a["files"]), 1)
        self.assertEqual(len(desk_a["calendar"]), 1)
        self.assertEqual(desk_a["mail"][0]["owner_id"], A)
        self.assertEqual(desk_a["files"][0]["owner_id"], A)
        self.assertEqual(desk_a["calendar"][0]["owner_id"], A)
        self.assertEqual(desk_a["files"][0]["path"], "jobs/north-pier-logistics.md")
        self.assertIn("2026-09-15T09:00:00+00:00", desk_a["calendar"][0]["start"])

        self.assertEqual(store.counts(B), {"mail": 0, "files": 0, "calendar": 0})
        self.assertEqual(store.desk(B), {"mail": [], "files": [], "calendar": []})

    def test_second_user_write_does_not_merge(self) -> None:
        store = DeskStore()
        first = ingest(SAMPLE, target_user=A, now=NOW)
        store.write_artifacts(A, first["mail"], first["file"], first["calendar"])
        second = ingest("Short note for B.\nContact: desk@b.example", target_user=B, now=NOW)
        store.write_artifacts(B, second["mail"], second["file"], second["calendar"])

        self.assertEqual(store.counts(A)["mail"], 1)
        self.assertEqual(store.counts(B)["mail"], 1)
        self.assertEqual(store.desk(A)["mail"][0]["owner_id"], A)
        self.assertEqual(store.desk(B)["mail"][0]["owner_id"], B)
        self.assertNotEqual(store.desk(A)["files"][0]["path"], store.desk(B)["files"][0]["path"])

    def test_ingest_requires_target_and_text(self) -> None:
        with self.assertRaises(ValueError):
            ingest(SAMPLE, target_user="")
        with self.assertRaises(ValueError):
            ingest("   ", target_user=A)
        with self.assertRaises(ValueError):
            DeskStore().write_artifacts("", {"a": 1}, {"b": 1}, {"c": 1})

    def test_artifacts_name_only_the_target_user(self) -> None:
        artifacts = ingest(SAMPLE, target_user=A, now=NOW)
        blob = str(artifacts)
        self.assertEqual(artifacts["target_user"], A)
        self.assertNotIn(B, blob)


if __name__ == "__main__":
    unittest.main()
