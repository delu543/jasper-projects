# 微信本地数据提取（WeChat Local Export）— 给 AI 代理的搭建指南

> 读者：帮用户在**他自己的 Mac**上搭建本项目的 AI 代理（Codex、Claude Code、Grok 等）。
> 目标：不从头写代码，按本指南即可让用户在本机读取**自己账号**的微信 4.x 聊天数据：
> 按聊天/时间扫描、导出文字/图片/语音/文件、合成语音 MP4、生成多聊天日报 JSON。
> 一切只在本机进行；不上传聊天内容；不操作微信界面；不改动微信原版应用和实时数据库。

## 0. 验证范围（请如实告诉用户）

- **已在真实环境验证**：Apple Silicon（arm64）Mac、macOS 系统完整性保护（SIP）保持开启、
  官方 Mac 微信 4.1.x（作者机器为 4.1.15）、单账号；文字扫描、语音 MP4、日报 `daily-digest`。
- **未验证 / 仅源码预览**：Intel Mac、微信 3.x、其它 4.x 小版本、多个 `message_N` 分片同时活跃、
  Windows（`live_tools/windows`，只有合成数据测试）。未知版本按“诊断状态”处理，不要假设兼容。
- 页 HMAC 未校验；解密正确性靠 AES 结构校验 + SQLite `quick_check` + 必需表检查。

## 1. 前置条件

- macOS（arm64），已安装 Xcode Command Line Tools（`xcode-select --install`，用于构建 Swift 媒体工具）。
- 系统自带 `/usr/bin/python3`（3.9+）。运行时依赖由安装脚本装进私有目录，不污染系统。
- 官方微信 4.x，已登录要读取的账号，并保持打开。
- 终端（或代理所在进程）需要“完全磁盘访问权限”，才能读取
  `~/Library/Containers/com.tencent.xinWeChat/...`。
- 一次性取密钥阶段需要 Frida（由 setup 脚本装进**独立**私有虚拟环境，版本与哈希固定）。

## 2. 安装

```bash
git clone <本仓库> && cd <仓库目录>
./scripts/codex_bootstrap.sh doctor      # 检查环境，输出 status=ready / needs_install
./scripts/codex_bootstrap.sh install     # 私有 Python 运行时 + 构建 Swift 工具 + 安装 Skill
```

安装位置：`~/Library/Application Support/WeChatLocalExport/`

```text
app/releases/<version>-<hash>/   源码 release（不可变）；app/current -> 当前 release
app/install.json                 当前 release 与源码哈希
tools/python/                    运行时 Python（含 zstandard 等）
key-init-tools/                  仅一次性取密钥用的独立环境（Frida、pycryptodome）
profiles/account-<ref>.json      每账号非机密 profile：vault_dir / account_root（0600）
snapshots/account-<ref>/run-*/   在线快照（默认只保留最新 1 个）
state/digest-state.json          日报游标（0600）
daily/<日期>_<时间>.json          日报（0600，默认保留 14 天）
```

Skill 以软链安装到 `~/.agents/skills/`（`wechat-local-export`、`wechat-local-export-setup`）。

## 3. 每个账号一次性初始化（必须由用户明确发起）

调用 `$wechat-local-export-setup`。它会做（代码在 `live_tools/wechat_key_init.py`）：

1. 用当前官方微信进程打开的文件（lsof，两次采样一致）**唯一绑定**当前登录账号；
   不按目录修改时间、大小等启发式选账号。
2. 校验 `/Applications/微信.app` 的 Apple 签名、Team ID（5A4RE8SF68）和 CDHash。
3. 把官方微信**复制**到私有目录，对**副本**做 ad-hoc 重签（`codesign --force --deep --sign -`），
   原版应用不做任何修改，也不需要关闭 SIP。
4. 让用户退出原版微信后，用 Frida **spawn 这个副本**，hook `CCKeyDerivationPBKDF`；
   用户在副本里登录同一账号。
5. 只接受能匹配某个数据库 16 字节 salt、并能解出合法 SQLCipher 第一页的候选密钥；
   候选只在内存中，匹配后丢弃其它。
6. 最终密钥写入 0700 私有目录下的 0600 文件（当前实现：
   `~/Library/Application Support/WeChatVoiceMP4/private/wechat-db-keys.json`，按账号时在
   `accounts/<account-ref>/` 下）。密钥绝不进入命令行参数、环境变量、stdout、日志或仓库。
7. 用户正常退出副本，运行 cleanup，再打开原版微信即可。之后日常使用不再需要副本。

需要用户分别确认：安装依赖、对当前账号取密钥、保留私有解密快照。代理不得自行推断同意。

## 4. 日常使用（自然语言 → 客户端命令）

客户端：`<skill_dir>/scripts/wechat_local_export_client.py`（只接受高层命令，不接收任何密钥）。

| 命令 | 作用 |
|---|---|
| `doctor` | 绑定当前账号、检查 profile/快照/依赖是否就绪 |
| `scan --request <0600 JSON> --output plan.json` | 单聊天+时间范围+类型的只读扫描（会先做一次在线刷新） |
| `export --plan ... --confirm-digest ... --confirm-count ...` | 按用户确认的计划原子导出 |
| `direct-voice-mp4 --request ... --output-dir ...` | 一次完成语音扫描并导出 MP4 |
| `daily-digest [--since ...] [--dry-run] [--no-refresh] [--chats-file ...]` | 一次刷新、读取所有置顶（或清单）聊天，写私有日报 JSON |

scan 请求文件（目录 0700、文件 0600）：

```json
{"schema_version": 1, "chat": "群名或备注", "chat_id": null,
 "start": "2026-01-01 00:00:00", "end": "2026-01-01 23:59:59", "types": ["text"]}
```

日报：

```bash
python3 <client> daily-digest                       # 从各聊天游标（无游标则近 24 小时）读到现在，推进游标
python3 <client> daily-digest --dry-run --since "2026-01-01 08:00"   # 试跑，不推进游标
python3 <client> daily-digest --init-cursors-at "2026-01-01 08:00"   # 只设置游标
```

日报 JSON 每个聊天包含：显示名、类型、文字条数、非文字分类计数、前 5 名发言人（备注>昵称，识别“我”）、
@我的消息、我自己发的消息、最近若干条文字（默认 200 条、每条 500 字以内）。
置顶判断：`contact.flag & 0x800`。公众号消息不在 `message_N` 中，会以单聊天错误列出。
定时：可由 AI 助手的定时任务在 Mac 在线时调用；本项目不安装 LaunchAgent。

## 5. 在线刷新模型（为什么微信不用关）

1. 对 SQLite 的 WAL/SHM 协调字节加 OFD 共享锁，校验锁定状态下的 SHM/WAL 锚点；
2. APFS clone 加密主库与 WAL（写时复制，几乎不占额外空间）；
3. 只回放已提交的 WAL 帧，生成一致的加密快照；
4. 用已保存密钥逐页解密（4096 字节页、80 字节保留区、16 字节 IV、AES-256-CBC）到新的 `run-*/decrypted/`；
5. `quick_check` + 必需表检查 + doctor 通过后，**原子**更新 profile 的 `vault_dir`；失败则保留旧快照；
6. 之后按保留策略删除同账号旧 `run-*`（`WECHAT_LOCAL_EXPORT_KEEP_RUNS`，默认 1，永不删当前）。

单聊天 scan 只刷新 contact + 该聊天所在分片；`daily-digest` 刷新 contact + 所有已初始化的 `message_N`。
消息表名为 `Msg_<md5(chat_id)>`；内容可能是 zstd 压缩；1:1 聊天与自己在群里的发言用
`real_sender_id`（`Name2Id` 行号）表示发送者，本版本会解析成用户名和显示名。

## 6. 排错

- **微信大版本更新后取密钥失败 / task_for_pid / 签名不匹配**：setup 会重新校验官方签名和 CDHash；
  副本需按新版本重新复制、重签。已取得的密钥通常仍有效（密钥与数据库 salt 绑定，而非应用版本）。
- **“没有目标聊天表”/ 解密失败 / salt 变化**：账号重新登录、重装或数据库重建都会改变 salt，
  需要用户明确重新运行 setup。
- **微信未打开或无法唯一绑定账号**：scan 会停止；`daily-digest` 退回到上次成功绑定的账号与其最后一个
  已验证快照，并标记 `stale: true` 和 `data_as_of`。
- **新增分片**（如出现 `message_1.db`）：只有初始化时取过密钥的分片能被刷新；需要时重新 setup。
- **磁盘膨胀**：0.3.0 起自动保留最新快照；旧版本可手动删除 `snapshots/account-*/run-*`（保留 profile 指向的那个）。
- **Swift 构建报 module cache path 不一致**：删除 `.build/*/release/ModuleCache` 后重建。

## 7. 安全边界（代理必须遵守）

- 只读：不在微信里点击、输入、发送；不修改实时数据库；只对副本重签，绝不改原版应用；不关闭 SIP。
- 不打印、复制、提交密钥；不把密钥写进参数/环境变量/日志/仓库。
- 不上传聊天内容，不调用远程服务处理聊天内容；日报和导出只在本机（0600/0700）。
- 模糊或重名的聊天必须让用户选择，绝不自动挑一个。
- 导出前必须展示条数/时间范围并等待用户确认（`direct-voice-mp4` 是唯一明示例外）。
- 测试数据必须是合成数据；仓库里不得出现真实 wxid、群名、聊天内容或本机路径。

## 8. 测试

```bash
./scripts/release_check.sh   # 仓库扫描 + 包校验 + 全部单元测试 + Swift 构建与自检
```
