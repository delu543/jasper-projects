# 融合与兼容

基座：`project-observatory`，原提交 `35555b15b7a7c63b09e7501998d8daffff269186`，MIT。
融合来源：`project-progress-observatory`，原提交 `ff6f7a7370a48fe4050e9db60e60483ccf19c893`，MIT。
原始版本保留在合集的同名 history 分支；所有者与许可正文保持原样。

采用前者的分层界面、双语、Git/项目结构/GitHub 信号和本机来源边界；吸收后者的用户结果、问题与下一步、任务职责、验证环境、保存版本和旧数据导入语义。没有将两套模型或服务器并列嵌入。

## 状态映射

旧 `unreviewed/planned` → `planned`；`doing` → `active`；`blocked` 保留；`local_verified/real_verified/delivered` → `accepted` 并保留独立 `reviewLevel`。验收仍须通过当前完整版本、环境、证据与干净代码检查。未满足者只保留旧记录，显示待复核。

目标、问题、任务映射、备注、负责人、下一步与长正文均保留。导入只读取当前目标项目下的旧文件，先验证项目身份和字段，再写入新状态。原文件不变；新状态存在、旧数据格式不明或版本冲突时拒绝覆盖。

旧 API 不再提供另一套服务器。`project-progress` 兼容命令直接进入统一 CLI。自建脚本请使用当前 `/api/snapshot`、`/api/context` 和有 revision 租约的写入接口。

原全景面板已有 project.json 可以直接读入；新增字段使用安全空值，旧验收未写验证环境时保持可见但不计代码通过。恢复原版本时可使用保留的旧数据与 Git 历史；不要将示例预览数据导入真实项目。
