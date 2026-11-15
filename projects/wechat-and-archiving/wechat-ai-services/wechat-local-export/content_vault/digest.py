"""Multi-chat daily digest over one frozen, already-decrypted vault.

The digest is the daily-report counterpart of ``scan``: instead of one exact
chat per online refresh, it reads many chats from a single verified vault,
starting at a per-chat cursor, and writes one private JSON file that an
assistant can summarize. It never writes to WeChat data, never exports media
bodies and never leaves the local machine.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from direct_vault.direct_voice_vault import (
    VaultError,
    _connect_read_only,
    _message_databases,
    _normalize_text,
    _parse_time,
    _quote_identifier,
    _resolve_vault,
)
from content_vault.identity import (
    chat_kind,
    load_contacts,
    load_name2id,
    owner_username_from_account_root,
    pinned_chat_ids,
    resolve_sender,
)
from content_vault.message_parser import parse_message
from content_vault.scanner import _message_columns, _row_content


DIGEST_SCHEMA_VERSION = 1
STATE_SCHEMA_VERSION = 1
DEFAULT_LOOKBACK_SECONDS = 24 * 3600
DEFAULT_MAX_TEXT_MESSAGES = 200
DEFAULT_MAX_TEXT_CHARS = 500
DEFAULT_MAX_HIGHLIGHTS = 50
DEFAULT_RETENTION_DAYS = 14
MAX_CHATS = 500
_CURSOR_END_SEQ = 2 ** 62
_RUN_TIME = re.compile(r"run-([0-9]{8}T[0-9]{6})(?:\.([0-9]{1,9}))?Z\Z")
_DIGEST_NAME = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})_[0-9]{6}\.json\Z")
_MENTION_TERMINATORS = " \u2005\u2006\u00a0\t\r\n,，:：!！?？。"


class DigestError(VaultError):
    """A safe digest failure without private paths."""


# --------------------------------------------------------------------------
# private file helpers


def _ensure_private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise DigestError("私有目录不能是符号链接")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise DigestError("私有目录不属于当前用户")
    if stat.S_IMODE(info.st_mode) != 0o700:
        os.chmod(path, 0o700)
    return path


def write_private_json(path: Path, value: Any) -> Path:
    parent = _ensure_private_dir(path.parent)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return path


def read_private_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise DigestError("私有状态文件不是普通文件")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise DigestError("私有状态文件权限过宽；需要 0600")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise DigestError("私有状态文件不属于当前用户")
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise DigestError("私有状态文件格式无效")
    return value


# --------------------------------------------------------------------------
# cursor state


class CursorStore:
    """``state/digest-state.json``: per account, per chat (create_time, sort_seq)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        loaded = read_private_json(path)
        if loaded is None:
            loaded = {"schema_version": STATE_SCHEMA_VERSION, "accounts": {}}
        if loaded.get("schema_version") != STATE_SCHEMA_VERSION or not isinstance(
            loaded.get("accounts"), dict
        ):
            raise DigestError("digest 状态文件版本不受支持")
        self.data = loaded

    @property
    def last_account_ref(self) -> Optional[str]:
        value = self.data.get("last_account_ref")
        return value if isinstance(value, str) else None

    def cursors(self, account_ref: str) -> Dict[str, Dict[str, int]]:
        account = self.data["accounts"].get(account_ref) or {}
        result: Dict[str, Dict[str, int]] = {}
        for chat_id, value in (account.get("cursors") or {}).items():
            try:
                result[str(chat_id)] = {
                    "create_time": int(value["create_time"]),
                    "sort_seq": int(value["sort_seq"]),
                }
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def update(self, account_ref: str, cursors: Mapping[str, Mapping[str, int]]) -> None:
        account = self.data["accounts"].setdefault(account_ref, {})
        stored = account.setdefault("cursors", {})
        for chat_id, value in cursors.items():
            stored[chat_id] = {
                "create_time": int(value["create_time"]),
                "sort_seq": int(value["sort_seq"]),
            }
        account["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.data["last_account_ref"] = account_ref

    def remember_account(self, account_ref: str) -> None:
        self.data["last_account_ref"] = account_ref

    def save(self) -> None:
        write_private_json(self.path, self.data)


# --------------------------------------------------------------------------
# selection


def vault_data_as_of(vault_dir: Union[str, Path]) -> Tuple[int, str]:
    """Return (unix, source) for the moment the vault's data was captured."""

    vault = _resolve_vault(vault_dir)
    match = _RUN_TIME.fullmatch(vault.parent.name)
    if vault.name == "decrypted" and match:
        moment = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S").replace(
            tzinfo=timezone.utc
        )
        return int(moment.timestamp()), "snapshot-run"
    newest = 0
    for path in vault.rglob("*.db"):
        try:
            newest = max(newest, int(path.stat().st_mtime))
        except OSError:
            continue
    return newest, "file-mtime"


def load_chat_list(path: Path) -> List[str]:
    value = read_private_json(path)
    chats = value.get("chats") if value else None
    if not isinstance(chats, list) or not chats or len(chats) > MAX_CHATS:
        raise DigestError("聊天清单需要 {\"chats\": [...]}，且 1 到 500 项")
    if any(not isinstance(item, str) or not item.strip() for item in chats):
        raise DigestError("聊天清单只能包含非空字符串（chat_id 或精确显示名）")
    return [item.strip() for item in chats]


def select_chats(
    contacts: Mapping[str, Mapping[str, Any]],
    *,
    mode: str = "pinned",
    requested: Optional[Sequence[str]] = None,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Return (chat_ids, selection_errors). Exact matches only; never fuzzy."""

    if mode == "pinned":
        return pinned_chat_ids(contacts), []
    if mode != "list" or not requested:
        raise DigestError("聊天选择模式无效")
    selected: List[str] = []
    errors: List[Dict[str, Any]] = []
    by_name: Dict[str, List[str]] = {}
    for username, item in contacts.items():
        for name in {item.get("display_name"), item.get("nick_name")}:
            if name:
                by_name.setdefault(str(name), []).append(username)
    for entry in requested:
        if entry in contacts:
            chosen = entry
        else:
            matches = sorted(set(by_name.get(entry, [])))
            if len(matches) != 1:
                errors.append(
                    {
                        "requested": entry,
                        "error": "chat-not-found" if not matches else "ambiguous-name",
                        "candidate_count": len(matches),
                    }
                )
                continue
            chosen = matches[0]
        if chosen not in selected:
            selected.append(chosen)
    return selected, errors


# --------------------------------------------------------------------------
# digest


def _mention_patterns(names: Iterable[str]) -> List[str]:
    return sorted({"@" + name.strip() for name in names if name and name.strip()}, key=len, reverse=True)


def _mentions(text: str, patterns: Sequence[str]) -> bool:
    for pattern in patterns:
        start = text.find(pattern)
        while start >= 0:
            end = start + len(pattern)
            if end >= len(text) or text[end] in _MENTION_TERMINATORS:
                return True
            start = text.find(pattern, start + 1)
    return False


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _local_iso(unix: int) -> str:
    return datetime.fromtimestamp(unix).astimezone().isoformat(timespec="seconds")


def _table_index(connection: sqlite3.Connection) -> set:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"
        )
    }


def build_digest(
    vault_dir: Union[str, Path],
    *,
    chat_ids: Sequence[str],
    contacts: Mapping[str, Mapping[str, Any]],
    owner_username: Optional[str],
    cursors: Mapping[str, Mapping[str, int]],
    since_unix: Optional[int],
    data_as_of_unix: int,
    mention_names: Sequence[str] = (),
    max_text_messages: int = DEFAULT_MAX_TEXT_MESSAGES,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
    max_highlights: int = DEFAULT_MAX_HIGHLIGHTS,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, int]]]:
    """Read every selected chat once; return (chat digests, advanced cursors).

    ``since_unix`` overrides stored cursors. Without either, the last 24 hours
    before ``data_as_of_unix`` are read.
    """

    vault = _resolve_vault(vault_dir)
    owner = contacts.get(owner_username or "") or {}
    names = list(mention_names)
    for key in ("nick_name", "alias"):
        if owner.get(key):
            names.append(str(owner[key]))
    patterns = _mention_patterns(names)
    default_since = data_as_of_unix - DEFAULT_LOOKBACK_SECONDS

    databases = _message_databases(vault)
    results: Dict[str, Dict[str, Any]] = {}
    collected: Dict[str, List[Dict[str, Any]]] = {chat_id: [] for chat_id in chat_ids}
    found: Dict[str, bool] = {chat_id: False for chat_id in chat_ids}
    windows: Dict[str, Tuple[int, int]] = {}
    for chat_id in chat_ids:
        if since_unix is not None:
            windows[chat_id] = (since_unix, -1)
        elif chat_id in cursors:
            windows[chat_id] = (cursors[chat_id]["create_time"], cursors[chat_id]["sort_seq"])
        else:
            windows[chat_id] = (default_since, -1)

    for database in databases:
        with _connect_read_only(database, vault) as connection:
            tables = _table_index(connection)
            try:
                name2id = load_name2id(connection)
            except (VaultError, sqlite3.Error):
                name2id = {}
            for chat_id in chat_ids:
                table = "Msg_" + hashlib.md5(chat_id.encode("utf-8")).hexdigest()
                if table not in tables:
                    continue
                found[chat_id] = True
                columns = _message_columns(connection, table)
                aliases = [
                    f"{_quote_identifier(column)} AS {_quote_identifier(alias)}"
                    if column
                    else f"NULL AS {_quote_identifier(alias)}"
                    for alias, column in columns.items()
                ]
                create_col = _quote_identifier(str(columns["create_time"]))
                seq_col = _quote_identifier(str(columns["sort_seq"] or columns["local_id"]))
                start_time, start_seq = windows[chat_id]
                sql = (
                    f"SELECT {', '.join(aliases)} FROM {_quote_identifier(table)} "
                    f"WHERE {create_col} >= ? ORDER BY {create_col}, {seq_col}"
                )
                is_group = chat_id.endswith("@chatroom")
                for row in connection.execute(sql, (start_time,)):
                    create_time = int(row["create_time"] or 0)
                    sort_seq = int(row["sort_seq"] or row["local_id"] or 0)
                    if create_time == start_time and sort_seq <= start_seq:
                        continue
                    try:
                        content = _row_content(row)
                    except VaultError:
                        content = ""
                    real_sender = _normalize_text(row["real_sender_id"]).strip()
                    parsed = parse_message(
                        int(row["local_type"] or 0),
                        content,
                        is_group=is_group,
                        real_sender_id=real_sender,
                    )
                    sender_id = parsed.get("sender_id") or real_sender
                    username, display, is_self = resolve_sender(
                        sender_id, name2id, contacts, owner_username
                    )
                    payload = parsed.get("payload") or {}
                    text = payload.get("text") if isinstance(payload, dict) else None
                    collected[chat_id].append(
                        {
                            "create_time": create_time,
                            "sort_seq": sort_seq,
                            "kind": str(parsed.get("kind") or "unknown"),
                            "sender": display,
                            "sender_username": username,
                            "is_self": is_self,
                            "text": text if isinstance(text, str) else None,
                        }
                    )

    advanced: Dict[str, Dict[str, int]] = {}
    for chat_id in chat_ids:
        contact = contacts.get(chat_id) or {}
        kind = chat_kind(chat_id)
        entry: Dict[str, Any] = {
            "chat_id": chat_id,
            "display_name": contact.get("display_name") or chat_id,
            "kind": kind,
            "window_start": _local_iso(windows[chat_id][0]),
            "window_source": (
                "since-option" if since_unix is not None
                else "cursor" if chat_id in cursors
                else "default-24h"
            ),
        }
        if not found[chat_id]:
            entry["status"] = "error"
            entry["error"] = (
                "official-account-not-in-message-db" if kind == "official"
                else "chat-table-not-in-message-db"
            )
            results[chat_id] = entry
            continue
        rows = sorted(collected[chat_id], key=lambda item: (item["create_time"], item["sort_seq"]))
        counts = Counter(row["kind"] for row in rows)
        senders = Counter((row["sender"], row["is_self"]) for row in rows)
        texts = [row for row in rows if row["kind"] == "text" and row["text"]]

        def view(row: Mapping[str, Any]) -> Dict[str, Any]:
            return {
                "time": _local_iso(row["create_time"]),
                "sender": row["sender"],
                "is_self": row["is_self"],
                "text": _truncate(row["text"] or "", max_text_chars),
            }

        mentions = [row for row in texts if not row["is_self"] and _mentions(row["text"], patterns)]
        mentions_all = [row for row in texts if "@所有人" in row["text"] or "@All" in row["text"]]
        own = [row for row in rows if row["is_self"]]
        entry.update(
            {
                "status": "ok",
                "message_count": len(rows),
                "text_count": counts.get("text", 0),
                "non_text_counts": {k: v for k, v in sorted(counts.items()) if k != "text"},
                "top_senders": [
                    {"name": name, "is_self": is_self, "count": count}
                    for (name, is_self), count in senders.most_common(5)
                ],
                "owner_message_count": len(own),
                "mention_count": len(mentions),
                "mentions": [view(row) for row in mentions[-max_highlights:]],
                "mentions_all_count": len(mentions_all),
                "owner_messages": [view(row) for row in own if row["text"]][-max_highlights:],
                "text_messages_truncated": len(texts) > max_text_messages,
                "text_messages": [view(row) for row in texts[-max_text_messages:]],
                "first_time": _local_iso(rows[0]["create_time"]) if rows else None,
                "last_time": _local_iso(rows[-1]["create_time"]) if rows else None,
            }
        )
        results[chat_id] = entry
        if rows:
            advanced[chat_id] = {
                "create_time": rows[-1]["create_time"],
                "sort_seq": rows[-1]["sort_seq"],
            }
        elif chat_id not in cursors or since_unix is not None:
            # Nothing new up to the snapshot moment: start next time just before it.
            advanced[chat_id] = {"create_time": data_as_of_unix - 1, "sort_seq": _CURSOR_END_SEQ}
    ordered = [results[chat_id] for chat_id in chat_ids]
    ordered.sort(key=lambda item: (item.get("status") != "ok", -int(item.get("message_count") or 0)))
    return ordered, advanced


def initial_cursors(chat_ids: Sequence[str], at_unix: int) -> Dict[str, Dict[str, int]]:
    return {chat_id: {"create_time": at_unix, "sort_seq": -1} for chat_id in chat_ids}


def prune_digests(directory: Path, *, keep_days: int = DEFAULT_RETENTION_DAYS, now: Optional[float] = None) -> int:
    if not directory.is_dir():
        return 0
    cutoff = (now if now is not None else time.time()) - keep_days * 86400
    removed = 0
    for path in directory.iterdir():
        if not _DIGEST_NAME.fullmatch(path.name) or path.is_symlink() or not path.is_file():
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def parse_since(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?: [0-9]{2}:[0-9]{2}(?::[0-9]{2})?)?", value.strip()):
        raise DigestError("时间格式需要 YYYY-MM-DD[ HH:MM[:SS]]（本地时间）")
    return _parse_time(value)


def owner_for(account_root: Optional[str], contacts: Mapping[str, Any]) -> Optional[str]:
    return owner_username_from_account_root(account_root, contacts)
