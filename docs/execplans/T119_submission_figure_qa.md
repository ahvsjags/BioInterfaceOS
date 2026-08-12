# T119 — 提交级图件重建与视觉 QA

## 目的

替换当前“从任意 JSON 行提取数值并绘制装饰性图表”的 publication renderer。新 renderer 必须按 figure spec 的字段绑定、单位、独立单位、区间和证据等级生成图件，并在几何、语义和可视化三层通过检查。

## 边界

- 只修复软件图件管线与历史 fixture 图件的诚实表达；不将 fixture 数值升级为真实实验结果；
- 不改写 T111/旧 release 的 hash 受保护 artifact；新 R2 输出使用新的版本化目录；
- 没有 real-data source、n、单位或区间的 panel 必须撤回或渲染为 protocol/contract diagram，不能用聚合柱状图替代。

## 实施步骤

1. 定义 versioned `FigureSpec`：每个 panel 显式声明 source file、字段映射、图形类型、x/y units、independent unit、n、interval method、evidence class、caption 和可发表状态；
2. renderer 只接受 declared field mappings；拒绝隐式列选择、空单位、未声明 n/interval、source/manifest hash 不匹配和跨 evidence-class 拼接；
3. 为 SVG 建立 viewBox/geometry linter：所有 shape/text 近似 bounds 必须落在可见区域，panel label、axis title、legend 和 data marks 不得 clipping 或 overlap；生成 PNG 后还需 raster dimensions/blank-margin check；
4. 建立 semantic QA：source values、axis labels、单位、n、interval、caption、figure/table cross-reference 和 evidence boundary 均逐项对照 spec；
5. 对每个图生成 field-map/source-data card、machine QA receipt 及独立人工 visual-signoff 模板；fixture 图件添加 `CONTRACT_TEST` watermark/caption；
6. 新增错误字段、标签裁切、装饰性 chart、缺少 interval、错误 source hash 和未签署 visual QA 的负例测试；生成 R2 report 和撤回列表。

## 验收

- 每个新 panel 具有可验证的 declared field mapping、单位、独立单位、n 和 uncertainty/abstention 说明；
- 自动 QA 在 SVG/PNG geometry、manifest hash、source fields、caption 和 evidence language 上失败封闭；
- 所有 fixture-derived 图仅表述 contract/software behavior，不含 empirical validation、independent-study、scientific replication 或 OOD generalization 声称；
- 旧问题图要么被可审计替换，要么明确撤回，不能以视觉装饰掩盖不存在的数据。

## 失败处理

无可重建 source data 或未完成 visual signoff 的图不进入公开 bundle，相关文稿只保留 protocol/implementation 图，并把缺口交由 T118/T120–T124 的真实数据与复现门禁处理。
