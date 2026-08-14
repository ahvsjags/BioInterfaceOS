# R4 T203：bootstrap seed 审计对账

日期：2026-08-14。

T203 OOD receipt 的 protocol SHA-256 为 916acb43e67fa0430630f2120c59bd4338d8f3c24f6efeea53f5d598757c9d7c，对应已执行的 protocol v1.0.0。该版本的 uncertainty base seed 是 20260824。

实现中的 paired composition ablation 使用确定性派生规则：

paired_ablation_seed = uncertainty.random_seed + 701 = 20260824 + 701 = 20261525

因此 report 中的 20261525 不是未记录的独立随机选择，而是由已冻结的 base seed 和代码中的固定 offset 派生。T203 的数值 receipt 保持不变；本说明补齐审计解释，不修改已执行 protocol v1.0.0 或其 hash。下一版 protocol 如继续使用该规则，应在 protocol JSON 中显式登记派生字段后再执行。
