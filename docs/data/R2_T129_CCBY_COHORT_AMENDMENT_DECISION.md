# T129 CC-BY 候选 cohort：范围修订决策包

**状态：** `AWAITING_SCOPE_OWNER_DECISION`
**证据等级：** `DEVELOPMENT_OBSERVATION`；不是 target 准入、模型运行或投稿授权。
**触发证据：** T132 已校验 PXD017052 的完整 12 个出版方附件，并将 9 个
结果/原始单位显式连接到三个 SPION 与重复号；该路线为 CC-BY 4.0、单实验室。

## 需要决定的唯一范围变化

现行 T129 冻结为 **CC0-only** cohort。批准本修订只会建立一个与 CC0 队列完全
隔离的 `CCBY_DEVELOPMENT_CANDIDATE` 名称空间；不会把 CC-BY 数据重新标为 CC0，
不会将其放入公共 CC0 release，也不会授权模型或结果稿。

| 选项 | 决定 | 立即效果 | 仍然禁止 |
| --- | --- | --- | --- |
| A | 保持 CC0-only | PXD017052 仅保留为审计线索，不建立候选 cohort | 合并、模型、T123/T124、实证投稿 |
| B | 建立隔离 CC-BY 候选 cohort | 允许登记 T132 的单位映射、材料属性与来源受限的原始附件；仅用于寻找第二独立来源与冻结共同 endpoint | 与 CC0 混合、公共复制原始输入、模型拟合、ablation、OOD、独立验证、实证结论 |

## 如果批准 B，固定的不变量

1. `license_id=CC-BY-4.0`、`cohort=CCBY_DEVELOPMENT_CANDIDATE`，且每个
   派生资产保留 T131/T132 收据哈希。
2. PXD017052 仍是单实验室；它不是 internal held-out、external validation 或
   independent evaluation。
3. 仅在第二个独立实验室也有显式单位级材料映射、相同冻结蛋白 endpoint、明确
   生物单位与分析计划修订后，才可重新评估 T129/T121。
4. 任何缺失条件必须生成 `NOT_ADMITTED` receipt；文件顺序、图像、名称或叙述
   不能补全单位映射。
5. 在获得范围所有者的明确批准前，本文件不改变现行 CC0-only policy。

## 已知的第二来源路线

RSC `C9NR08186K`（University of Helsinki，CC-BY 3.0）可能包含可复核补充
工作簿，但当前出版方正常 HTTPS 路径在复查时未提供可获取文件（一个 404，后续
请求 429）。未尝试绕过验证。即便以后可取得，其端点和单位定义仍需独立核验，
不能预先视为第二实验室或共同 endpoint。

## 批准记录模板

仅在范围所有者明确选择 B 后写入：

```text
scope_owner_decision: B
approved_at: <RFC3339 timestamp>
scope_owner: <name or role>
reason: <why isolated CC-BY development cohort is allowed>
```
