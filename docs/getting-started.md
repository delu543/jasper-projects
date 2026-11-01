# 使用与安装

[返回项目分类](../README.md)

源码总目录便于浏览；安装时推荐以下单项目克隆方式。每条命令都从本总仓库获取一个完整的原项目，保留它需要的独立 Git 根目录。

这些 history 分支保存迁移时的公开版本，不是自动更新通道。原 README 中的旧仓库 clone、npx、skills add 或远程下载地址不再作为统一入口，请使用本页命令和[下载中心](downloads.md)。克隆后继续阅读本地文档中的功能、授权及平台说明。

以下命令是供选择项目后执行的操作说明；浏览本仓库不会运行它们。不要将现有项目的 main 直接推到总仓库 main。

<a id="ai-video-production"></a>
## AI 视频制作

把视频需求推进到成片：真实素材研究、配音、字幕、混音与验收。

```sh
git clone --single-branch --branch history/ai-video-production/main https://github.com/delu543/jasper-projects.git ai-video-production
cd ai-video-production
```

Python 3.9+；渲染需要 FFmpeg/FFprobe、libass 与字体。

```sh
python3 scripts/install_skill.py
python3 skills/ai-video-production/scripts/video.py doctor
```

[项目说明](../projects/content-creation/ai-video-production/README.md) · [源码](../projects/content-creation/ai-video-production)

<a id="digital-human-workflow"></a>
## 数字人工作流

将授权文案与声像制作成数字人口播、广告短片及可编辑素材包。

```sh
git clone --single-branch --branch history/digital-human-workflow/codex/initial-release https://github.com/delu543/jasper-projects.git digital-human-workflow
cd digital-human-workflow
```

克隆后请 Codex 阅读本地 INSTALL_FOR_CODEX.md。使用自己的授权声像与服务账号；生成费用另行确认。

[项目说明](../projects/content-creation/digital-human-workflow/README.md) · [源码](../projects/content-creation/digital-human-workflow)

<a id="wechat-ai-services"></a>
## 微信 AI 服务

统一调用聊天导出、公众号归档、直播与课程转 Word、媒体转 MP3；开发预览。

```sh
git clone --single-branch --branch history/wechat-ai-services/main https://github.com/delu543/jasper-projects.git wechat-ai-services
cd wechat-ai-services
```

先检查环境，再让 Codex 按本地 docs/FIRST_RUN.md 安装所需服务。Skill 入口位于 skills/。

```sh
python3 wechat_ai.py doctor all
```

[项目说明](../projects/wechat-and-archiving/wechat-ai-services/README.md) · [源码](../projects/wechat-and-archiving/wechat-ai-services)

<a id="wechat-data-extraction"></a>
## 微信数据提取

按会话和时间导出本机微信消息与媒体，并提供直播转 Word 的独立工作流。

```sh
git clone --single-branch --branch history/wechat-data-extraction/main https://github.com/delu543/jasper-projects.git wechat-data-extraction
cd wechat-data-extraction
```

macOS 从 scripts/codex_bootstrap.sh doctor 开始；Windows 从 scripts/codex_bootstrap.ps1 doctor 开始。聊天初始化与导出范围分别授权。

[项目说明](../projects/wechat-and-archiving/wechat-data-extraction/README.md) · [源码](../projects/wechat-and-archiving/wechat-data-extraction)

<a id="wechat-public-account-archiver"></a>
## 公众号本地归档

按公众号整理公开文章与短内容，增量去重、保留进度并输出 Word；当前以被动缓存路线为主。

```sh
git clone --single-branch --branch history/wechat-public-account-archiver/main https://github.com/delu543/jasper-projects.git wechat-public-account-archiver
cd wechat-public-account-archiver
```

macOS。检查不会自动归档；安装和启动请按本地 README.md 的对应步骤进行。

```sh
./install.sh --check
```

[项目说明](../projects/wechat-and-archiving/wechat-public-account-archiver/README.md) · [源码](../projects/wechat-and-archiving/wechat-public-account-archiver)

<a id="weixin-replay-to-mp3"></a>
## 链接与回放转 MP3

将有权处理的视频号、课程、网页媒体或本地音视频转成经完整解码验证的 MP3。

```sh
git clone --single-branch --branch history/weixin-replay-to-mp3/main https://github.com/delu543/jasper-projects.git weixin-replay-to-mp3
cd weixin-replay-to-mp3
```

此命令用于 macOS；Windows x64 优先使用下方下载中心的固定便携包。

```sh
python3 scripts/bootstrap.py doctor
```

[项目说明](../projects/wechat-and-archiving/weixin-replay-to-mp3/README.md) · [源码](../projects/wechat-and-archiving/weixin-replay-to-mp3)

Windows：[固定便携包与校验方法](downloads.md#windows-mp3)。优先离线安装，不调用旧仓库的在线 bootstrap 下载路径。

<a id="project-observatory"></a>
## 项目全景开发面板

用本地看板呈现目标、开发、验证、交付和运行阶段，结合 Git 与可选 Codex 活动。

```sh
git clone --single-branch --branch history/project-observatory/main https://github.com/delu543/jasper-projects.git project-observatory
cd project-observatory
```

Node.js 20+ 和 Git。把示例目标路径替换成自己的项目。

```sh
node bin/project-observatory.mjs init --project /absolute/path/to/your-project
node bin/project-observatory.mjs serve --project /absolute/path/to/your-project
```

[项目说明](../projects/developer-tools/project-observatory/README.md) · [源码](../projects/developer-tools/project-observatory)

<a id="project-progress-observatory"></a>
## 项目进度观测台

按项目维护里程碑、验收证据和实时活动；开发活动与已验收成果分开显示。

```sh
git clone --single-branch --branch history/project-progress-observatory/main https://github.com/delu543/jasper-projects.git project-progress-observatory
cd project-progress-observatory
```

Node.js 20+；无需 npm install。目标项目路径需自行指定。

```sh
node bin/project-progress.mjs init --project /absolute/path/to/your-project
node bin/project-progress.mjs serve --project /absolute/path/to/your-project --port 4180
```

[项目说明](../projects/developer-tools/project-progress-observatory/README.md) · [源码](../projects/developer-tools/project-progress-observatory)

<a id="claude-residential-ip-rules"></a>
## Claude 网络配置规则

识别本机环境，按 Claude、普通外网和直连用途生成分流方案，提供检查与回滚工具。

```sh
git clone --single-branch --branch history/claude-residential-ip-rules/main https://github.com/delu543/jasper-projects.git claude-residential-ip-rules
cd claude-residential-ip-rules
```

先查能力与目标环境；网络方案应用、手机导入和实机验收是后续独立步骤。

```sh
python3 scripts/universal.py capabilities
```

[项目说明](../projects/networking/claude-residential-ip-rules/README.md) · [源码](../projects/networking/claude-residential-ip-rules)
