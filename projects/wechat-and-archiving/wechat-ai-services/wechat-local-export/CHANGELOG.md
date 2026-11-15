# Changelog

## 0.3.0-dev.1

- `daily-digest`：一次在线刷新（contact + 全部已初始化 `message_N`）后读取多个聊天；
  默认选择置顶聊天（`contact.flag & 0x800`），可用私有清单文件指定；每聊天游标
  `(create_time, sort_seq)` 存于 `state/digest-state.json`（0600）；输出 `daily/*.json`（0600），
  14 天自动清理；支持 `--since`、`--dry-run`、`--no-refresh`、`--init-cursors-at`、`--mention-name`；
  微信关闭或刷新失败时退回上次已验证快照并标记 `stale`。
- 快照保留：每次在线刷新并切换 profile 后自动删除同账号旧 `run-*`，默认保留 1 个
  （`WECHAT_LOCAL_EXPORT_KEEP_RUNS`），永不删除当前 vault；失败不影响刷新结果。
- 发送者解析：扫描计划新增 `sender_username`、`sender_display_name`、`sender_is_self`，
  通过 `Name2Id` + contact 解析 1:1 聊天与本人群发言的数字 id；归档 transcript 使用显示名。
- 新模块：`content_vault/identity.py`、`content_vault/digest.py`、`live_tools/snapshot_retention.py`；
  新测试：`content_vault/tests/test_digest.py`、`live_tools/tests/test_snapshot_retention.py`、
  `portable_skill/tests/test_daily_digest.py`，以及在线刷新的全分片/保留测试。
