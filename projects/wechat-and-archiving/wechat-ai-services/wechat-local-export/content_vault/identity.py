"""Read-only identity helpers: owner detection and sender display names.

WeChat 4.x stores ``real_sender_id`` as a numeric ``Name2Id`` rowid in each
``message_N.db``. Group text usually also carries a ``username:\\n`` prefix,
but the owner's own group messages and every 1:1 message only carry the numeric
id. These helpers translate those ids into contact usernames and display names
(remark > nick_name > alias > username) without writing to any database.
"""

from __future__ import annotations

from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, Mapping, Optional, Tuple, Union

from direct_vault.direct_voice_vault import (
    VaultError,
    _choose_column,
    _columns,
    _connect_read_only,
    _find_database,
    _find_table,
    _normalize_text,
    _quote_identifier,
    _resolve_vault,
)


PINNED_FLAG = 0x800
_ACCOUNT_DIR_SUFFIX = re.compile(r"\A(?P<user>.+)_[0-9A-Za-z]{1,8}\Z")


def chat_kind(username: str) -> str:
    if username.endswith("@chatroom"):
        return "group"
    if username.startswith("gh_"):
        return "official"
    if "@" in username:
        return "special"
    if username in {"filehelper", "weixin", "fmessage", "medianote", "floatbottle"}:
        return "system"
    return "direct"


def load_contacts(vault_dir: Union[str, Path]) -> Dict[str, Dict[str, Any]]:
    """Return ``username -> {display_name, nick_name, alias, flag}``."""

    vault = _resolve_vault(vault_dir)
    contact_path = _find_database(vault, "contact/contact.db", "contact.db")
    result: Dict[str, Dict[str, Any]] = {}
    with _connect_read_only(contact_path, vault) as connection:
        table = _find_table(connection, "contact")
        if not table:
            raise VaultError("contact.db 中没有 contact 表")
        columns = _columns(connection, table)
        username = _choose_column(columns, ("username", "userName"))
        optional = {
            "remark": _choose_column(columns, ("remark",), required=False),
            "nick_name": _choose_column(columns, ("nick_name", "nickname"), required=False),
            "alias": _choose_column(columns, ("alias",), required=False),
            "flag": _choose_column(columns, ("flag",), required=False),
            "delete_flag": _choose_column(columns, ("delete_flag",), required=False),
        }
        assert username is not None
        selected = [f"{_quote_identifier(username)} AS username"]
        for alias, column in optional.items():
            selected.append(
                f"{_quote_identifier(column)} AS {alias}" if column else f"NULL AS {alias}"
            )
        sql = f"SELECT {', '.join(selected)} FROM {_quote_identifier(table)}"
        for row in connection.execute(sql):
            name = _normalize_text(row["username"]).strip()
            if not name:
                continue
            remark = _normalize_text(row["remark"]).strip()
            nick = _normalize_text(row["nick_name"]).strip()
            alias_value = _normalize_text(row["alias"]).strip()
            try:
                flag = int(row["flag"] or 0)
            except (TypeError, ValueError):
                flag = 0
            try:
                deleted = int(row["delete_flag"] or 0)
            except (TypeError, ValueError):
                deleted = 0
            result[name] = {
                "display_name": remark or nick or alias_value or name,
                "nick_name": nick,
                "alias": alias_value,
                "flag": flag,
                "deleted": bool(deleted),
            }
    return result


def pinned_chat_ids(contacts: Mapping[str, Mapping[str, Any]]) -> list:
    """Chats whose contact flag carries the sticky-on-top bit (0x800)."""

    return sorted(
        username
        for username, item in contacts.items()
        if int(item.get("flag") or 0) & PINNED_FLAG and not item.get("deleted")
    )


def owner_username_from_account_root(
    account_root: Optional[str], contacts: Optional[Mapping[str, Any]] = None
) -> Optional[str]:
    """Derive the owner's username from ``xwechat_files/<user>_<suffix>``.

    The candidate is accepted only when it exists in the contact table (when a
    contact map is supplied). Returns ``None`` instead of guessing.
    """

    if not account_root:
        return None
    base = Path(account_root).name
    candidates = []
    match = _ACCOUNT_DIR_SUFFIX.fullmatch(base)
    if match:
        candidates.append(match.group("user"))
    candidates.append(base)
    for candidate in candidates:
        if contacts is None or candidate in contacts:
            return candidate
    return None


def load_name2id(connection: sqlite3.Connection) -> Dict[int, str]:
    table = _find_table(connection, "Name2Id")
    if not table:
        return {}
    columns = _columns(connection, table)
    column = _choose_column(columns, ("user_name", "username"), required=False)
    if not column:
        return {}
    result: Dict[int, str] = {}
    sql = f"SELECT rowid AS id, {_quote_identifier(column)} AS name FROM {_quote_identifier(table)}"
    for row in connection.execute(sql):
        name = _normalize_text(row["name"]).strip()
        if name:
            result[int(row["id"])] = name
    return result


def resolve_sender(
    sender_id: Any,
    name2id: Mapping[int, str],
    contacts: Mapping[str, Mapping[str, Any]],
    owner_username: Optional[str],
) -> Tuple[str, str, bool]:
    """Return ``(username, display_name, is_self)`` for one parsed sender id."""

    raw = _normalize_text(sender_id).strip()
    username = raw
    if raw.isdecimal():
        username = name2id.get(int(raw), raw)
    contact = contacts.get(username)
    display = str(contact["display_name"]) if contact else username
    is_self = bool(owner_username) and username == owner_username
    return username, display, is_self
