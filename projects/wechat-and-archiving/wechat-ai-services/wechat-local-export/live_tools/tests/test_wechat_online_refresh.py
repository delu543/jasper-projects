from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from live_tools.wechat_online_refresh import (
    OnlineRefreshError,
    all_message_database_requests,
    preserved_capability_databases,
    refresh_online_snapshot,
    refresh_online_snapshot_all_messages,
    snapshot_database_requests,
)


class Binding:
    account_ref = "account-0123456789ab"


class OnlineRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.vault = self.root / "vault"
        (self.vault / "contact").mkdir(parents=True)
        (self.vault / "message").mkdir()
        (self.vault / "contact/contact.db").write_bytes(b"contact")
        self.chat_id = "fixture@chatroom"
        table = "Msg_" + hashlib.md5(self.chat_id.encode()).hexdigest()
        with sqlite3.connect(self.vault / "message/message_0.db") as connection:
            connection.execute(f"CREATE TABLE [{table}](id INTEGER)")
        with sqlite3.connect(self.vault / "message/message_1.db") as connection:
            connection.execute("CREATE TABLE unrelated(id INTEGER)")
        with sqlite3.connect(self.vault / "message/media_0.db") as connection:
            connection.execute("CREATE TABLE VoiceInfo(svr_id INTEGER)")
        with sqlite3.connect(
            self.vault / "message/message_resource.db"
        ) as connection:
            connection.execute("CREATE TABLE MessageResourceInfo(id INTEGER)")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_requests_only_target_chat_message_shards(self) -> None:
        self.assertEqual(
            snapshot_database_requests(
                self.vault,
                kinds=["text"],
                chat_id=self.chat_id,
            ),
            ["contact", "message_0"],
        )
        self.assertEqual(
            snapshot_database_requests(
                self.vault,
                kinds=["voice"],
                chat_id=self.chat_id,
            ),
            ["contact", "message_0", "media_0"],
        )
        self.assertEqual(
            snapshot_database_requests(
                self.vault,
                kinds=["all"],
                chat_id=self.chat_id,
            ),
            ["contact", "message_0", "media_0", "message_resource"],
        )

    def test_refresh_uses_online_snapshot_and_updates_profile_last(self) -> None:
        run = self.root / "run"
        (run / "decrypted").mkdir(parents=True)
        calls: dict[str, object] = {}

        def snapshotter(**kwargs: object) -> dict[str, object]:
            calls["snapshot"] = kwargs
            return {
                "status": "complete",
                "database_count": 4,
                "run_directory": str(run),
                "safety": {
                    "snapshot_mode": "online_sqlite_shm_coordinated_apfs_clone"
                },
            }

        def profile_writer(account_ref: str, profile: object) -> None:
            calls["profile"] = (account_ref, profile)

        report = refresh_online_snapshot(
            Binding(),
            {
                "schema_version": 2,
                "account_ref": Binding.account_ref,
                "vault_dir": str(self.vault),
                "account_root": str(self.root / "account"),
                "swift_bin": str(self.root / "swift"),
            },
            kinds=["voice"],
            chat_id=self.chat_id,
            output_root=self.root / "snapshots",
            resolver=lambda account_ref: self.root / "db_storage",
            snapshotter=snapshotter,
            doctor_fn=lambda *args, **kwargs: {
                "ready_for_scan": True,
                "ready_for_voice_mp4": True,
            },
            profile_writer=profile_writer,
        )
        snapshot = calls["snapshot"]
        self.assertTrue(snapshot["online"])
        self.assertIsNone(snapshot["keys_file"])
        self.assertEqual(
            snapshot["databases"],
            ["contact", "message_0", "media_0", "message_resource"],
        )
        self.assertIn("profile", calls)
        self.assertTrue(report["profile_updated"])
        self.assertFalse(report["page_hmac_verified"])

    def test_profile_is_not_updated_when_new_snapshot_fails_doctor(self) -> None:
        run = self.root / "failed-run"
        (run / "decrypted").mkdir(parents=True)
        wrote: list[object] = []
        with self.assertRaisesRegex(OnlineRefreshError, "doctor"):
            refresh_online_snapshot(
                Binding(),
                {
                    "schema_version": 2,
                    "account_ref": Binding.account_ref,
                    "vault_dir": str(self.vault),
                    "account_root": str(self.root / "account"),
                    "swift_bin": str(self.root / "swift"),
                },
                kinds=["text"],
                chat_id=self.chat_id,
                output_root=self.root / "snapshots",
                resolver=lambda account_ref: self.root / "db_storage",
                snapshotter=lambda **kwargs: {
                    "status": "complete",
                    "database_count": 4,
                    "run_directory": str(run),
                    "safety": {
                        "snapshot_mode": (
                            "online_sqlite_shm_coordinated_apfs_clone"
                        )
                    },
                },
                doctor_fn=lambda *args, **kwargs: {
                    "ready_for_scan": False,
                    "ready_for_voice_mp4": False,
                },
                profile_writer=lambda *args: wrote.append(args),
            )
        self.assertEqual(wrote, [])



class AllMessageRefreshTests(unittest.TestCase):
    setUp = OnlineRefreshTests.setUp
    tearDown = OnlineRefreshTests.tearDown

    def _profile(self) -> dict:
        return {
            "schema_version": 2,
            "account_ref": Binding.account_ref,
            "vault_dir": str(self.vault),
            "account_root": str(self.root / "account"),
            "swift_bin": None,
        }

    def _snapshotter(self, calls: dict, run: Path, count: int):
        def snapshotter(**kwargs: object) -> dict:
            calls["snapshot"] = kwargs
            return {
                "status": "complete",
                "database_count": count,
                "run_directory": str(run),
                "safety": {"snapshot_mode": "online_sqlite_shm_coordinated_apfs_clone"},
            }
        return snapshotter

    def test_all_message_requests_cover_every_shard(self) -> None:
        self.assertEqual(
            all_message_database_requests(self.vault),
            ["contact", "message_0", "message_1"],
        )
        self.assertEqual(
            preserved_capability_databases(self.vault),
            ["media_0", "message_resource"],
        )

    def test_digest_snapshot_keeps_media_for_the_next_voice_scan(self) -> None:
        run = self.root / "digest-run"
        published: dict[str, str] = {}

        def snapshotter(**kwargs: object) -> dict:
            databases = list(kwargs["databases"])
            decrypted = run / "decrypted"
            for name in databases:
                if name == "contact":
                    relative = Path("contact/contact.db")
                else:
                    relative = Path("message") / f"{name}.db"
                destination = decrypted / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = self.vault / relative
                destination.write_bytes(source.read_bytes())
            return {
                "status": "complete",
                "database_count": len(databases),
                "run_directory": str(run),
                "safety": {
                    "snapshot_mode": "online_sqlite_shm_coordinated_apfs_clone"
                },
            }

        def profile_writer(_account_ref: str, profile: dict) -> None:
            published["vault_dir"] = profile["vault_dir"]

        refresh_online_snapshot_all_messages(
            Binding(),
            self._profile(),
            output_root=self.root / "snapshots",
            resolver=lambda account_ref: self.root / "db_storage",
            snapshotter=snapshotter,
            doctor_fn=lambda *args, **kwargs: {"ready_for_scan": True},
            profile_writer=profile_writer,
            pruner=None,
        )
        voice = snapshot_database_requests(
            published["vault_dir"],
            kinds=["voice"],
            chat_id=self.chat_id,
        )
        self.assertEqual(voice, ["contact", "message_0", "media_0"])

    def test_one_refresh_then_prune_after_profile_switch(self) -> None:
        run = self.root / "run"
        (run / "decrypted").mkdir(parents=True)
        calls: dict = {}
        order: list = []

        def profile_writer(account_ref: str, profile: object) -> None:
            order.append("profile")

        def pruner(vault: str) -> dict:
            order.append("prune")
            calls["pruned"] = vault
            return {"status": "complete", "removed": 2}

        report = refresh_online_snapshot_all_messages(
            Binding(),
            self._profile(),
            output_root=self.root / "snapshots",
            resolver=lambda account_ref: self.root / "db_storage",
            snapshotter=self._snapshotter(calls, run, 5),
            doctor_fn=lambda *a, **k: {"ready_for_scan": True},
            profile_writer=profile_writer,
            pruner=pruner,
        )
        self.assertEqual(
            calls["snapshot"]["databases"],
            ["contact", "message_0", "message_1", "media_0", "message_resource"],
        )
        self.assertEqual(order, ["profile", "prune"])
        self.assertEqual(calls["pruned"], str((run / "decrypted").resolve()))
        self.assertEqual(report["retention"]["removed"], 2)

    def test_retention_failure_does_not_fail_refresh(self) -> None:
        run = self.root / "run"
        (run / "decrypted").mkdir(parents=True)

        def pruner(vault: str) -> dict:
            raise OSError("disk")

        report = refresh_online_snapshot(
            Binding(),
            self._profile(),
            kinds=["text"],
            chat_id=self.chat_id,
            output_root=self.root / "snapshots",
            resolver=lambda account_ref: self.root / "db_storage",
            snapshotter=self._snapshotter({}, run, 4),
            doctor_fn=lambda *a, **k: {"ready_for_scan": True},
            profile_writer=lambda *a: None,
            pruner=pruner,
        )
        self.assertTrue(report["profile_updated"])
        self.assertEqual(report["retention"]["status"], "failed")

if __name__ == "__main__":
    unittest.main()
