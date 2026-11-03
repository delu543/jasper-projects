# 项目开发观测台

这是两个原看板融合后的唯一实现。`lib/config.mjs` 与 `lib/project.mjs` 定义一份项目状态，`lib/server.mjs` 和 `public/` 提供一个界面。

用户指定目标项目后，先运行 `node bin/project-observatory.mjs context --project <绝对路径>` 读取目标、问题、任务职责、版本与验收。状态不存在时先询问是否初始化；打开本仓库不会自动初始化其他项目。

数据与验收规则：

- 仅操作用户指定项目的 `.project-observatory`；原 `.progress-observatory` 只能显式 `migrate`，默认预览，`--apply` 才写新状态，原文件保留。
- 代码验收要求当前干净完整 Git SHA、证据和环境。任务活动、旧版测试或来源失效不能替代当前验收。
- UI 写入必须保留期望 revision、当前提交检查和同源令牌；不要绕过冲突覆盖其他编辑。
- Codex、GitHub 来源默认关闭。上下文和草稿可由 Codex / Claude 使用，但不因此获得发送消息、读取其他项目或执行业务脚本的授权。
- 本地测试使用合成临时项目，不用用户真实项目作测试夹具。修改后运行 `npm test` 与 `npm run check`；新增 UI/API 功能要核验实际路径。
