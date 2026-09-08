"""Platform-neutral Windows contracts; synthetic bytes only."""
import hashlib
import hmac
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from Crypto.Cipher import AES
from live_tools.windows.router import AccountRoutingError, Binding, bind_active_account
from live_tools.windows.setup_support import (SetupError, raw_candidates, string_pointers,
                                             target_set, valid_page_key)
from portable_skill.scripts.dev_backend import _redact_public_value


def encrypted_page(key=None, salt=None):
    key = key or hashlib.sha256(b"synthetic-key-only").digest()
    salt = salt or hashlib.sha256(b"synthetic-salt-only").digest()[:16]
    plain = bytearray(4096)
    plain[:16] = b"SQLite format 3\0"
    plain[16:24] = b"\x10\x00\x01\x01\x50\x40\x20\x20"
    iv = bytes(range(16))
    body = salt + AES.new(key, AES.MODE_CBC, iv).encrypt(bytes(plain[16:4016])) + iv
    mac_key = hashlib.pbkdf2_hmac("sha512", key, bytes(b ^ 0x3a for b in salt), 2, 32)
    return body + hmac.new(mac_key, body[16:] + struct.pack("<I", 1), "sha512").digest(), key


class Contracts(unittest.TestCase):
    def test_first_page_authentication(self):
        page, key = encrypted_page()
        self.assertTrue(valid_page_key(page, key))
        self.assertFalse(valid_page_key(page, bytes(32)))
        self.assertFalse(valid_page_key(page[:-1] + bytes([page[-1] ^ 1]), key))
        self.assertFalse(valid_page_key(page[:100], key))

    def test_raw_literals_are_bounded_and_salt_bound(self):
        page, key = encrypted_page()
        raw = b"x'" + key.hex().encode() + page[:16].hex().encode() + b"'"
        self.assertEqual(list(raw_candidates(raw)), [(key, page[:16])])
        self.assertEqual(list(raw_candidates(b"x'" + b"a" * 97 + b"'")), [])

    def test_std_string_candidates(self):
        data = struct.pack("<QQQQ", 0x12340000, 0, 32, 47)
        self.assertEqual(list(string_pointers(data)), [0x12340000])
        self.assertEqual(list(string_pointers(struct.pack("<QQQQ", 4, 0, 32, 47))), [])
        self.assertEqual(list(string_pointers(struct.pack("<QQQQ", 0x12340000, 0, 32, 4096))), [])

    def test_target_union_no_wildcard_or_missing_media(self):
        found = {"contact/contact.db": {}, "message/message_0.db": {},
                 "message/message_9.db": {}, "message/media_3.db": {},
                 "message/message_resource.db": {}}
        self.assertEqual(len(target_set(found, ["text"])), 3)
        self.assertEqual(len(target_set(found, ["text", "voice"])), 4)
        self.assertEqual(len(target_set(found, ["all"])), 5)
        for types in ([], ["*"], ["all", "text"]):
            with self.assertRaises(SetupError):
                target_set(found, types)
        del found["message/media_3.db"]
        with self.assertRaises(SetupError):
            target_set(found, ["voice"])

    def test_binding_switch_and_restart_fail(self):
        first = Binding("account-" + "a" * 12, Path("fixture"), 1, 1, Path("fixture.exe"), "4.0", ("contact", "message"))
        second = Binding(first.account_ref, first.db_base, 2, 2, first.executable, first.version, first.categories)
        self.assertIs(bind_active_account(sampler=lambda: first, pause=lambda _: None), first)
        samples = iter([first, second])
        with self.assertRaises(AccountRoutingError):
            bind_active_account(sampler=lambda: next(samples), pause=lambda _: None)
        self.assertNotIn(first.account_ref, repr(first))
        self.assertNotIn("pid", json.dumps(first.public_report()))

    def test_windows_private_paths_redacted(self):
        for value in ("C:" + "\\Private\\data.db", "failed: D:/Private/data.db", "\\\\host\\share\\file"):
            self.assertEqual(_redact_public_value(value), "[private]")

    def test_thin_client_still_has_no_setup_route(self):
        from portable_skill.skills import __path__
        root = Path(__path__[0]).parent
        text = (root / "skills/wechat-local-export/scripts/wechat_local_export_client.py").read_text()
        self.assertNotIn('add_parser("capture"', text)
        self.assertNotIn("ReadProcessMemory", text)


if __name__ == "__main__":
    unittest.main()
