# R4 T192 三实验室可再分发共同 target 状态

状态：`THREE_INDEPENDENT_LABORATORY_COMMON_TARGET_VERIFIED_RESTRICTED_DEVELOPMENT`

T192 将三个不同来源的公开数据重新绑定为一条可再分发、行级可追溯的开发共同 target 链：

| 来源 | 实验室锚点 | 许可 | 严格正值 target | common rows | batches |
|---|---|---|---:|---:|---:|
| Edinburgh DataShare DS7545 | University of Edinburgh | CC-BY-4.0 | 23 | 404 | 49 |
| PRIDE PXD060795 | Dalian University of Technology | CC0 | 22 | 52 | 6 |
| PRIDE PXD064962 | University College Dublin / Conway Institute | CC0 | 15 | 353 | 30 |

三方严格交集为 9 个冻结 accession：`P04004`, `P04264`, `P05556`, `P06396`, `P07996`, `P26038`, `P60174`, `Q04695`, `Q9HDC9`。共同 ledger 共 809 行，输入 source-map 共 2,486 行，其中 1,495 行满足严格正值 rank eligibility。

每一行保留 source id、实验室锚点、原始资产、worksheet/column、原始行号、source coordinate、source identifier、measurement batch 和原始数值。不同研究的 abundance scale 不合并；跨源比较只允许使用各源内 batch rank。

这条链比旧 T178 更接近目标要求，因为三个来源均有明确的 CC0 或 CC-BY-4.0 再分发边界，且不再把 Michigan State pooled multi-core technical benchmark 作为生物学独立实验室的替代。但它仍是 development evidence：Dalian 的材料是 pooled/unspecified plasma，Edinburgh 当前 map 未编码 donor ID，UCD 的技术重复不是独立单位。因此 T192 不能单独关闭 primary OOD、lockbox、无作者复现或 `scientific_submission_ready` 门禁。

机器入口：

- 协议：`docs/data/R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_PROTOCOL.json`
- 冻结 registry：`docs/data/R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_REGISTRY.json`
- 审计代码：`src/biointerfaceos/r4_t192_three_lab_common_target.py`
- ledger/report/receipt：`reports/review_round_4/three_lab_redistributable_common_target/v1.0.0/`

官方来源入口：Edinburgh DataShare DS7545、PRIDE PXD060795、PRIDE PXD064962。所有外部 evaluator、无作者复现、adoption 和 DOI 声明继续保持 false。
