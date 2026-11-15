from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from live_tools.snapshot_retention import configured_keep_runs, prune_account_runs


class RetentionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.account = Path(self.temporary.name) / "account-0123456789ab"
        self.runs = []
        for stamp in ("20240101T000000.1Z", "20240102T000000.1Z", "20240103T000000.1Z"):
            run = self.account / f"run-{stamp}"
            (run / "decrypted").mkdir(parents=True)
            (run / "decrypted/marker").write_text("x")
            self.runs.append(run)
        (self.account / "unrelated").mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_keeps_active_run_and_removes_older(self) -> None:
        report = prune_account_runs(self.runs[2] / "decrypted", keep=1)
        self.assertEqual(report["removed"], 2)
        self.assertTrue(self.runs[2].exists())
        self.assertFalse(self.runs[0].exists() or self.runs[1].exists())
        self.assertTrue((self.account / "unrelated").exists())

    def test_never_removes_active_even_if_not_newest(self) -> None:
        report = prune_account_runs(self.runs[0] / "decrypted", keep=2)
        self.assertEqual(report["removed"], 1)
        self.assertTrue(self.runs[0].exists() and self.runs[2].exists())
        self.assertFalse(self.runs[1].exists())

    def test_unrecognized_layout_is_skipped(self) -> None:
        other = Path(self.temporary.name) / "elsewhere" / "decrypted"
        other.mkdir(parents=True)
        self.assertEqual(prune_account_runs(other)["status"], "skipped")
        self.assertTrue(all(run.exists() for run in self.runs))

    def test_keep_runs_environment_is_bounded(self) -> None:
        self.assertEqual(configured_keep_runs({}), 1)
        self.assertEqual(configured_keep_runs({"WECHAT_LOCAL_EXPORT_KEEP_RUNS": "3"}), 3)
        self.assertEqual(configured_keep_runs({"WECHAT_LOCAL_EXPORT_KEEP_RUNS": "0"}), 1)
        self.assertEqual(configured_keep_runs({"WECHAT_LOCAL_EXPORT_KEEP_RUNS": "x"}), 1)


if __name__ == "__main__":
    unittest.main()
