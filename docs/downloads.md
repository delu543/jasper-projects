# 下载中心

[返回项目分类](../README.md)

这里保留原项目已发布的下载附件，文件内容与原 Release 一致。

<a id="windows-mp3"></a>
## MP3 工具 · Windows x64

**推荐：v0.5.0 便携包。** 内含所需 Python、媒体依赖、源码、Skill 与离线安装器。

[下载 ZIP](https://github.com/delu543/jasper-projects/releases/download/weixin-replay-to-mp3/v0.5.0/weixin-replay-to-mp3-windows-portable-v0.5.0.zip) · [查看 Release](https://github.com/delu543/jasper-projects/releases/tag/weixin-replay-to-mp3/v0.5.0)

- 文件大小：88,193,866 字节。
- SHA-256：`c362b8766af52b785525ea0819efbf86a89caedbd95816c72a9339f1e8b8fdb4`。

下载后在 PowerShell 中校验，确认与上面的哈希和字节数一致，再解压并运行包内的 install-offline.ps1：

```powershell
Get-FileHash .\weixin-replay-to-mp3-windows-portable-v0.5.0.zip -Algorithm SHA256
(Get-Item .\weixin-replay-to-mp3-windows-portable-v0.5.0.zip).Length
# 校验通过并解压后，进入包含 install-offline.ps1 的目录
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install-offline.ps1
```

安装器会在当前用户目录安装运行时和 Skill；这不授权读取微信、处理媒体或发送消息。Windows 视频号流程仍可能需要本人在文件传输助手打开精确链接并确认播放。

## 原始发布附件

| 版本 | 文件 | 字节数 | SHA-256 |
| --- | --- | ---: | --- |
| v0.5.0 | [bootstrap-windows.ps1](https://github.com/delu543/jasper-projects/releases/download/weixin-replay-to-mp3/v0.5.0/bootstrap-windows.ps1) | 14,085 | `f7710cb8faff59bd1936270c34020dfacdac5761b7bd1ab555c8e690d7bb9189` |
| v0.5.0 | [install-windows.ps1](https://github.com/delu543/jasper-projects/releases/download/weixin-replay-to-mp3/v0.5.0/install-windows.ps1) | 1,535,235 | `16e898cd18d5fee2de1f65b53dcf0c9fd643aae7ef9fa2e40b57a84817aace4a` |
| v0.5.0 | [weixin-replay-to-mp3-windows-portable-v0.5.0.zip](https://github.com/delu543/jasper-projects/releases/download/weixin-replay-to-mp3/v0.5.0/weixin-replay-to-mp3-windows-portable-v0.5.0.zip) | 88,193,866 | `c362b8766af52b785525ea0819efbf86a89caedbd95816c72a9339f1e8b8fdb4` |
| v0.5.0 | [weixin-replay-to-mp3-windows-portable-v0.5.0.zip.json](https://github.com/delu543/jasper-projects/releases/download/weixin-replay-to-mp3/v0.5.0/weixin-replay-to-mp3-windows-portable-v0.5.0.zip.json) | 296 | `076b379d46af1d3ddf115d7decbd8b4f0bc68e45ecb54755d8b90ac7dfa55717` |
| v0.4.2 | [bootstrap-windows.ps1](https://github.com/delu543/jasper-projects/releases/download/weixin-replay-to-mp3/v0.4.2/bootstrap-windows.ps1) | 14,085 | `7ce81fde46bbfb590ac788aa66af908c8ff0afa42e17460215b7f6d669e88b04` |
| v0.4.2 | [install-windows.ps1](https://github.com/delu543/jasper-projects/releases/download/weixin-replay-to-mp3/v0.4.2/install-windows.ps1) | 1,532,682 | `8e1763d4ef2fabdfe52f191de47520de3ccd3f6f046062ce7076524432757dee` |

历史在线 PowerShell 安装器按原样保存，其中含旧仓库下载地址；新用户使用上面的便携包或[本地源码安装](getting-started.md#weixin-replay-to-mp3)。原始附件保留原哈希，不把改写后的文件冒充原版本。
