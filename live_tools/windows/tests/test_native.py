"""Windows runner acceptance gates, explicitly not a live-WeChat test."""
import ctypes
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from live_tools.platform_support import WINDOWS, is_private, private_chmod, private_mkdir


@unittest.skipUnless(WINDOWS, "requires native Windows APIs")
class NativeWindows(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        private_chmod(self.root, 0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_acl_and_dpapi_current_user(self):
        from live_tools.windows import state
        ref = "account-" + "a" * 12
        support = self.root / "support"
        with patch.object(state, "support_root", return_value=support):
            state.store_initialization(ref, {"schema_version": 1, "account_ref": ref, "test": "synthetic"})
            self.assertEqual(state.load_initialization(ref)["test"], "synthetic")
            path = state.account_directory(ref) / "initialization.dpapi"
            self.assertTrue(is_private(path))
            self.assertNotIn(b"synthetic", path.read_bytes())
            damaged = bytearray(path.read_bytes())
            damaged[len(damaged) // 2] ^= 1
            state.write_private(path, damaged)
            with self.assertRaises(state.ProfileError):
                state.load_initialization(ref)

    def test_acl_rejects_other_readers_and_junction(self):
        import win32security as security
        from live_tools.platform_support import require_no_reparse
        path = self.root / "private"
        private_mkdir(path)
        sd = security.GetNamedSecurityInfo(str(path), security.SE_FILE_OBJECT, security.DACL_SECURITY_INFORMATION)
        acl = sd.GetSecurityDescriptorDacl()
        acl.AddAccessAllowedAce(security.ACL_REVISION, 0x120089, security.ConvertStringSidToSid("S-1-1-0"))
        security.SetNamedSecurityInfo(str(path), security.SE_FILE_OBJECT, security.DACL_SECURITY_INFORMATION, None, None, acl, None)
        self.assertFalse(is_private(path))
        with self.assertRaises(OSError):
            private_mkdir(path)
        link = self.root / "junction"
        result = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(path)], capture_output=True)
        self.assertEqual(result.returncode, 0)
        with self.assertRaises(OSError):
            require_no_reparse(link / "file")
        os.rmdir(link)  # Only this test-created junction, never its target.

    def test_read_process_memory_is_read_only(self):
        from live_tools.windows.key_capture import MemoryReader
        from live_tools.windows.router import process_owned_by_current_user
        self.assertTrue(process_owned_by_current_user(os.getpid()))
        data = ctypes.create_string_buffer(b"synthetic memory fixture")
        reader = MemoryReader(os.getpid())
        try:
            self.assertEqual(reader.read(ctypes.addressof(data), len(data)), data.raw)
        finally:
            reader.close()

    def test_shm_locks_block_real_sqlite_writer_and_release(self):
        from live_tools.windows.snapshot import shm_lease
        database = self.root / "native.db"
        connection = sqlite3.connect(database, timeout=0.05)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE fixture(value)")
            connection.commit()
            with shm_lease(database, "fixture"):
                with self.assertRaises(sqlite3.OperationalError):
                    connection.execute("INSERT INTO fixture VALUES (1)")
                connection.rollback()
            connection.execute("INSERT INTO fixture VALUES (2)")
            connection.commit()
            self.assertEqual(connection.execute("SELECT value FROM fixture").fetchall(), [(2,)])
        finally:
            connection.close()

    def test_path_and_handle_fingerprints_match_after_write(self):
        from live_tools.wechat_safe_snapshot import FileFingerprint
        path = self.root / "fingerprint.db"
        path.write_bytes(b"fixture")
        before = FileFingerprint.from_stat(path.stat())
        with path.open("ab") as handle:
            handle.write(b"changed")
        after = FileFingerprint.from_stat(path.stat())
        self.assertNotEqual(before, after)
        with path.open("rb") as handle:
            self.assertEqual(after, FileFingerprint.from_stat(os.fstat(handle.fileno())))

    def test_snapshot_replays_latest_commit_without_mutating_sources(self):
        from live_tools.windows import snapshot, state
        from live_tools.windows.router import Binding
        from fixtures import reserved_sqlite, encrypt_database, committed_wal
        base = self.root / "account/db_storage"
        (base / "contact").mkdir(parents=True)
        (base / "message").mkdir()
        (base.parent / "msg").mkdir()
        table = "Msg_" + hashlib.md5(b"fixture@chatroom").hexdigest()
        targets = {}
        for relative, sql in {
            "contact/contact.db": "CREATE TABLE contact(username TEXT,nick_name TEXT,remark TEXT,alias TEXT); INSERT INTO contact VALUES ('fixture@chatroom','Fixture','','');",
            "message/message_0.db": f"CREATE TABLE {table}(local_id INTEGER,server_id INTEGER,local_type INTEGER,create_time INTEGER,message_content TEXT);",
        }.items():
            plain = self.root / (Path(relative).stem + "-plain.db")
            reserved_sqlite(plain, sql)
            key = hashlib.sha256(relative.encode()).digest()
            salt = hashlib.sha256((relative + "salt").encode()).digest()[:16]
            destination = base / relative
            destination.write_bytes(encrypt_database(plain, key, salt))
            if relative.startswith("message/"):
                with closing(sqlite3.connect(plain)) as conn, conn:
                    conn.execute(f"INSERT INTO {table} VALUES (1,2,1,100,'latest commit')")
            committed_wal(destination, encrypt_database(plain, key, salt))
            targets[relative] = {"salt": salt.hex(), "key": key.hex()}
        ref = "account-" + "b" * 12
        binding = Binding(ref, base, 1, 1, Path("fixture.exe"), "4.0", ("contact", "message"))
        before = {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).digest() for p in base.rglob("*") if p.is_file()}
        payload = {"schema_version": 1, "account_ref": ref, "db_base": str(base), "targets": targets,
                   "types": ["text"], "snapshot_retention_approved": True}
        support = self.root / "support"
        with patch.object(snapshot, "require_same", return_value=binding), patch.object(snapshot, "support_root", return_value=support), patch.object(state, "support_root", return_value=support):
            state.account_directory(ref, create=True)
            report = snapshot.create_snapshot(binding, payload)
            self.assertEqual(report["status"], "online-refresh-complete")
            profile = state.load_account_profile(ref)
            with closing(sqlite3.connect(Path(profile["vault_dir"]) / "message/message_0.db")) as conn:
                self.assertEqual(conn.execute(f"SELECT message_content FROM {table}").fetchall(), [("latest commit",)])
        after = {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).digest() for p in base.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_real_silk_and_ffmpeg_both_export_modes(self):
        import pysilk
        from direct_vault.tests.test_direct_voice_vault import FixtureVault
        from content_vault.scanner import build_content_plan
        from content_vault.archive_export import export_archive
        from direct_vault.direct_voice_vault import _write_json_private
        fixture = FixtureVault(self.root / "vault")
        silk = pysilk.encode(bytes(24000 * 2), sample_rate=24000)
        fixture.add_message(1, 101, 100, 1000)
        fixture.add_voice(101, 1000, blob=silk)
        account = self.root / "account"
        (account / "msg").mkdir(parents=True)
        plan = build_content_plan(fixture.root, fixture.chat_name, "0", "600", kinds=["voice"])
        plan_path = self.root / "plan.json"
        _write_json_private(plan_path, plan, None)
        for fast in (True, False):
            out = self.root / ("fast" if fast else "full")
            report = export_archive(fixture.root, account, plan_path, plan["plan_digest"], out,
                                    voice_mp4_only=fast)
            self.assertEqual(report["verification"]["status"], "verified-before-atomic-publish")
            self.assertTrue(list(out.rglob("*.mp4")))
            self.assertTrue(all(is_private(p) for p in out.rglob("*") if p.is_file()))

    def test_stalled_pipe_has_deadline(self):
        from content_vault.archive_export import _write_ffmpeg_stdin
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"], stdin=subprocess.PIPE)
        try:
            with self.assertRaises(subprocess.TimeoutExpired):
                _write_ffmpeg_stdin(process, bytes(4 * 1024 * 1024), time.monotonic() + 0.1)
        finally:
            process.kill()
            process.wait(timeout=5)
            process.stdin.close()


if __name__ == "__main__":
    unittest.main()
