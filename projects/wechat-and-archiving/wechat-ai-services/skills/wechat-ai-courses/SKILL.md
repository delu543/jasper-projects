---
name: wechat-ai-courses
description: 按用户授权的本地课程清单选音频优先、断点转写、保留讲义并逐合集生成完整 Word。
---

# wechat-ai-courses

读取 docs/COURSES.md；python3 wechat_ai.py run courses -- plan <manifest>，用户核对层级/数量后 run <manifest> --model <本地模型>。不读取课程登录状态，不自动下载模型，不擅自改正人名。

## 运行位置与安装

执行前读取[统一运行约定](../COMMON.md)。本 Skill 只说明当前目标所需的输入与操作。
