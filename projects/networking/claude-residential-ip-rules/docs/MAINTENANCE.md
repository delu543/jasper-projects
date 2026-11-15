# 已有部署：保留现网，更新有证据的缺口

维护源是 `jasper-projects/main` 的 `projects/networking/claude-residential-ip-rules`。根目录其他项目、历史分支和旧独立仓库不参与运行配置。先核对本地 remote/分支/未提交修改，保留 `.private` 和旧回退材料；不要用 `reset --hard`、强制覆盖或清理目录来更新。

## 微软/Outlook 注册域名增量（2026-11-14）

公共 `src/policy.json` 新增 13 个注册、登录和验证码后缀，见 README 完整清单。`signup.live.com` 和 `login.live.com` 由 `live.com` 后缀覆盖。生成器从本地清单的 `roles.claude` / 旧版 `residential` 选择固定节点，不复制维护者的公网 IP、入站地址、节点名或订阅。普通池、地区优先级、ChatGPT opt-in 和国内规则均保持原设置。

- **Mihomo / Verge**：新增后缀规则排在已有内置 Claude 域名之后、`GEOSITE,PRIVATE` 之前；`nameserver-policy` 对应的 `+.<域名>` 使用用户选定的 `proxiedResolvers`，每个解析器附加 `#Claude 固定出口`。保留自定义 DNS；兼容入口默认包含 `https://1.1.1.1/dns-query` 和 Google DoH，两者都经过固定组，不能默默改成 DIRECT。
- **既有 UDP 行为**：仓库的受保护域名一直另有 UDP 拒绝规则，新加入的 13 个域名沿用此行为。因此新生成的 Mihomo 配置增加 13 条固定出口规则、13 条相应 UDP 规则和 13 个 DNS policy；不是只凭配置行数判断成功，也不额外开启全机 UDP 拒绝。相关网页可能改用 TCP，部分通话功能需要实际验证。
- **手机适配**：Shadowrocket / Surge 从同一公共表生成固定域名路线；其原生 DNS 实现和能力边界不变，不能将 Mihomo 的 `nameserver-policy` 字段粘贴进去或宣称已获得相同分域 DNS 保证。仍按 LEAK-PROTECTION、原生导入及设备日志验收。

已有部署先读当前持久 Script、Merge、runtime 和私有清单，备份并记录哈希。只追加缺失的这些域名及 DNS 项，避免与用户已有 `extraClaudeDomains` 重复；保留其他自定义规则、额外 Claude 域名、固定节点、端口、普通池、TUN 和系统/浏览器设置。不要为同步域名直接用整份模板覆盖现网。若有微软域名被用户明确要求 DIRECT 或企业内网路由，先报告冲突与影响，不能静默抹掉既有要求；通用清单会拒绝冲突的 directDomains。

完成差异检查后沿用原备份、语法校验、`force=false` 热加载及冲突保护回滚流程。使用目标机实际普通代理端口新建 `curl https://signup.live.com`、`curl https://login.live.com` 请求，查看它们命中固定组；再从专用入口核对公网出口与该用户已确认的预期值一致。不要仅用强制专用端口请求替代域名规则验收，不打印登录参数、Cookie 或节点凭据，不自动提交账号注册。

旧连接可能维持旧出口，不能为通过检查清空所有连接或重启开发应用。共享域名的其他微软/Outlook/Office 服务也将计入所选固定线路流量。连接和出口一致不证明注册错误码已解除，也不保证注册或验证成功。

## 2026-11-07 补强范围

桌面端 Claude 可能把内置 Code 安装到应用包之外。只匹配 Claude.app 和独立 CLI 会漏掉 `~/Library/Application Support/Claude/claude-code/` 下的可执行文件。`manage.discover_paths()` 现在仅在该目录实际存在时加入其稳定根目录；`universal.py discover/draft` 与旧 `manage.py init` 共用这一发现逻辑。

生成器现有的两条进程规则继续使用同一组路径：拒绝匹配到的 UDP，捕获到的公网请求走唯一 Claude 固定出口。带分隔符的目录前缀覆盖未来版本子目录，不加入整个用户目录、共享 Node/Python 或无关程序。Windows 继续根据实际 executable 发现路径；不创建猜测的目录，也不把 Mac 路径复制过去。客户端日后迁移到其他根目录，仍需重新盘点。

## 执行顺序

1. 使用目标机原有可用网络，读取当前持久化脚本、运行态、进程路径、监听端口和私有清单；记录版本与哈希。只在本地查看，不打印订阅凭据或完整配置。
2. 在本子目录运行 `python scripts/universal.py discover --output .private/discovery-maintenance-1`（目录名每次新建）。已识别为 Verge 时可运行 `python scripts/manage.py inspect`。盘点不操作手机、不更新订阅、不切节点、不启用 TUN。
3. 比较发现路径与当前清单的 `claudePaths`（schema2 和旧 settings 均使用该字段）、持久脚本及运行规则。只添加已核实、授权范围内的遗漏路径；保留现有自定义路径、普通池、ChatGPT opt-in、DNS、地区和固定出口。不要用新模板覆盖已有清单，也不要因更新工具批准新的供应商出口。
4. 按 [通用流程](UNIVERSAL.md) 生成新候选和独立安装计划，核对差异、原生语法及备份。若只是补路径，却改变了节点、DNS、TUN、其他规则或端口，先查清原因，不能作为无关默认升级一起应用。哈希变化说明有并发修改，应重新检查。
5. 获准部署时复用 `manage.py apply` / 对应 Windows 流程的 `force=false` 热加载。不要重启主内核、关代理、清空连接或退出开发客户端来做故障测试。先在隔离实例检验节点失败/监听关闭，热加载连通性可用下方测试。单次测试通过不是所有环境都绝对零中断的承诺。
6. 回读新运行规则，查看真实 Claude/Code 连接链。已建立的连接可能保留原路径，新规则不证明旧会话已迁移；需要客户端重开时等待用户合适时机。共享工具子进程、远端/容器和不遵从代理的程序分别验收。DNS、WebRTC 按 [隐私说明](LEAK-PROTECTION.md) 独立检查。

隔离热加载回归只启动自己的本地测试内核，禁用 TUN/DNS、使用临时端口和回环 echo 服务；不读生产配置，不请求真实节点、不消耗套餐：

```sh
python tests/integration_hot_reload.py --mihomo /path/to/mihomo
```

它验证两条持续 CONNECT 流跨 `force=false` 加载仍能收发且连接 ID 不变；不证明任意客户端、系统 DNS 或全进程树隔离。普通/固定路线互不备用另用 `tests/integration.py --snapshots` 检查。

## 恢复与独立过滤器

应用异常时使用对应安装计划的 `manage.py rollback --plan <安装计划目录>`（Windows按其文档），回读原脚本/运行态和联网。文件有后续修改时工具会拒绝覆盖，应先核对冲突，不能强行还原；客户端/浏览器设置各用自己的回退工具。备份与回执留在本地。

本工具没有 LuLu/Little Snitch 运行依赖，不安装、启用或恢复它们。已有其他过滤器的设备先查状态与冲突，不能未经授权关闭安全软件。若用户明确卸载，使用其正式流程并保留恢复信息；系统要求重启时，按用户的联网约束另择时间，不把“已停用”写成“所有系统实体已清除”。

去掉独立过滤器不会把 Clash 分流变成系统防火墙：固定节点失败时，进入固定组/专用入口的请求失败、不换节点；Clash 退出后，仅遵从显式代理的程序因本机端口不可达而失败。任意子进程或绕过代理的流量仍不在这个保证内。节点质量、账户审核与这些配置能力分开报告。
