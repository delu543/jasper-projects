# 迁移与历史

[返回项目分类](../README.md)

本合集收录 Jasper 的 9 个公开项目，分为内容创作、微信与媒体归档、开发工具和网络配置四类。源码迁移基线为 2026-10-31（America/Los_Angeles）。

## 保留内容

- 每个公开项目默认分支的完整源码树，按分类原样放入 projects/。
- 所收录项目的原始 Git 提交、作者信息、分支与标签。
- 原许可证、第三方声明、项目文档和工作流文件。
- MP3 项目的 2 个历史 Release、6 个原始附件。

本次整理验证源码与分发入口一致性，不代表重新完成每个产品的实机、媒体、付费服务或用户验收。

## 项目对应关系

| 原项目名称 | 当前目录 | 默认分支基线 |
| --- | --- | --- |
| ai-video-production | [projects/content-creation/ai-video-production](../projects/content-creation/ai-video-production) | `d4bdf05e4d6cd1b4e9654dc824c3586cfdd5ef01` |
| claude-residential-ip-rules | [projects/networking/claude-residential-ip-rules](../projects/networking/claude-residential-ip-rules) | `b7cddaf6ddba1e233a7045ed57eb1b0a7c08a784` |
| digital-human-workflow | [projects/content-creation/digital-human-workflow](../projects/content-creation/digital-human-workflow) | `c304c12c2a4f3e442ecb44a5f583fac40c72b509` |
| project-observatory | [projects/developer-tools/project-observatory](../projects/developer-tools/project-observatory) | `35555b15b7a7c63b09e7501998d8daffff269186` |
| project-progress-observatory | [projects/developer-tools/project-progress-observatory](../projects/developer-tools/project-progress-observatory) | `ff6f7a7370a48fe4050e9db60e60483ccf19c893` |
| wechat-ai-services | [projects/wechat-and-archiving/wechat-ai-services](../projects/wechat-and-archiving/wechat-ai-services) | `5ecafff2a5f0ae3ed1f50af34c9b4adb0a2870e4` |
| wechat-data-extraction | [projects/wechat-and-archiving/wechat-data-extraction](../projects/wechat-and-archiving/wechat-data-extraction) | `1c340a063837c7ea7981b55dbdf93c684ae13903` |
| wechat-public-account-archiver | [projects/wechat-and-archiving/wechat-public-account-archiver](../projects/wechat-and-archiving/wechat-public-account-archiver) | `0bd40506d1eee0f167638c2006b3efe8d7a2ee36` |
| weixin-replay-to-mp3 | [projects/wechat-and-archiving/weixin-replay-to-mp3](../projects/wechat-and-archiving/weixin-replay-to-mp3) | `4cec3daecf67d65ec10eb5f1ef0c86783efbe514` |

## 历史命名

- 原分支：`history/<项目名>/<原分支名>`。
- 原标签：`<项目名>/<原标签名>`。
- 所收录项目的原始提交 SHA 不变；分类导入提交以原默认分支提交为父提交，保留历史可达性。
- history 分支保持迁移快照；新开发从总仓库 main 的分类目录开始。

[逐项目机器可读清单](migration-manifest.json)

## 入口与兼容

安装时使用[独立克隆命令](getting-started.md)，以便依赖 Git 根目录的工具继续在原目录结构中运行。Windows MP3 使用迁移后的[便携包下载](downloads.md)。

项目内旧 URL、来源锁定文件和历史验证报告保留原文，作为来源与版本证据；它们不是迁移后的推荐安装入口。原仓库 URL、Stars、Fork 网络、Issue/PR 编号和 Actions 页面不会自动变成总仓库中的同等对象。

分类目录中的 .github/workflows 原样保留。总仓库暂不自动执行这些依赖独立目录与环境的工作流。

## 合集历史调整

合集已按仓库所有者确认的公开范围重新整理主分支历史。其余公开项目的源码和历史分支保持原样。曾克隆旧合集的使用者应重新克隆当前版本；不要将旧合集的 main 合并或推回本仓库。
