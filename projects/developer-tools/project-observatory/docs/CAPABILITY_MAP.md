# 能力矩阵

| 能力 | 状态 | 验证或边界 |
| --- | --- | --- |
| 单项目状态、目标与用户结果 | active | 目标、说明、备注写入一份 project.json |
| 上中下游检查点与下一步 | active | 负责人、完成条件、证据和验证环境 |
| 本地 / 真实 / 交付验收 | active | 完整当前提交与干净树；旧证据保留待复核 |
| 问题跟踪与任务职责映射 | active | 与验收状态独立，同一 API 与 revision |
| Git、结构与可用脚本 | active | 仅读取，不运行目标项目脚本 |
| Codex / GitHub 实时信号 | optional | 默认关闭；失效显示过期，任务活动不作验收 |
| 搜索、双语与实时刷新 | active | 检查点/问题/任务统一搜索；页面隐藏暂停快速采集 |
| Codex / Claude 任务草稿与 JSON | active | 可编辑草稿与只读 context，不自动发送 |
| 旧 board.json 导入 | replaced | 预览 / apply；原文件不改，新状态存在则拒绝覆盖 |
| 旧 project-progress 命令 | compatibility | 指向同一个 CLI、模型和服务器 |

Removed / Changed Existing Capabilities：两套并行模型与 UI 已合为一套。旧独立项目目录退役；其目标、问题、映射和验收能力由当前项目承接。原本缺失验证环境的代码验收不再计为当前通过。
