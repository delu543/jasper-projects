# Project Observatory · 项目开发观测台

一个项目，一份目标与验收状态，一个本地面板。把项目全景开发面板与原进度观测台融合：目标、开发阶段、问题、任务职责、Git 与验收证据在同一处维护。

不把代码活动自动记作完成。代码验收必须关联当前干净提交、证据与验证环境；旧证据保留，但版本变化后显示待复核。

## 三步使用

需要 Node.js 20+；没有运行时 npm 依赖。

```sh
git clone --single-branch --branch main https://github.com/delu543/jasper-projects.git
cd jasper-projects/projects/developer-tools/project-observatory
node bin/project-observatory.mjs init --project /absolute/path/to/your-project --lang zh
node bin/project-observatory.mjs serve --project /absolute/path/to/your-project --port 4187
```

打开终端显示的本地 URL。端口被占用时使用 `--port 0` 自动选择；`Ctrl-C` 关闭服务。`init` 不覆盖已有状态，不运行目标项目的脚本，数据位于目标项目的 `.project-observatory/project.json` 并被当前 checkout 的 Git 排除。

## 同一张面板里做什么

- **目标与进度：** 写清用户结果，按上游方案、中游实现、下游验收维护检查点、负责人和下一步。
- **问题与任务：** 记录影响、证据和处理状态；可为发现的 Codex 任务关联阶段与职责。
- **实时信号：** 查看 Git、项目结构和可用检查入口；Codex、GitHub 为默认关闭的可选只读来源。
- **验收分层：** 记录本地、真实环境或交付层级；验收证据必须对应版本和环境。代码改变或 Git 来源失效后不继续计入通过。
- **Agent 协作：** 生成可编辑的 Codex / Claude 任务草稿，或读取完整 JSON 上下文。复制草稿不发送消息、不自动执行。
- **一致保存：** 浏览器与多服务实例使用同一状态文件，旧版本编辑返回冲突；外部修改约每 2 秒刷新。页面隐藏时停止快速采集。

检查点、问题和任务支持统一搜索。完整流程使用同一份数据，不维护平行的“进度条状态”。

## 给 Codex 或 Claude 读取

先读取 [AGENTS.md](AGENTS.md)，再按目标项目取得最新上下文：

```sh
node bin/project-observatory.mjs context --project /absolute/path/to/your-project
```

该命令只读项目状态与已启用的来源；输出目标、问题、职责、版本和证据，不执行构建、测试、部署或发送消息。`doctor` 检查状态格式；`refresh` 显式保存当前采集结果。

## 导入原进度观测台

在目标项目仍保留 `.progress-observatory/board.json` 时，先预览：

```sh
node bin/project-observatory.mjs migrate --project /absolute/path/to/your-project
```

核对数量后加 `--apply`。导入保留目标、全部检查点、问题、任务映射、备注和证据；原文件不改动。已存在新状态时拒绝覆盖。短提交号仅在目标项目内可唯一解析时转换为完整 SHA；未知版本或缺失环境的旧验收保持待复核。旧 `project-progress` 命令名作为同一 CLI 的兼容别名保留，不再带第二套服务器。

## 本地与安全

服务只监听 `127.0.0.1`，写入检查 Host、Origin、会话令牌与状态版本。没有任意文件浏览器、命令执行、遥测或账户。Git 不自动 fetch/push；只有启用 GitHub 来源后才使用当前用户的 gh 身份读取远端信号。

Codex 来源仅读取当前项目内匹配的本机任务与有限公开进展；未配置或不可用时，其余功能继续工作。不宣称能自动发现 Claude 会话；Claude 通过通用上下文与任务草稿使用面板。

## 开发

```sh
npm test
npm run check
```

[能力矩阵](docs/CAPABILITY_MAP.md) · [融合与兼容说明](docs/INTEGRATION.md) · [架构与边界](docs/ARCHITECTURE.md)

MIT 许可；两个原看板均为同一作者的 MIT 项目，来源版本与适配范围记录在融合说明中。
