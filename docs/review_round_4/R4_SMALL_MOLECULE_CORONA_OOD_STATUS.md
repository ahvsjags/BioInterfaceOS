# R4 PMC11544298 公开同谱系 OOD 执行状态

状态：`AUTHOR_RUN_PUBLIC_OOD_EXPLORATORY`。分析严格使用 R3 已冻结的 2,724 个开发观测、R3 sequence feature table 和 R4 先冻结的协议；没有把 PMC11544298 追加到 R3 训练集，也没有使用 R4 结果修改模型或 target。

## 执行结果

| 项目 | 结果 |
|---|---:|
| R3 开发观测 | 2,724 |
| R4 外部观测 | 7,075 |
| R4 可评估批次 | 134 |
| R4 共享 canonical proteins（可评估） | 94 |
| sequence ridge full：批次等权 Spearman | 0.400190 |
| sequence ridge full：95% cluster bootstrap CI | 0.374161–0.422958 |
| composition-only：批次等权 Spearman | 0.404864 |
| full − composition 配对差 | −0.004674 |
| 配对差 95% bootstrap CI | −0.009887–0.000490 |
| 批内置换负对照上尾 p | 0.003891 |

结果逐批计算，置信区间以测量批次为 cluster；负对照在 R3 开发批次内置换 target，并固定观察到的 nested-selected alpha。没有合并不同研究的 raw abundance scale。

## 解释边界

- 这是可审计的真实公开补充数据上的作者运行 OOD，证明了该冻结执行管线可以在新的公开数据上运行，并提供了可复核的正结果与负消融结果。
- PMC11544298 与既有 R3 Michigan State 来源属于同一实验室谱系，因此新增独立实验室锚点为 0。
- `independent_validation=false`、`external_scientific_reproduction=false`、`scientific_submission_ready=false` 必须保持不变。
- full 模型没有优于 composition-only；论文若报告它，必须同时报告这个方向相反的配对消融，不能只挑选 full 模型。

## 可复核产物

- 协议：`docs/data/R4_T159_SMALL_MOLECULE_CORONA_OOD_PROTOCOL.json`
- 执行回执与报告：`reports/review_round_4/small_molecule_corona_ood/v1.0.0/`
- 执行模块：`src/biointerfaceos/r4_small_molecule_corona_ood.py`
- 测试：`tests/review_round_4/test_r4_small_molecule_corona_ood.py`

本结果不关闭强 Q1 门禁。下一步仍需非作者 evaluator 的保护式 lockbox、无作者参与团队的原始输入科学复现，以及可验证的公开 release/DOI/独立安装/外部采用链条。
