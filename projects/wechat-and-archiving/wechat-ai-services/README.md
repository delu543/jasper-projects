# 微信 AI 服务

把微信聊天、公众号文章、回放与课程整理成可保存、可核验的档案。Codex 和 Claude 使用同一份任务说明与命令入口。

原“微信数据提取”和“公众号本地归档”已融合到本项目：聊天只有一份解析与导出引擎；公众号只有一份归档、去重和交付状态。各能力按结果组织，不需要判断该打开哪个旧项目。

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

## 适用范围

聊天支持 macOS；Windows 聊天仍是实机待验的源码预览。公众号可见会话流程为 macOS。回放目录与 MLX 转写为 Apple Silicon 开发预览；媒体核心支持 macOS / Windows。没有把合成回归当作所有电脑与账号的实机验收。[能力与验证边界](docs/CAPABILITY_MAP.md)

账号、消息、媒体、数据库、模型和交付文件保存在本机。聊天初始化、私有快照、临时代理、发送消息与模型下载分别判断授权，不相互继承。

[Skills 导航](skills/README.md) · [统一执行约定](skills/COMMON.md) · [融合与旧数据迁移](docs/INTEGRATION.md) · [许可范围](docs/LICENSE_SCOPE.md) · [来源](docs/SOURCES.md)
