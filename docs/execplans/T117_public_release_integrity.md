# T117 — 公开发布合规、文档与清单修复

## 目的

把当前 public package 从“可运行但来源和许可不完整”的状态修复为可审计的软件发布物。T117 仅解决发布合规、来源可追踪性和文档准确性；它不把 fixture 或 software replay 升级为实证研究结果。

## 范围与边界

- 清点根目录、源代码、测试 fixture、生成文件、图件、文稿、数据和容器文件；
- 为每个可发布资产明确许可、作者权利和 redistributability；
- 对无法合法重发的资产执行移除、替换为自制可重建资产，或 controlled-access/不可发布标记；
- 修复 README、引用信息、安装与复现入口，使其仅承诺已验证的软件 replay；
- 历史 release、receipt 和 fixture 不重写；其证据语义继续受 T116 隔离。

## 实施步骤

1. 建立 machine-readable asset/license registry，记录路径、类别、来源、许可证、权利状态、是否可公开发布及替代策略；
2. 为代码补充明确根许可证，为可引用软件写 `CITATION.cff`，并为第三方依赖和 bundled material 制作 notices/SBOM 链接；
3. 增加 strict public-release audit：缺失许可、路径失效、未登记资产、错误 redistribution 声明或 README 过度承诺均必须失败；
4. 重写 README/release inventory，区分 source、fixture、generated output、software replay、受控/不可发布材料和未验证科学主张；
5. 对修复后的 release 作 clean-tree audit，并将清单、审计 receipt 和负面发现写入报告。

## 验收

- 根 `LICENSE`、`CITATION.cff`、asset/license registry、release inventory 和 strict audit 都存在并互相一致；
- README 中的路径、命令和声明可解析，未将 fixture/replay 描述为 empirical validation；
- 每一份代码、文本、图件和数据资产都有明确的公开、受控或排除决策；
- 检查失败时必须指明具体路径和缺失字段，不能以默认“可发布”放行。

## 失败处理

未能确定权利或来源的资产从 public package 排除，并将其对下游可重建性的影响明确记为 blocker；不以猜测性许可证或外部链接替代证据。
