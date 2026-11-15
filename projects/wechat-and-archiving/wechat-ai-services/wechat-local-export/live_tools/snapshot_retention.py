"""Bounded retention for private online-snapshot runs.

Every online refresh publishes a new ``snapshots/<account-ref>/run-*/`` tree
(encrypted clone, materialized pages and decrypted vault). Without pruning the
private directory grows by roughly the size of the refreshed databases on every
scan. After the profile has been atomically switched to the new vault, this
helper removes older runs of the same account, keeping the newest ``keep``
runs and never the run the active profile points to.

Retention never raises: a failure to delete leaves extra data behind but must
not fail an otherwise verified refresh.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import stat
from typing import Any, Dict, Mapping, Optional


RUN_NAME = re.compile(r"run-[0-9]{8}T[0-9]{6}(?:\.[0-9]{1,9})?Z\Z")
ACCOUNT_DIR_NAME = re.compile(r"account-[0-9a-f]{12}\Z")
KEEP_RUNS_ENVIRONMENT = "WECHAT_LOCAL_EXPORT_KEEP_RUNS"
DEFAULT_KEEP_RUNS = 1
MAX_KEEP_RUNS = 20


def configured_keep_runs(environ: Optional[Mapping[str, str]] = None) -> int:
    value = (environ if environ is not None else os.environ).get(KEEP_RUNS_ENVIRONMENT)
    if value is None or not value.strip():
        return DEFAULT_KEEP_RUNS
    try:
        parsed = int(value.strip())
    except ValueError:
        return DEFAULT_KEEP_RUNS
    return min(max(parsed, 1), MAX_KEEP_RUNS)


def prune_account_runs(active_vault: Any, *, keep: Optional[int] = None) -> Dict[str, Any]:
    """Delete older ``run-*`` siblings of the active vault's run directory."""

    keep_count = configured_keep_runs() if keep is None else min(max(int(keep), 1), MAX_KEEP_RUNS)
    try:
        vault = Path(active_vault).resolve(strict=True)
    except (OSError, TypeError):
        return {"status": "skipped", "reason": "active-vault-missing", "removed": 0}
    active_run = vault.parent
    account_dir = active_run.parent
    if (
        vault.name != "decrypted"
        or not RUN_NAME.fullmatch(active_run.name)
        or not ACCOUNT_DIR_NAME.fullmatch(account_dir.name)
    ):
        return {"status": "skipped", "reason": "unrecognized-layout", "removed": 0}
    uid = os.getuid() if hasattr(os, "getuid") else None
    runs = []
    try:
        entries = list(account_dir.iterdir())
    except OSError:
        return {"status": "skipped", "reason": "account-dir-unreadable", "removed": 0}
    for entry in entries:
        if not RUN_NAME.fullmatch(entry.name):
            continue
        try:
            info = entry.lstat()
        except OSError:
            continue
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            continue
        if uid is not None and info.st_uid != uid:
            continue
        runs.append(entry)
    runs.sort(key=lambda path: path.name, reverse=True)
    kept = [active_run]
    for run in runs:
        if len(kept) >= keep_count:
            break
        if run != active_run:
            kept.append(run)
    removed = 0
    failed = 0
    for run in runs:
        if run in kept:
            continue
        try:
            shutil.rmtree(run)
            removed += 1
        except OSError:
            failed += 1
    return {
        "status": "complete" if failed == 0 else "partial",
        "kept": len(kept),
        "removed": removed,
        "failed": failed,
        "keep_runs": keep_count,
    }
