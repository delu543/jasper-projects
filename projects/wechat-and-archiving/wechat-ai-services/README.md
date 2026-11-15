# 微信 AI 服务

WeChat AI Services. 这是合集中的一个项目：把本机微信数据库扫描、聊天导出、公众号文章、回放、课程和媒体转音频放在同一份说明里。Codex、Claude 和只读本仓库的助手使用同一份入口。

## 项目组成

| 部分 | 位置 | 做什么 |
| --- | --- | --- |
| 本机数据库扫描与导出 | [wechat-local-export/](wechat-local-export/) | WeChatLocalExport `0.3.0-dev.1`：在线刷新、日报 `daily-digest`、快照保留、发送者显示名。其他 AI 从 [GUIDE.md](wechat-local-export/GUIDE.md) 读起 |
| 套件聊天与回放 | [components/chat](components/chat/README.md) | 已融合的解析、精确导出、语音 MP4 与回放引擎，经 `wechat_ai.py` 调用 |
| 公众号 | [components/articles](components/articles/README.md) | 一份归档、去重、增量与交付状态 |
| 媒体 | [components/media](components/media/README.md) | 链接或本地文件转 MP3，并做完整解码核验 |
| 课程 | [services/courses.py](services/courses.py) | 复用回放的本地转写与 Word |
| 可移植 Skill | [portable_skill/skills](wechat-local-export/portable_skill/skills/) | `wechat-local-export` 与仅能显式调用的 `wechat-local-export-setup` |

GUIDE 里的「本仓库」就是 `wechat-local-export/` 这个目录。安装检查用 [scripts/codex_bootstrap.sh](wechat-local-export/scripts/codex_bootstrap.sh)。工具链自己的代理说明是 [AGENTS.md](wechat-local-export/AGENTS.md)。

The Mac WeChat DB scan/export toolchain lives in [wechat-local-export/](wechat-local-export/). Other agents start at [GUIDE.md](wechat-local-export/GUIDE.md). Suite tasks still start at `python3 wechat_ai.py`.

## 先选你要的结果

| 目标 | 任务入口 | 交付 |
| --- | --- | --- |
| 聊天消息、附件或选定语音 | `chat-export` / `chat-voice-mp4` | 按会话、时间、类型归档；选定语音可合成 MP4 |
| 更新已登记公众号 | `articles-update` | 保留缓存增量、去重、缺口报告与待验 Word |
| 归档公众号可见历史 | `articles-history` | 精确账号、日期范围的文章与媒体档案 |
| 添加公众号、管理订阅 | `articles-subscribe` | 保存种子与范围，复用同一份文章库 |
| 账号回放或课程合集 | `replay-word` / `courses-word` | 断点转写、完整 Word；课程保留讲义 |
| 链接或本地媒体转音频 | `media-mp3` | 时长和完整解码核验后的 MP3 |

## 从这里开始

```sh
git clone --single-branch --branch main https://github.com/delu543/jasper-projects.git
cd jasper-projects/projects/wechat-and-archiving/wechat-ai-services
python3 wechat_ai.py plan articles-update
```

`plan` 只返回所需输入、对应 Skill 和后续命令，不运行服务或访问账号。告诉 Agent 目标、素材和范围，它会先读 [AGENTS.md](AGENTS.md)，再检查所选环境：

```sh
python3 wechat_ai.py doctor articles
```

用户要求安装或使用后，按 [首次使用](docs/FIRST_RUN.md)仅安装所需服务。运行形式统一为 `python3 wechat_ai.py run <服务> -- <动作与参数>`；[完整任务与命令导航](docs/capabilities.json)可供 Agent 直接读取。

## 公众号更新的顺序

1. `run articles -- cache-update --check` 核对已有缓存、范围、交付回执和缺口；没有配置时报告待配置，不初始化数据库。
2. 已明确采集范围后，使用同一命令的 `--collect` 做有界缓存收集。空缓存不会自动启动前台恢复或旧调度。
3. 导出时明确使用 `--export --accept-discovered`。可见正文、未知覆盖和全部历史完整性分别记录，不把“找到一些文章”写成“已经收齐”。
4. Word 渲染与检查通过后才确认交付回执；下次从同一份回执去重。正文变化仍需复核，不静默覆盖。

可见历史、订阅和本地控制台都复用这一文章引擎。被动缓存之外的账号接入与初始化仍需相应明确授权。[公众号操作说明](skills/wechat-ai-articles/SKILL.md)

## 本机数据库扫描的前提

在用户自己的 Mac 上使用 `wechat-local-export` 时需要：

- Apple Silicon（arm64）Mac
- 官方微信 4.x 已登录，并保持打开
- 终端或代理进程拥有完全磁盘访问权限，才能读取本机微信容器
- 每个账号的密钥初始化只在用户明确发出 `$wechat-local-export-setup` 之后进行；安装依赖、取密钥、保留私有解密快照分别确认

## 已验证与未验证

`wechat-local-export` 已在真实环境验证的范围：arm64 Mac、系统完整性保护保持开启、官方 Mac 微信 4.1.x（作者机器为 4.1.15）、单账号；文字扫描、语音 MP4、日报 `daily-digest`。

尚未实机验证、只能当源码预览的范围：Intel Mac、微信 3.x、其他 4.x 小版本、多个 `message_N` 分片同时活跃、Windows。未知版本按诊断状态处理。

套件其余能力：公众号可见会话为 macOS；回放目录与 MLX 转写、课程 MLX 为 Apple Silicon 开发预览；媒体核心支持 macOS / Windows。合成测试不等于每台电脑、每个账号都已验收。[能力与验证边界](docs/CAPABILITY_MAP.md)

## 安全边界

只处理用户有权访问的本机数据。扫描与导出不上传聊天内容，不操作微信界面，不修改官方微信应用和它的实时数据库。密钥不进入命令行、环境变量、日志或本仓库。聊天初始化、私有快照、临时代理、发送消息和模型下载各自单独授权，不互相继承。账号、消息、媒体、数据库和交付文件留在本机。

[Skills 导航](skills/README.md) · [统一执行约定](skills/COMMON.md) · [融合与旧数据迁移](docs/INTEGRATION.md) · [许可范围](docs/LICENSE_SCOPE.md) · [来源](docs/SOURCES.md)
