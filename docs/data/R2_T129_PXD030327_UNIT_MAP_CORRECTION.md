# T129 PXD030327 样本映射更正记录

**记录日期：** 2026-08-13  
**证据等级：** `DEVELOPMENT_OBSERVATION`；仅用于来源筛选，不是模型输入、
实证结果或独立验证。  
**当前决定：** `NOT_ADMITTED_PENDING_NUMERIC_MATERIAL_COVARIATE_AND_CROSS_LAB_ENDPOINT`

## 更正范围

`R2_T129_CC0_PRIDE_API_DISCOVERY_LOG.md` 先前对 PXD030327 的限定性检查只
覆盖了文件列表的前两页，并记录为没有 mapping-named asset。完整项目搜索响应
列出了官方 `Sample_table.xlsx`，因此“前两页没有映射文件”的观察不能继续被解释
为项目没有来源映射。本记录不修改既有 v1.0 non-admission receipt；它追加可复核
的来源资产事实，并维持未准入决定。

## 官方资产与固定观察

| 资产 | 官方 URL | 观察到的大小 | SHA-256 |
| --- | --- | ---: | --- |
| 样本映射 | `https://ftp.pride.ebi.ac.uk/pride/data/archive/2022/09/PXD030327/Sample_table.xlsx` | 65,050 bytes | `b1e4a750122e1c3f70808caf666bf0ed432d63bf37d4c359ad831d14633f486a` |
| 7-NP 蛋白矩阵 | `https://ftp.pride.ebi.ac.uk/pride/data/archive/2022/09/PXD030327/EXP21053_7NP_libfree_relaxed.pg_matrix.tsv` | 1,782,272 bytes | `e58fb1dc7d234b67471ae19f82caac2d6c7735e609a6a6eb6cd7aef39b4c23a3` |
| 10-plate 蛋白矩阵 | `https://ftp.pride.ebi.ac.uk/pride/data/archive/2022/09/PXD030327/EXP21053_10plates_libfree_relaxed.pg_matrix.tsv` | 8,926,147 bytes | `d9d83c7578eccb5cc171b88151e96193ee5872528c7f6a2bee834b83bd7346da` |

`Sample_table.xlsx` 的 `Run info` 工作表有 806 个来源 run 行，字段为 `Run`、
`NP`、`P/NP ratio`、`Replicate`、`Remove from analysis`、`Notes` 和
`Incubation time`。其中 636 行的 `Remove from analysis=false`；`P/NP ratio`
显式取值为 0、0.3、1、1.25、2、2.5、5、10、20、40、50、80、100、320 和
`NA`，重复编号为 1–4。

对两个矩阵的 Windows 路径列名先去路径和 `.d` 后缀后：7-NP 矩阵有 160 个 run
列，其中 102 个精确匹配未排除映射行；10-plate 矩阵有 659 个 run 列，其中 534
个精确匹配未排除映射行。两个矩阵合并后恰有 636 个唯一 run 与未排除映射行匹配。
矩阵其余 183 个 run 列没有被重新解释：本记录既不把它们视为生物学重复，也不据此
推断排除原因。

## 为什么仍不能冻结 T129 target

1. `P/NP ratio` 是来源定义的数值暴露条件，不是粒径、表面电荷、组成比例或其他
   数值材料属性；`NP-A` 至 `NP-E` 仍是类别标签，不能被编码为连续材料特征。
2. 这是一项 Seer Inc. 来源研究，尚未与第二个独立实验室共同冻结可比 endpoint。
3. 蛋白矩阵是作者的 project-level output；尚未建立跨研究的统一预处理、analysis
   unit、study-held-out split、negative controls 或 T121 修订。

因此该项目提高了真实数据实施路径的可审计性，但不会授权模型拟合、ablation、OOD、
lockbox 评估或任何 submission-ready 声明。重新评估必须首先取得来源匹配的数值
材料/尺寸协变量，并在至少两个独立实验室之间冻结共同 endpoint。
