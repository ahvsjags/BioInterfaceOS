# R4 强 Q1 改进目标与验收门槛

**目标状态：`IN_PROGRESS`**  
**目标：** 在不伪造数据、第三方身份、用户采用或独立结果的前提下，把 BioInterfaceOS 从“可审计方法/内部 benchmark”推进到“可稳投强 Q1 方法论文”的证据状态。仅当所有硬门槛均有可核验 artifact 时，才允许把 `scientific_submission_ready` 改为 `true`。

## 1. 不可妥协的总验收条件

强 Q1 目标不是把缺失证据用作者端重跑补齐，而是同时满足以下条件：

1. 至少两个真正独立于开发 lineage 的外部来源；每个来源必须有可重获原始输入、明确许可、accession、SHA-256、样本设计、target mapping 和 batch 元数据。
2. 至少一个非作者团队完成预注册的端到端科学复现；最好由两个没有共同作者或项目控制关系的机构分别完成 lockbox/reproduction。
3. 至少一次真正的 protected-data lockbox：作者在评估期间不能读取 held-out target、逐行结果或中间日志；只能收到 aggregate receipt。
4. primary endpoint、容差、有效独立单位、missingness、cluster bootstrap、置换检验、多重比较和失败规则在数据解封前冻结。
5. 外部结果必须报告完整的点估计、95% CI、batch/target/lineage/institution 层级有效样本、失败案例和负结果；不能只挑选成功子集。
6. 至少两名非作者用户在干净环境中完成安装并运行独立任务，留下可核验日志、版本/容器信息、输出 hash 和局限性反馈；“下载”不计为采用。
7. 标题、摘要、结果和结论逐句通过 claim-to-evidence 审计；没有 receipt 的 independent/external/generalizable/clinical 表述全部删除。

## 2. 分阶段任务

### Gate A — 数据与 estimand 冻结

**交付物：** `R4_EXTERNAL_DATA_FREEZE_MANIFEST.json`、来源许可表、target/batch/lineage 映射、预注册统计协议和不可变 SHA manifest。

**退出标准：**

- R3 development、same-lineage R4 OOD、Dalian exploratory sensitivity 和真正 external holdout 四者分离；
- 不把同一 pooled material 的 technical replicates 当作独立 donor；
- primary external endpoint 的最低批次数和最低 target 覆盖率在执行前固定；
- 候选来源不满足许可或样本级定量要求时，保持 `HOLD/REJECTED`，不得为了凑数量纳入。

### Gate B — 统计、模型与有效样本闭环

**交付物：** primary endpoint receipt、effective-n report、cluster-aware bootstrap、预设 permutation、full/composition-only/simple-rank/constant baselines、paired ablation、失败案例清单。

**退出标准：**

- batch、target、lineage、institution 都有独立单位计数；
- 所有模型共享冻结 outer split，禁止根据 external holdout 调参；
- sequence/full 模型只有在预设 CI 和容差下优于 simple/composition baseline 才能声称增量价值；
- 若增量为零或为负，正文明确写成负结果，不改写为机制确认。

### Gate C — 非作者 lockbox

**交付物：** evaluator identity/COI declaration、预注册协议 hash、输入文件 SHA-256、代码 commit、container digest、依赖 lockfile hash、stdout/stderr、原始输出 hash、aggregate receipt、失败记录和签名时间戳。

**退出标准：**

- evaluator 无共同作者、无项目控制关系，并独立保存 protected input；
- 作者无法访问逐行 target、预测、中间调参或失败样本；
- receipt 能由编辑或审稿人独立验证，但不泄露受保护数据；
- 负结果和失败运行也进入 receipt，不能只提交成功运行。

### Gate D — 非作者科学复现

**交付物：**独立 checkout、原始 accession 重获日志、环境安装日志、完整命令、测试结果、核心指标/CI、输出 hash、偏差解释、贡献与 COI 声明以及带 DOI 或不可变时间戳的公开存档。

**退出标准：**

- 至少一个团队在没有作者现场调参或手工修复的情况下完成端到端运行；
- 复现核心 Spearman、CI、missingness 处理和主要图表；
- 偏差容差事先固定，超出容差必须作为失败报告而不是事后修改协议。

### Gate E — 外部用户与编辑复评

**交付物：**两份非作者独立安装/使用报告、issue/PR 或独立项目记录、版本/容器与输出 hash、局限性反馈、最终多智能体编辑复评和 claim audit。

**退出标准：**

- 两名非作者用户在不同环境完成不同任务；
- 报告真实失败和修复，不把作者自测包装为采用；
- 重新评分时：数据兼容性、统计设计、统计执行、模型/OOD、lockbox、外部复现、用户采用各模块均 ≥90，且严格综合门槛 ≥90；
- `scientific_submission_ready=true` 只能由全部 receipts 和复评报告共同支持。

## 3. 不能由本项目内部自动完成的门槛

公开全文/PRIDE 数据可以补足来源、许可、映射、作者端执行和 exploratory OOD，但不能自动产生：

- 非作者 evaluator；
- 作者不可访问的 protected lockbox；
- 非作者科学复现；
- 真实外部用户采用。

这些是外部协调依赖。项目内部可以提前准备协议、容器、测试、receipt schema 和 handoff，但在真实第三方 artifact 到达前，目标必须保持 `IN_PROGRESS`，不允许用合成 receipt 或作者控制账户闭合门槛。

## 4. 当前可执行命令与状态检查

```bash
cd /ibex/user/xup0a/BioInterfaceOS-r3-real-data
uv sync --locked --all-groups
uv run pytest tests/review_round_3 tests/review_round_4 -q
git status --short
```

以上命令只能证明代码、测试和当前公开数据链可运行，不能证明 Gate C–E 已完成。每个外部 gate 必须另外提交对应 receipt 和不可变 hash。

## 5. 终止规则

如果在预设期限内无法获得非作者 lockbox 和复现团队，稿件必须转为“方法/软件与可审计 benchmark，外部结果为 exploratory”的诚实定位；不得为了达到 90 分而改写权重、删除负结果、扩大 technical replicate 的独立性或把作者端运行称为第三方验证。

