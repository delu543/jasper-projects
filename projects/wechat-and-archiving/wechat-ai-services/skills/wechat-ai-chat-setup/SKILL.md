---
name: wechat-ai-chat-setup
description: 仅在用户显式调用时初始化当前微信账号，独立确认初始化与私有快照保留。
---

# wechat-ai-chat-setup

仅用户显式调用 $wechat-ai-chat-setup 或原 $wechat-local-export-setup 时进入。以 components/chat 中 live_tools 的初始化程序和 references/contract.md 为准。不能从安装、导出或路由触发初始化。

## 运行位置与安装

执行前读取[统一运行约定](../COMMON.md)。本 Skill 只说明当前目标所需的输入与操作。

执行前完整读取 [能力与安全契约](references/contract.md)。
