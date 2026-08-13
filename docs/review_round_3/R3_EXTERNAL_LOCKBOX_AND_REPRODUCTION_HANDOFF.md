# R3 独立 Lockbox 与科学复现交接包

**当前状态：`PREPARED_NOT_EXECUTED`**

此文件把已经真实运行的 R3 数据工作流交给第三方，但不把作者团队的重跑称为独立验证。第三方必须是非作者、无监督的 evaluator 或 reproduction team；实际身份、利益冲突和签名由项目负责人核验。

## 不可变输入

| 内容 | 定位 | 作用 |
|---|---|---|
| R3 主协议 | `docs/data/R3_T151_ANALYSIS_PROTOCOL.json` | 三实验室开发/外留设计 |
| R3 开发目标账本 | `data/raw/r3_common_rank_target/R3_common_rank_target_ledger.csv` | 2,724 个开发观测 |
| R3 序列特征 | `data/raw/r3_uniprot_sequence_features/uniprot_sequence_features/R3_uniprot_sequence_features.csv` | 不含蛋白 identity 或来源标签的特征 |
| 银来源审计 | `docs/data/R3_T154_SILVER_PLASMA_SOURCE_REGISTRY.json` | 公开全文补充数据的字节、许可与源单元契约 |
| R3 银 OOD 协议 | `docs/data/R3_T155_SILVER_EXTERNAL_OOD_PROTOCOL.json` | 不参与训练的公共外部来源测试 |
| 既有作者运行结果 | `reports/review_round_3/` | 只用于复核，不得作为第三方预期结果的调参依据 |

## A. 独立 evaluator 的一次性 lockbox

1. 项目负责人先冻结一个**未被作者查看的**新实验室数据包；不可使用已公开的 R3 四个来源作为 lockbox。
2. evaluator 在独立环境中验证 source manifest、许可、行级坐标、protein mapping 和共同 target，然后只向作者披露汇总 receipt。
3. 作者在 evaluator 获取保护 target 后不得更改特征、模型、超参数、阈值、脚本或随机种子。
4. evaluator 使用冻结的 R3 协议运行 `SEQUENCE_RIDGE_FULL`、`SEQUENCE_RIDGE_COMPOSITION_ONLY` 和 constant baseline；报告每个源定义批次的 Spearman、MAE、RMSE、cluster bootstrap interval、负对照与配对消融。
5. receipt 至少包含输入哈希、代码 commit、环境 lockfile 哈希、独立单位数、所有预声明模型的汇总指标、偏离清单、签名指纹；不得导出受保护逐行 target。

成功门槛不是单一 p 值：外部目标必须预先兼容，所有预声明模型均要报告，且 evaluator receipt 必须能由项目负责人验证而无需暴露 lockbox 原始值。

## B. 无作者科学复现

1. 外部团队在新的 checkout 和新环境中，从论文/PRIDE/Europe PMC 公开原始入口重新获取或独立地验证 R3 所用文件字节。
2. 按顺序运行：

   ```powershell
   biointerfaceos data audit-r3-silver-plasma-source --assets-root data/raw/r3_candidate_pmc6592156 --strict
   biointerfaceos data evaluate-r3-common-rank-models --output-data-root data/raw --feature-root data/raw/r3_uniprot_sequence_features --strict
   biointerfaceos data evaluate-r3-silver-external-ood --output-data-root data/raw --feature-root data/raw/r3_uniprot_sequence_features --silver-assets-root data/raw/r3_candidate_pmc6592156 --strict
   ```

   输出目录已存在时，工作流会拒绝覆盖；复现者应使用全新 checkout，而不是删除或改写作者结果。

3. 外部团队提交：重获/验证的数据路径和 SHA-256、软件版本与 `uv.lock` 哈希、完整命令、测试结果、结果哈希比较、所有偏离（即使没有偏离也要显式写明）、及其作者贡献与利益冲突声明。
4. 编辑复审者需检查：Oklahoma 的负 OOD 结果是否仍被保留、银来源是否仍标为 author-run public OOD、任何新 lockbox 是否真正对作者隐藏、以及结论是否仍限制在 source-local ranking。

## 仍然禁止的做法

- 使用作者本人或其受控账号签发 independent-evaluator / external-reproduction receipt；
- 将公开银来源称作 lockbox；
- 因 Oklahoma 外留表现不佳而剔除该来源；
- 将来源特异的 LFQ、spectral count 或原始强度跨研究拼接；
- 以软件重跑替代科学复现；
- 在收到真实第三方 receipt 前将 `scientific_submission_ready` 改为 `true`。
