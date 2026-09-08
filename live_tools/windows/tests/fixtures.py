"""Native synthetic SQLCipher/WAL fixtures. Contains no user data."""
import ctypes
import hashlib
import hmac
import os
from pathlib import Path
import struct
import sys

from Crypto.Cipher import AES
from live_tools.wechat_safe_snapshot import _wal_checksum_words


def reserved_sqlite(path, statements):
    library = ctypes.CDLL(str(Path(sys.base_prefix) / "DLLs/sqlite3.dll"))
    library.sqlite3_open_v2.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_int, ctypes.c_char_p]
    library.sqlite3_file_control.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p]
    library.sqlite3_exec.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    library.sqlite3_close.argtypes = [ctypes.c_void_p]
    database = ctypes.c_void_p()
    assert library.sqlite3_open_v2(str(path).encode("utf-8"), ctypes.byref(database), 6, None) == 0
    try:
        reserve = ctypes.c_int(80)
        assert library.sqlite3_file_control(database, b"main", 38, ctypes.byref(reserve)) == 0
        sql = "PRAGMA page_size=4096; VACUUM; " + statements
        assert library.sqlite3_exec(database, sql.encode("utf-8"), None, None, None) == 0
    finally:
        library.sqlite3_close(database)
    assert path.read_bytes()[20] == 80


def encrypt_database(path, key, salt):
    data = path.read_bytes()
    result = bytearray()
    mac_key = hashlib.pbkdf2_hmac("sha512", key, bytes(b ^ 0x3a for b in salt), 2, 32)
    for offset in range(0, len(data), 4096):
        number = offset // 4096 + 1
        page = data[offset:offset + 4096]
        iv = hashlib.sha256(str(number).encode()).digest()[:16]
        body = (salt if number == 1 else b"") + AES.new(key, AES.MODE_CBC, iv).encrypt(page[16 if number == 1 else 0:4016]) + iv
        body += hmac.new(mac_key, body[16 if number == 1 else 0:] + struct.pack("<I", number), "sha512").digest()
        result.extend(body)
    return bytes(result)


def committed_wal(database, encrypted):
    salt = bytes(range(8))
    header = struct.pack(">IIII", 0x377F0682, 3007000, 4096, 1) + salt
    checksum = _wal_checksum_words(header, "little")
    wal = bytearray(header + struct.pack(">II", *checksum))
    pages = len(encrypted) // 4096
    for index in range(pages):
        page = encrypted[index * 4096:(index + 1) * 4096]
        frame = struct.pack(">II", index + 1, pages if index + 1 == pages else 0)
        checksum = _wal_checksum_words(frame + page, "little", checksum)
        wal.extend(frame + salt + struct.pack(">II", *checksum) + page)
    Path(str(database) + "-wal").write_bytes(wal)
    index_header = bytearray(48)
    struct.pack_into("<I", index_header, 0, 3007000)
    index_header[12] = 1
    struct.pack_into("<HII", index_header, 14, 4096, pages, pages)
    struct.pack_into("<II", index_header, 24, *checksum)
    index_header[32:40] = salt
    struct.pack_into("<II", index_header, 40, *_wal_checksum_words(bytes(index_header[:40]), "little"))
    Path(str(database) + "-shm").write_bytes(bytes(index_header) * 2 + bytes(32768 - 96))
