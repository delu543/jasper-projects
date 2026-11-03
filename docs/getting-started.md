# 使用与安装

[返回项目分类](../README.md)

当前功能使用下方指定入口。微信 AI 服务和项目开发观测台从 main 获取融合后的实现；其余未改项目保留独立历史快照克隆方式。

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

原微信数据提取和公众号归档已融合至此。当前功能从 main 获取，不使用旧项目的历史分支安装。

```sh
git clone --single-branch --branch main https://github.com/delu543/jasper-projects.git
cd jasper-projects/projects/wechat-and-archiving/wechat-ai-services
python3 wechat_ai.py plan articles-update
```

`plan` 不执行服务；查看任务所需素材、对应 Skill 和选定服务的 doctor 命令。聊天、公众号、回放和课程共用统一路由，并保留独立权限和平台边界。

[功能与使用](../projects/wechat-and-archiving/wechat-ai-services/README.md) · [首次使用](../projects/wechat-and-archiving/wechat-ai-services/docs/FIRST_RUN.md)

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
## 项目开发观测台

两个原看板共用一份目标、问题、进度和验收状态。Node.js 20+，无运行时 npm 依赖。

```sh
git clone --single-branch --branch main https://github.com/delu543/jasper-projects.git
cd jasper-projects/projects/developer-tools/project-observatory
node bin/project-observatory.mjs init --project /absolute/path/to/your-project --lang zh
node bin/project-observatory.mjs serve --project /absolute/path/to/your-project
```

Codex 或 Claude 使用 `context --project <绝对路径>` 读取同一份上下文。已有 `.progress-observatory/board.json` 时先用 `migrate` 预览，确认后 `--apply`；原文件保留。

[使用与迁移](../projects/developer-tools/project-observatory/README.md) · [能力与边界](../projects/developer-tools/project-observatory/docs/CAPABILITY_MAP.md)

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
