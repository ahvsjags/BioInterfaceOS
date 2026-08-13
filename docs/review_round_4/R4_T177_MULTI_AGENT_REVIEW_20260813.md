# BioInterfaceOS T177 多智能体编辑复评（2026-08-13）

## 编辑结论

**Decision：Major Revision / 不建议以强 Q1 生物学验证论文投稿。**

T176/T177 解决了两项此前真实缺口：一个公开全文来源的 dataset-level license 已解析并逐字节审计；一条独立于当前 R3 anchor 的 technical source 已按冻结规则形成 source-cell map，并完成了真实模型、nested selection、消融、batch-cluster bootstrap 和 negative control 执行。但该来源只有一个 pooled biological unit，且 T177 的 full model 外部批次均值 Spearman 仅为 `0.0240`，negative-control 上尾 `p=0.3268`。因此它不能被包装成稳健的外部生物学发现。

按强 Q1 的硬门槛，本轮综合为 **30/100**，`scientific_submission_ready=false`。分数不是把缺失的第三方事实用作者运行结果补齐：protected lockbox、无作者端到端科学复现和外部采用收据仍然没有。

## 评审材料与可核验事实

- T176 source registry：`docs/data/R4_T176_PMC13106918_TECHNICAL_SOURCE_REGISTRY.json`
- T176 source audit：`reports/review_round_4/pmc13106918_source_audit/v1.0.0/`
- T177 protocol：`docs/data/R4_T177_PMC13106918_TECHNICAL_OOD_PROTOCOL.json`
- T177 execution：`reports/review_round_4/pmc13106918_technical_ood/v1.0.0/`
- T177 implementation：`src/biointerfaceos/r4_pmc13106918_technical_ood.py`
- T177 tests：`tests/review_round_4/test_r4_pmc13106918_source_audit.py`、`tests/review_round_4/test_r4_pmc13106918_technical_ood.py`

## 五个独立角色

### 1. EIC：计算生物学方法/资源期刊编辑

**判断：Major Revision；强 Q1 生物学发现稿不送审或早期拒稿风险高。**

新贡献是可审计的数据入口和 fail-closed 分析链，而不是一个已经通过独立生物学验证的科学结论。T177 将“没有执行结果”推进到“有执行结果”，但结果接近零相关，不能承担广泛泛化或机制价值。若改投方法/软件、可复核 benchmark 或数据资源方向，论文可以有清晰定位；若声称跨实验室预测、材料设计 utility 或生物学机制，证据不足。

**EIC 评分：**方法/软件定位 `68/100`；强 Q1 生物学发现定位 `30/100`；投稿建议为 `Major Revision`。

### 2. 统计方法审稿人

**优点：**R3 development population 冻结；T177 使用 nested alpha selection；外部 estimand 是批次内正值 LFQ 的 midrank percentile；full/composition-only 是成对消融；不确定性按 measurement batch cluster bootstrap；negative control 在 R3 measurement batch 内置换 target。

**主要问题：**外部有效 biological n 仍为 `1`；16 个 technical batches 不是 16 个独立生物学批次；full model 的 `0.0240` 区间跨零；negative-control `p=0.3268` 不支持正向预测证据。T177 的统计执行可以复核，但不能把执行完成等同于效应成立。

**统计评分：**设计 `84/100`；执行与有效样本 `62/100`；外部模型证据 `57/100`。

### 3. 领域审稿人：纳米-蛋白冠层/蛋白质组学

**判断：**RCSI/DCU 的 pooled human plasma、五种 digestion protocol 和技术重复对于 sample-preparation robustness 有资源价值；但它不是 donor-level cross-laboratory biological replication。R3 的 rank-percentile target 也不等于总冠层丰度、材料效应或机制 estimand。

**主要要求：**正文必须区分 protein-group compatibility、technical robustness、donor-level biological validation 和 independent evaluation；不能以八名 pooled donors 写成 `n=8` 的外部有效样本；需要把 T177 的接近零相关结果作为结果而不是隐藏在补充材料。

**领域评分：**数据/问题相关性 `64/100`；生物学外部有效性 `24/100`；机制贡献 `20/100`。

### 4. 跨学科/开放科学审稿人

**判断：**source registry、ZIP-to-extraction byte equality、cell ledger、protocol hash、receipt 和 CLI 重跑路径是强项；但公共 handoff 仍只是请求外部团队参与，不是外部采用证据。需要第三方 clean checkout、环境、命令、输出 hash、偏差和失败记录，才能把可复现性从“工程可复现”推进到“科学复现”。

**开放科学评分：**代码/资产审计 `78/100`；独立复现 `0/100`；外部采用 `25/100`。

### 5. Devil’s Advocate：最强反驳

**核心反驳：**论文可能把“一个成功下载并审计的公开数据包”和“外部验证”混为一谈；又可能把 20 个技术列、16 个达标批次和 8 名 pooled donors 叙述成大样本跨实验室证据。T177 的 full model 相关性接近零，且 permutation control 没有显著分离，这使“序列特征具有可迁移预测力”的核心叙述无法成立。

**致命问题：**没有非作者 protected lockbox，没有无作者端到端复现，没有外部用户采用；因此不能通过修改权重或增加作者运行来把所有模块抬到 `90+`。如果稿件仍使用 `independently validated`、`externally replicated`、`broadly generalizes` 或 `clinical/material-design utility`，编辑建议拒稿或要求彻底重写 claim boundary。

**Devil’s Advocate 评分：**核心主张可信度 `23/100`；反驳后强 Q1 可接受性 `18/100`。

## 综合模块评分

| 模块 | T176/T177 后评分 | 证据依据 | 到 90+ 仍缺什么 |
|---|---:|---|---|
| 数据兼容性与样本基础 | 64 | 53 个唯一 source target、36 个正值可排序 target、16 个合格 technical batches，全部可追溯 | 至少 3 个独立实验室、donor/cluster-level biological n、独立 primary OOD cohort |
| 统计分析设计 | 84 | estimand、nested selection、cluster bootstrap、missingness 和 negative control 均冻结 | 非作者按协议执行并提供结果/偏差 receipt |
| 统计执行与有效样本 | 62 | T177 有 2,724 development observations、418 external observations、16 batches 的真实执行 | 非作者执行、独立 biological units、预注册 endpoint receipt |
| 模型、消融与 OOD 证据 | 57 | 3 模型、full/composition ablation、CI、negative control 已执行 | 多实验室/多 donor held-out 稳健效应、预设成功标准、独立重复 |
| 独立评估 / protected lockbox | 4 | 只有结构预检与接口 | 非作者 evaluator、作者不可见输入、签名 aggregate receipt |
| 外部科学复现 | 0 | 公共 handoff 与 Issue 已存在 | 非作者 clean checkout、重获数据、日志和输出 hash |
| 外部用户采用 | 25 | handoff、版本 tag、安装路径已公开 | 至少两名不同机构非作者完成并提交可核验使用记录 |

**严格强 Q1 综合：30/100；`scientific_submission_ready=false`。**最低项不是通过加权平均可以抵消的硬门槛。

## 本轮必须执行的改进目标

1. 将 T176/T177 结果纳入正文和补充材料，明确 `technical OOD`、`biological unit=1`、`author-run` 与负结果。
2. 保持 T177 full-model 结果为 `0.0240` 和 negative-control `p=0.3268`，不进行结果选择或包装成正向发现。
3. 获取非作者 protected lockbox evaluator receipt；无该 receipt，不得填写 independent validation。
4. 获取非作者 clean-checkout scientific reproduction receipt；记录环境、命令、输入/输出哈希和偏差。
5. 获取至少两名不同机构非作者的实际使用/adoption receipt；GitHub Issue、下载、star 或作者邀请不能替代它们。
6. 取得版本 DOI 后，重新运行五角色复评；只有所有硬门槛都有真实 artifact，才重新计算是否达到 `90+`，在此之前不得打开 `scientific_submission_ready`。
