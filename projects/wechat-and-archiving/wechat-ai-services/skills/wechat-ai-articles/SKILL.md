---
name: wechat-ai-articles
description: 公众号保留缓存增量、精确历史归档、去重与 Word；区分已发现内容和完整覆盖。
---

# wechat-ai-articles

`python3 wechat_ai.py plan articles-update` 选择增量流程；默认先 `python3 wechat_ai.py run articles -- cache-update --check`。历史发现另用 `plan articles-history`。默认 127.0.0.1:8876；套件配置关闭调度与自动会话准备。执行会话恢复需先确认本轮授权。

## 运行位置与安装

执行前读取[统一运行约定](../COMMON.md)。本 Skill 只说明当前目标所需的输入与操作。

执行前完整读取 [能力与安全契约](references/contract.md)。
