from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PACKAGE_ROOT.parent
CLIENT_PATH = PACKAGE_ROOT / "skills/wechat-local-export/scripts/wechat_local_export_client.py"
DEV_BACKEND_PATH = PACKAGE_ROOT / "scripts/dev_backend.py"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from content_vault import digest as digest_module  # noqa: E402
from content_vault.tests.test_digest import BASE, FRIEND, GROUP, OWNER, DigestFixture  # noqa: E402
from direct_vault.direct_voice_vault import _resolve_vault  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeBinding:
    account_ref = "account-0123456789ab"


class DailyDigestCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.fixture = DigestFixture(self.root / "snapshots")
        self.fixture.add(GROUP, 1, 10, "member_a:\n@示例本人 早", "9")
        self.fixture.add(FRIEND, 1, 20, "在吗", "7")
        self.support = self.root / "support"
        self.backend_module = _load("dev_backend_digest_fixture", DEV_BACKEND_PATH)
        self.refresh_calls = 0
        self.bind_error: Exception | None = None
        self.refresh_error: Exception | None = None
        profile = {
            "schema_version": 2,
            "account_ref": FakeBinding.account_ref,
            "vault_dir": str(self.fixture.vault),
            "account_root": f"/fixture/{OWNER}_ab12",
            "swift_bin": None,
        }

        def bind():
            if self.bind_error is not None:
                raise self.bind_error
            return FakeBinding()

        def refresh_all(binding, received_profile):
            self.refresh_calls += 1
            if self.refresh_error is not None:
                raise self.refresh_error
            return {"profile_updated": True, "retention": {"status": "complete", "removed": 1}}

        self.backend = SimpleNamespace(
            bind_active_account=bind,
            load_account_profile=lambda account_ref: dict(profile),
            refresh_all=refresh_all,
            resolve_vault=_resolve_vault,
            digest=digest_module,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_digest(self, *argv: str) -> dict:
        args = self.backend_module.build_parser().parse_args(["daily-digest", *argv])
        reports: list = []
        code = self.backend_module.run_daily_digest(
            args, self.backend, support_root=self.support, report_sink=reports.append,
            now=lambda: float(BASE + 200),
        )
        self.assertEqual(code, 0)
        return reports[-1]

    def test_one_refresh_private_digest_and_cursor(self) -> None:
        report = self.run_digest("--since", "2023-12-31")
        self.assertEqual(self.refresh_calls, 1)
        self.assertEqual(report["status"], "digest-complete")
        self.assertFalse(report["stale"])
        digest_path = self.support / report["digest_file"]
        self.assertEqual(stat.S_IMODE(digest_path.stat().st_mode), 0o600)
        document = json.loads(digest_path.read_text())
        group = {c["chat_id"]: c for c in document["chats"]}[GROUP]
        self.assertEqual(group["mention_count"], 1)
        self.assertTrue(document["owner"]["detected"])
        state = json.loads((self.support / "state/digest-state.json").read_text())
        self.assertIn(GROUP, state["accounts"][FakeBinding.account_ref]["cursors"])

    def test_dry_run_does_not_advance_cursors(self) -> None:
        self.run_digest("--dry-run", "--since", "2023-12-31")
        self.assertFalse((self.support / "state/digest-state.json").exists())

    def test_refresh_failure_falls_back_to_stale_vault(self) -> None:
        self.refresh_error = RuntimeError("synthetic failure")
        report = self.run_digest("--since", "2023-12-31")
        self.assertTrue(report["stale"])
        self.assertEqual(report["refresh"]["status"], "failed")

    def test_wechat_closed_uses_last_known_account_only(self) -> None:
        self.run_digest("--since", "2023-12-31")
        self.bind_error = self.backend_module.CurrentAccountRoutingError("no-active-account")
        report = self.run_digest()
        self.assertTrue(report["stale"])
        self.assertEqual(report["session"], "last-known-account")
        self.assertEqual(self.refresh_calls, 1)

    def test_wechat_closed_without_history_stops(self) -> None:
        self.bind_error = self.backend_module.CurrentAccountRoutingError("no-active-account")
        args = self.backend_module.build_parser().parse_args(["daily-digest"])
        with self.assertRaises(self.backend_module.CurrentAccountRoutingError):
            self.backend_module.run_daily_digest(
                args, self.backend, support_root=self.support, report_sink=lambda r: None
            )

    def test_init_cursors_without_digest(self) -> None:
        report = self.run_digest("--init-cursors-at", "2024-01-01 00:00:30")
        self.assertEqual(report["status"], "cursors-initialized")
        self.assertEqual(self.refresh_calls, 0)
        self.assertFalse((self.support / "daily").exists())

    def test_client_forwards_digest_options(self) -> None:
        client = _load("client_digest_fixture", CLIENT_PATH)
        args = client.build_parser().parse_args(
            ["daily-digest", "--since", "2024-01-01 08:00", "--dry-run", "--mention-name", "示例"]
        )
        self.assertEqual(
            client.backend_arguments(args),
            ["daily-digest", "--since", "2024-01-01 08:00", "--mention-name", "示例", "--dry-run"],
        )
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                client.build_parser().parse_args(["daily-digest", "--since", "昨天"])


if __name__ == "__main__":
    unittest.main()
