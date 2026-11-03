---
name: wechat-ai-services
description: 统一识别微信聊天导出、链接转音频、直播转 Word、课程合集和公众号归档，保持各能力独立权限。
---

# wechat-ai-services

先运行 `python3 wechat_ai.py capabilities` 查看任务索引，使用 `plan <任务>`取得同一份执行路线；按用户目标选择以下 Skill，再运行所选服务的 `python3 wechat_ai.py doctor <service>`；不要因链接都来自微信而混用权限。

## 运行位置与安装

执行前读取[统一运行约定](../COMMON.md)。本 Skill 只说明当前目标所需的输入与操作。

## 确定路由

- `wechat-ai-chat`：按精确聊天、时间和内容类型导出本机微信，保留扫描确认和严格媒体校验。
- `wechat-ai-chat-setup`：仅在用户显式调用时初始化当前微信账号，独立确认初始化与私有快照保留。
- `wechat-ai-media`：本人有权处理的链接或本地媒体转 MP3，保留来源绑定、断点下载与完整解码。
- `wechat-ai-replay-word`：账号直播回放生成一份完整 Word，目录、音轨、转写、Word 分层验收。
- `wechat-ai-articles`：从公开文章链接发现精确账号历史并在本机归档，支持日期边界与可见会话恢复。
- `wechat-ai-subscriptions`：添加公众号或更新全部公众号到今天，精确 biz、重叠去重和增量 Word。
- `wechat-ai-courses`：按用户授权的本地课程清单选音频优先、断点转写、保留讲义并逐合集生成完整 Word。

有歧义时询问目标产物；不要通过实际访问账号来猜测。多目标按依赖顺序处理；共享限制暂停所有受影响请求，独立已授权步骤继续。
