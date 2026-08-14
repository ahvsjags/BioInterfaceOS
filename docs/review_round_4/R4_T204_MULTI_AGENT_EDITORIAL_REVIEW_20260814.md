# R4 T204：T203 后多智能体编辑复审共识

日期：2026-08-14。评审对象：提交 beaa00a；新增证据：T203 PMC10257194 论文全文数据 OOD、source audit、KAUST receipt verify。三位独立 agent 分别承担统计、计算生物学编辑、复现/出版完整性角色。

## 共识分数

| 模块 | 三 agent 分数 | 共识判断 |
|---|---:|---|
| 数据兼容性、许可、样本基础与行级追溯 | 78–90 | 中心约 83；97 个共同 target、45 batches、45 biological units 和 4,362 个 source cells 已审计，但 CC-BY-NC-ND 不可进入 redistributable release，且只新增一个论文实验室 |
| 统计设计与泄漏控制 | 85–88 | 中心约 86；target 冻结、development-only nested selection、batch estimand、cluster bootstrap 和消融设计较强；置换控制固定已选 alpha，claim 需保持探索性 |
| 统计执行与有效样本 | 62–84 | 中心约 76；模型和 receipt 已真实执行，有效独立层级是 45 个 biological units/batches，不能把 4,362 行当作独立 n；提交树不含 NC-ND raw/map/receipt |
| 模型、消融、OOD、负对照与不确定性 | 78–82 | 中心约 80；full ridge Spearman 0.1773，配对增量 0.0241，2,000 batch bootstrap 和 256 permutations 已完成，但仍是单一新实验室的作者运行 paper OOD |
| Biological novelty | 38 | T203 是 frozen protein-rank prediction 的 portability/OOD，不是新的机制、因果或正交实验发现 |
| 外推与跨平台泛化 | 35 | 只支持探索性 portability，不支持跨实验室、平台和材料体系的稳定泛化结论 |
| Protected lockbox 独立评估 | 10 | 只有协议/handoff，无非作者 protected evaluator receipt |
| 无作者科学复现 | 5 | 无从原始输入起步且无作者参与的端到端 receipt |
| 外部用户采用 | 0–8 | 无真实外部用户/团队安装、任务日志、issue/PR 或采用记录 |
| DOI 永久归档与公开发布 | 20 | deposit package 已准备，但没有与 immutable release 绑定的正式 DOI receipt |
| 论断边界与出版诚信 | 88 | 许可和 claim boundary 基本写清，必须继续明确 independent_validation=false |

## 综合结论

- 严格出版成熟度：57–60/100，中心约 58/100。
- 方法/软件论文核心成熟度：约 77–86/100；尚不足以声称强 Q1 稳投。
- 生物学发现型论文成熟度：约 35–40/100，不建议按机制发现或临床转化论文投稿。
- 三位 agent 一致建议：NOT_READY；编辑决定为 MAJOR_REVISION。

## T203 的真实增量

T203 解决了“没有新的内部原始实验数据”这一限制：通过论文全文正式补充材料获得真实受试者测量矩阵，完成了 45 个受试者、97 个共同 target 的作者运行 OOD，并产生真实模型、配对消融、cluster bootstrap、负对照和行级 receipt。它提高了模型/OOD 和统计执行分数，但没有改变独立性硬门禁。

## 硬门禁 ledger

| 门禁 | 当前状态 | 解释 |
|---|---|---|
| independent_validation | false | T203 是作者运行 paper OOD，不是非作者验证 |
| external_scientific_reproduction | false | 没有无作者参与、从原始输入起步的复现 receipt |
| protected_lockbox_evaluator_receipt | 缺失 | 没有一次性不可见 endpoint/输入和外部 evaluator receipt |
| external_user_adoption | 0 | 没有可核验的外部用户/团队采用记录 |
| doi_archived | false | 只有准备好的 deposit package，没有正式 DOI record |
| scientific_submission_ready | false | 任一强门禁未关闭即保持 false |

## 必须完成的下一轮工作

1. 保留 T203 为 analysis-only paper OOD，并把 raw/map/receipt 存放在受控分析环境，不违反 CC-BY-NC-ND。
2. 获取非作者 protected lockbox evaluator receipt。
3. 获取至少一个无作者参与、从原始输入起步的科学复现 receipt。
4. 获取至少两条可核验的外部用户/团队采用记录。
5. 完成与 immutable release 绑定的正式 DOI 归档，并再次进行 claim audit 和多智能体复审。
