"""Minimal safety/unit tests for task-006 draft operator (offline)."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "episode_operator.py"
spec = importlib.util.spec_from_file_location("episode_operator", SCRIPT)
ep = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(ep)


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "episodes.json").write_text(json.dumps([{"date": "2026-11-13", "ja": {"title": "EP001", "seconds": 169.9}}]), encoding="utf-8")
        (self.root / "tools").mkdir()
        (self.root / "tools" / "validate_episode.py").write_text("print('test')", encoding="utf-8")

    def test_creates_unpublished_workspace(self):
        before = (self.root / "episodes.json").read_bytes()
        self.assertEqual(ep.new_episode(self.root, "EP002", "2026-11-20"), 0)
        self.assertTrue(ep.draft_json(self.root, "EP002", "2026-11-20").is_file())
        draft = json.loads(ep.draft_json(self.root, "EP002", "2026-11-20").read_text(encoding="utf-8"))
        self.assertEqual(draft["news"], [])
        self.assertEqual(draft["seconds"], 0)
        self.assertEqual((self.root / "episodes.json").read_bytes(), before)
        self.assertFalse((self.root / "episodes" / "2026-11-20-ja.json").exists())
        self.assertEqual((self.root / "editorial" / "work" / ".gitignore").read_text(encoding="utf-8"), "*\n!.gitignore\n")

    def test_no_duplicate_overwrite(self):
        self.assertEqual(ep.new_episode(self.root, "EP002", "2026-11-20"), 0)
        p = ep.draft_json(self.root, "EP002", "2026-11-20")
        before = p.read_bytes()
        self.assertEqual(ep.new_episode(self.root, "EP002", "2026-11-20"), 2)
        self.assertEqual(p.read_bytes(), before)
        self.assertEqual(ep.new_episode(self.root, "EP002", "2026-11-13"), 2)

    def test_date_and_id_validation(self):
        for s in ("2026-02-30", "2026-1-5", "not-a-date"):
            with self.assertRaises(Exception): ep.safe_date(s)
        self.assertEqual(ep.safe_date("2026-11-20"), "2026-11-20")
        self.assertEqual(ep.safe_ep("ep002"), "EP002")
        for s in ("002", "EP2", "EP-A"):
            with self.assertRaises(Exception): ep.safe_ep(s)


if __name__ == "__main__":
    unittest.main()
