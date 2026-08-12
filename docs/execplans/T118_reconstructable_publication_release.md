# T118 — 可重建发布表、图与运行 receipt

## 目的

建立一个干净环境可验证的 R2 software-replay release：它只打包经 T117 允许的源代码、文档、配置、R2 图件规范和可重建协议图，不重新发布历史 fixture/data/manuscript bundle，也不将软件重放描述为科学复现。

## 实施

1. 为 R2 publication package 生成 manifest、source hashes、SBOM、环境锁定信息和容器运行说明；
2. 新增 `reproduce release --strict`：从版本化 source/spec 重建 R2 protocol figures，检查 hashes、field maps、600-dpi outputs、许可证分类和 clean-room test receipt；
3. 任何缺失 source-data card、未登记依赖、未固定运行命令或旧 fixture/public bundle 进入新 package 都必须失败；
4. 发布生成/复现的 JUnit-style receipt，明确 `software_replay=true`、`scientific_reproduction=false` 与 `scientific_submission_ready=false`；
5. 对本机独立 worktree 或 clean container 执行重放，保留命令、commit 和完整 hash 证据。

## 验收

- R2 release 只含 T117 `PUBLIC` 文件与明确允许的 protocol artifacts；
- 所有 release outputs 可从 source/spec 重建并逐文件校验 hash；
- SBOM、环境、容器命令、运行 receipt 与 release manifest 一致；
- 新 command 遇到缺失、变更或历史 fixture bundle 时 fail closed；
- release 标签清楚说明这是 software replay，不是 independent scientific reproduction。

## 失败处理

若某图表不能从允许的 source/spec 重建，则其不进入 R2 package；相关论文只能维持 protocol/software scope，直至 T120–T124 产生合法的真实数据和独立证据。
