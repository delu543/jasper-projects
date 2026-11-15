from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import time
import unittest

from content_vault import digest
from content_vault.identity import (
    load_contacts,
    owner_username_from_account_root,
    pinned_chat_ids,
    resolve_sender,
)
from content_vault.scanner import build_content_plan


BASE = 1_704_067_200  # synthetic fixture time
OWNER = "owner_fixture"
GROUP = "100001@chatroom"
FRIEND = "friend_fixture"
OFFICIAL = "gh_fixture"


def _table(chat_id: str) -> str:
    return "Msg_" + hashlib.md5(chat_id.encode()).hexdigest()


class DigestFixture:
    """Fully synthetic vault: no real account, chat name or message."""

    def __init__(self, root: Path) -> None:
        self.vault = root / "account-0123456789ab" / "run-20240101T000000.000001Z" / "decrypted"
        (self.vault / "contact").mkdir(parents=True)
        (self.vault / "message").mkdir()
        with sqlite3.connect(self.vault / "contact/contact.db") as connection:
            connection.execute(
                "CREATE TABLE contact (id INTEGER, username TEXT, remark TEXT, nick_name TEXT, "
                "alias TEXT, flag INTEGER, delete_flag INTEGER)"
            )
            rows = [
                (1, OWNER, "", "示例本人", "", 0, 0),
                (2, GROUP, "", "示例群", "", 0x802, 0),
                (3, FRIEND, "示例好友备注", "示例好友", "", 0x803, 0),
                (4, OFFICIAL, "", "示例公众号", "", 0x803, 0),
                (5, "member_a", "", "成员甲", "", 3, 0),
                (6, "unpinned@chatroom", "", "未置顶群", "", 2, 0),
            ]
            connection.executemany("INSERT INTO contact VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        with sqlite3.connect(self.vault / "message/message_0.db") as connection:
            connection.execute("CREATE TABLE Name2Id (user_name TEXT)")
            connection.execute("INSERT INTO Name2Id(rowid, user_name) VALUES (1, ?)", (OWNER,))
            connection.execute("INSERT INTO Name2Id(rowid, user_name) VALUES (7, ?)", (FRIEND,))
            connection.execute("INSERT INTO Name2Id(rowid, user_name) VALUES (9, 'member_a')")
            for chat in (GROUP, FRIEND):
                connection.execute(
                    f"CREATE TABLE [{_table(chat)}] (local_id INTEGER, server_id INTEGER, "
                    "local_type INTEGER, create_time INTEGER, message_content TEXT, "
                    "compress_content BLOB, WCDB_CT_message_content INTEGER, "
                    "packed_info_data BLOB, real_sender_id TEXT, sort_seq INTEGER, server_seq INTEGER)"
                )

    def add(self, chat: str, local_id: int, offset: int, content: str, sender: str, local_type: int = 1) -> None:
        with sqlite3.connect(self.vault / "message/message_0.db") as connection:
            connection.execute(
                f"INSERT INTO [{_table(chat)}] VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?)",
                (local_id, 9000 + local_id, local_type, BASE + offset, content, sender,
                 (BASE + offset) * 1000 + local_id, local_id),
            )


class IdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = DigestFixture(Path(self.temporary.name))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_pinned_bit_and_display_names(self) -> None:
        contacts = load_contacts(self.fixture.vault)
        self.assertEqual(pinned_chat_ids(contacts), sorted([GROUP, FRIEND, OFFICIAL]))
        self.assertEqual(contacts[FRIEND]["display_name"], "示例好友备注")

    def test_owner_from_account_directory_requires_contact(self) -> None:
        contacts = load_contacts(self.fixture.vault)
        self.assertEqual(owner_username_from_account_root(f"/x/{OWNER}_a1b2", contacts), OWNER)
        self.assertIsNone(owner_username_from_account_root("/x/unknown_a1b2", contacts))

    def test_numeric_sender_resolves_to_self_and_names(self) -> None:
        contacts = load_contacts(self.fixture.vault)
        name2id = {1: OWNER, 7: FRIEND}
        self.assertEqual(resolve_sender("1", name2id, contacts, OWNER), (OWNER, "示例本人", True))
        self.assertEqual(resolve_sender("7", name2id, contacts, OWNER), (FRIEND, "示例好友备注", False))
        self.assertEqual(resolve_sender("42", name2id, contacts, OWNER), ("42", "42", False))

    def test_scan_plan_carries_resolved_sender(self) -> None:
        self.fixture.add(FRIEND, 1, 10, "你好", "7")
        self.fixture.add(FRIEND, 2, 20, "收到", "1")
        plan = build_content_plan(
            self.fixture.vault, "示例好友备注", str(BASE), str(BASE + 100),
            kinds=["text"], owner_username=OWNER,
        )
        senders = [(m["sender_display_name"], m["sender_is_self"]) for m in plan["messages"]]
        self.assertEqual(senders, [("示例好友备注", False), ("示例本人", True)])


class DigestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.fixture = DigestFixture(self.root)
        f = self.fixture
        f.add(GROUP, 1, 10, "member_a:\n大家好 @示例本人 看一下", "9")
        f.add(GROUP, 2, 20, "我看了", "1")
        f.add(GROUP, 3, 30, "member_a:\n<msg><img/></msg>", "9", local_type=3)
        f.add(GROUP, 4, 40, "member_a:\n@所有人 开会", "9")
        f.add(FRIEND, 1, 15, "在吗", "7")
        self.contacts = load_contacts(f.vault)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def build(self, **kwargs):
        options = dict(
            chat_ids=pinned_chat_ids(self.contacts),
            contacts=self.contacts,
            owner_username=OWNER,
            cursors={},
            since_unix=BASE,
            data_as_of_unix=BASE + 100,
        )
        options.update(kwargs)
        return digest.build_digest(self.fixture.vault, **options)

    def test_digest_counts_mentions_owner_and_errors(self) -> None:
        chats, cursors = self.build()
        by_id = {item["chat_id"]: item for item in chats}
        group = by_id[GROUP]
        self.assertEqual(group["text_count"], 3)
        self.assertEqual(group["non_text_counts"], {"image": 1})
        self.assertEqual(group["mention_count"], 1)
        self.assertEqual(group["mentions_all_count"], 1)
        self.assertEqual(group["owner_message_count"], 1)
        self.assertEqual(group["owner_messages"][0]["sender"], "示例本人")
        self.assertEqual(group["top_senders"][0], {"name": "成员甲", "is_self": False, "count": 3})
        self.assertEqual(by_id[FRIEND]["top_senders"][0]["name"], "示例好友备注")
        self.assertEqual(by_id[OFFICIAL]["status"], "error")
        self.assertEqual(by_id[OFFICIAL]["error"], "official-account-not-in-message-db")
        self.assertEqual(cursors[GROUP]["create_time"], BASE + 40)
        self.assertNotIn(OFFICIAL, cursors)

    def test_cursor_reads_only_new_messages(self) -> None:
        _, cursors = self.build()
        self.fixture.add(GROUP, 5, 50, "member_a:\n新消息", "9")
        chats, advanced = self.build(cursors=cursors, since_unix=None)
        group = {item["chat_id"]: item for item in chats}[GROUP]
        self.assertEqual(group["message_count"], 1)
        self.assertEqual(group["window_source"], "cursor")
        self.assertEqual(advanced[GROUP]["create_time"], BASE + 50)

    def test_same_second_messages_are_not_lost_or_repeated(self) -> None:
        _, cursors = self.build()
        self.fixture.add(GROUP, 6, 40, "member_a:\n同一秒的后一条", "9")
        chats, _ = self.build(cursors=cursors, since_unix=None)
        group = {item["chat_id"]: item for item in chats}[GROUP]
        self.assertEqual([m["text"] for m in group["text_messages"]], ["同一秒的后一条"])

    def test_text_cap_keeps_latest(self) -> None:
        chats, _ = self.build(max_text_messages=1)
        group = {item["chat_id"]: item for item in chats}[GROUP]
        self.assertTrue(group["text_messages_truncated"])
        self.assertEqual(group["text_messages"][0]["text"], "@所有人 开会")

    def test_explicit_list_selection_is_exact(self) -> None:
        selected, errors = digest.select_chats(
            self.contacts, mode="list", requested=[GROUP, "示例好友备注", "示例", "不存在"]
        )
        self.assertEqual(selected, [GROUP, FRIEND])
        self.assertEqual([e["error"] for e in errors], ["chat-not-found", "chat-not-found"])

    def test_cursor_store_and_digest_files_are_private(self) -> None:
        state = self.root / "support" / "state" / "digest-state.json"
        store = digest.CursorStore(state)
        store.update("account-0123456789ab", {GROUP: {"create_time": BASE, "sort_seq": 1}})
        store.save()
        self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(state.parent.stat().st_mode), 0o700)
        reloaded = digest.CursorStore(state)
        self.assertEqual(reloaded.last_account_ref, "account-0123456789ab")
        self.assertEqual(reloaded.cursors("account-0123456789ab")[GROUP]["sort_seq"], 1)
        os.chmod(state, 0o644)
        with self.assertRaises(digest.DigestError):
            digest.CursorStore(state)

    def test_prune_digests_only_removes_old_named_files(self) -> None:
        daily = self.root / "daily"
        daily.mkdir()
        old = daily / "2024-01-01_080000.json"
        new = daily / "2024-01-20_080000.json"
        other = daily / "notes.json"
        for path in (old, new, other):
            path.write_text("{}")
        now = time.time()
        os.utime(old, (now - 20 * 86400, now - 20 * 86400))
        os.utime(other, (now - 20 * 86400, now - 20 * 86400))
        self.assertEqual(digest.prune_digests(daily, now=now), 1)
        self.assertFalse(old.exists())
        self.assertTrue(new.exists() and other.exists())

    def test_data_as_of_comes_from_run_name(self) -> None:
        unix, source = digest.vault_data_as_of(self.fixture.vault)
        self.assertEqual(source, "snapshot-run")
        self.assertEqual(unix, BASE)

    def test_since_format_is_strict(self) -> None:
        with self.assertRaises(digest.DigestError):
            digest.parse_since("yesterday")


if __name__ == "__main__":
    unittest.main()
