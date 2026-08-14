# R4 T249：四来源论文数据共同 target 状态

状态：`FOUR_LABORATORY_COMMON_TARGET_VERIFIED_RESTRICTED_DEVELOPMENT`

T249 在不获取新湿实验的前提下，把已公开论文及其补充表转换为可复核的第四来源。新增来源是 PMC6592156 / PXD007648：论文报告 60 nm citrate-coated silver nanoparticle 在人血浆中的蛋白冠，补充表提供 899 个蛋白、30 个 pH/temperature measurement batches 和 3 个技术重复。原始补充包、补充表、规范化 source-cell map、论文和审计哈希均被保留。

## 冻结结果

| 指标 | T249 结果 |
|---|---:|
| source packages | 4 |
| laboratory/source anchors | 4 |
| exact common canonical accessions | 7 |
| common row-traceable observations | 783 |
| raw source-map cells | 15,971 |
| positive rank-eligible cells | 10,852 |
| measurement batches | Edinburgh 49；Dalian 6；UCD 30；PMC6592156 30 |

共同 target 为：`P04004`, `P05556`, `P06396`, `P07996`, `P26038`, `P60174`, `Q9HDC9`。选择规则是四个 source maps 的严格正值交集，未使用模型性能、效应大小或外层测试表现。

## 统计与解释边界

- abundance 不跨来源合并；只在 source-defined batch 内转 rank percentile。
- blank、zero、NA 保留并排除，不做插补。
- PMC6592156 的 pH/temperature 条件与技术重复不是 30 个独立生物样本。
- Dalian 仍是 pooled/unspecified plasma；Edinburgh 当前 map 不编码 donor ID；UCD 技术重复不计为独立单位。
- 因此 T249 提升了来源兼容性和论文数据可复核性，但不等于四个独立生物学队列，也不关闭 lockbox、无作者复现、外部采用、DOI 或 `scientific_submission_ready` 门禁。

## 复核入口

- 协议：`docs/data/R4_T249_FOUR_LAB_COMMON_TARGET_PROTOCOL.json`
- registry：`docs/data/R4_T249_FOUR_LAB_COMMON_TARGET_REGISTRY.json`
- 第四来源 registry：`docs/data/R4_T249_PMC6592156_SOURCE_REGISTRY.json`
- 审计代码：`src/biointerfaceos/r4_t249_four_lab_common_target.py`
- source audit：`reports/review_round_4/pmc6592156_t249_source_audit/v1.0.0/`
- ledger/report/receipt：`reports/review_round_4/four_lab_common_target/v1.0.0/`

复核命令：

```text
python -m biointerfaceos data verify-r4-t249-four-lab-common-target --strict
```

当前输出：`sources=4 laboratories=4 common_targets=7 common_rows=783 scientific_submission_ready=false`。
