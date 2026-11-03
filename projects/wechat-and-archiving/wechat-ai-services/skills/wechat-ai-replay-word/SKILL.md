---
name: wechat-ai-replay-word
description: 账号直播回放批量转写、恢复并合并为一份完整 Word，目录、音轨、转写与渲染分层验收。
---

# wechat-ai-replay-word

python3 wechat_ai.py run replay -- configure / prepare / capture / batch / dashboard / transcribe / word / assemble。先读 references/contract.md 和 references/upstream/workflow.md；配置使用套件 configure，其余子命令参数保持原脚本契约。

## 运行位置与安装

执行前读取[统一运行约定](../COMMON.md)。本 Skill 只说明当前目标所需的输入与操作。

执行前完整读取 [能力与安全契约](references/contract.md)。

## 整账号单份 Word

- `python3 wechat_ai.py doctor replay` 只读检查环境与渲染器可用性，不下载模型。
- 批次恢复使用 `python3 wechat_ai.py run replay -- batch <配置路径> --verified-audio-only`；先核实失败原因、旧计数和活动 worker。
- 只有特定序号获得额外尝试授权后才加 `--extra-asr-ordinals <序号列表>`，每场在原两次上限之外最多一次。
- 所有逐场 Word 渲染验收完成后执行 `python3 wechat_ai.py run replay -- assemble <配置路径> <新的完整Word路径>`。组装会重算冻结目录条目并逐段比对当前转写和已验收 Word。
- 合并结果仍需单独渲染、全页自动检查以及异常页/代表页目视；组装成功不会自动标记最终验收完成。
- 面板 `review_pending` 表示逐场 Word 已齐但验收未齐，`review_complete` 表示逐场已验但未完成最终交付；`complete` 依赖任务完成记录，不能替代最终 Word 证据。
- schema 2 与旧 ASR 缓存并存，由指针确定当前转写。旧 Word 不覆盖；更换 builder 后签名变化需使用新输出路径并重新验收。

执行恢复前完整读取 [故障诊断与验收](references/upstream/recovery-and-acceptance.md)。
