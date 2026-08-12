# T119 — R2 图件渲染与视觉 QA 完成记录

状态：`DONE`（协议图件软件 QA 已完成；真实数据结果图仍由 T122–T124 阻塞）。

## 处理结果

- 历史 15 张 fixture-derived 数值图未改写、未删除，但均登记为 `WITHDRAWN_FROM_R2_SUBMISSION_SCOPE`：它们缺少可验证字段映射、独立单位分母、区间声明和 R2 图件 QA receipt；
- 新增 `biointerfaceos publication render-r2 --strict`，只生成三张 `PROTOCOL_ONLY` SVG/PDF/600-dpi PNG：证据边界、公开发行分类、真实数据与独立验证路线；
- 每图强制 source hash、显式 nodes/edges 字段映射、`NOT_APPLICABLE` 的单位/n/interval 声明、证据等级、SVG bounds/overlap/text-size 规则、PNG 像素门槛和 output hash verification；
- 拒绝测试覆盖 source hash 篡改、隐式/错误字段映射、节点越界、节点重叠、重复执行和输出文件篡改。

## 自动与视觉检查

- 自动 receipt：`PASS_R2_PROTOCOL_FIGURE_SUITE`；3 图、15 张历史图撤回、600 dpi、field-mapped、`scientific_submission_ready=false`；
- 代理内部视觉审查：在 2026-08-12 对三张 PNG 逐张检查，标题、节点、箭头标签、图注、页底边界均可读；未观察到节点重叠、图形越界、文本裁切或空白面板；
- 此记录是 Codex 执行的内部视觉审查，不是独立人类科学签署，不能替代 T128 的外部复现/编辑验收。

## 证据位置

- 源规范与蓝图：`docs/figures/R2_FIGURE_SPECS.json`、`docs/figures/R2_PROTOCOL_FIGURE_DATA.json`、`docs/figures/R2_FIGURE_BLUEPRINT.md`；
- 不可变 render/QA 包：`reports/review_round_2/submission_figures/v1.1.0/`；
- 该包明确为 software replay/protocol output，不包含经验数据、效应值、性能、p 值或外部泛化结果。
