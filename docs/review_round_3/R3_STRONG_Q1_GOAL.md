# R3 强 Q1 目标与 KAUST 执行契约

状态：`IN_PROGRESS`。本文件是 `/ibex/user/xup0a/BioInterfaceOS-r3-real-data` 的当前任务目标；它不把已完成的作者运行结果误写为独立科学验证。

## 最终目标

将 BioInterfaceOS 从 protocol/software-only 状态推进为可稳投强 Q1 的计算生物学研究。提交就绪的强门禁只有在下列每一项均有可审计证据时才能通过：

1. 可再分发、行级可追溯、至少三个独立实验室均覆盖的共同真实 target；
2. 预先冻结的 study-held-out、nested-selection、cluster-aware 统计执行，以及真实模型、配对消融、负对照、OOD 和不确定性结果；
3. 非作者独立 evaluator 在作者不可访问的保护数据上完成一次性 lockbox，并提供可验证 receipt；
4. 无作者团队从原始公开输入开始完成外部科学复现，并提供数据重获、环境、命令、偏离和结果 receipt；
5. 公开仓库、版本 DOI、独立安装、外部用户与采用证据；
6. 新一轮多智能体编辑复审中，数据兼容性、统计设计、统计执行、模型/OOD、独立评估、外部复现、用户采用和强 Q1 综合成熟度均至少 90/100。

## 当前已证实的 R3 基线

- 三个 CC-BY 人血浆来源形成 100 个共同 UniProt 蛋白（99 个排名合格），2,724 个观测、47 个测量批次和三个实验室锚点；主账本为 `data/raw/r3_common_rank_target/R3_common_rank_target_ledger.csv`。
- 冻结的协议、三实验室 outer evaluation、negative control 和 paired ablation 已在 `reports/review_round_3/` 保存。
- 一个与训练和超参数选择隔离的 CC-BY 银纳米颗粒人血浆来源提供 953 个观测、30 个测量批次的作者运行外部 OOD；该结果仍是 `EXPLORATORY`，不是 lockbox 或复现。
- 所有失败、非人源、无可再分发授权、或批次/相交覆盖不足的全文来源必须继续保留于 `docs/data/R3_T153_FURTHER_FULLTEXT_SCREEN.json`。

## 仍未满足、不得绕过的门槛

| 门槛 | 当前状态 | 关闭证据 |
|---|---|---|
| 独立 lockbox | 未开始 | 非作者签名的 aggregate-only receipt；作者未访问保护值的审计记录 |
| 外部科学复现 | 未开始 | 无作者团队的独立 checkout、原始入口重获、命令/环境/偏离/结果 receipt |
| 公开版本与 DOI | 未开始 | 已发布的不可变版本、DOI、release manifest 和校验和 |
| 外部采用 | 未开始 | 非作者安装日志、issue/PR、引用或真实用户报告 |
| 强 Q1 编辑复审 | 未开始 | 新审稿团逐项评分均 >=90，且 `scientific_submission_ready=true` 有全部门禁支持 |

## KAUST 服务器执行顺序

```bash
cd /ibex/user/xup0a/BioInterfaceOS-r3-real-data
uv sync --locked --all-groups
uv run pytest tests/review_round_3 -q
uv run python -c "from pathlib import Path; from biointerfaceos.r3_model_evaluation import R3ModelEvaluationWorkflow; from biointerfaceos.r3_silver_external_ood import R3SilverExternalOODWorkflow; r=Path.cwd(); print(R3ModelEvaluationWorkflow(r, r/'data/raw', r/'data/raw/r3_uniprot_sequence_features').verify()); print(R3SilverExternalOODWorkflow(r, r/'data/raw', r/'data/raw/r3_uniprot_sequence_features', r/'data/raw/r3_candidate_pmc6592156').verify())"
```

这些命令只验证已有的作者运行 R3 证据。它们不能产生 independent evaluator、external scientific reproduction、DOI 或用户采用证据。
