# R4 T222：论文全文/补充表数据兜底路线

日期：2026-08-14。状态：`PAPER_DATA_FALLBACK_AUDITED`。

由于本项目当前无法再获得新的湿实验样本，本轮把“真实实验数据”定义为可公开获取、可逐行追溯、能从论文全文/补充表或公共 accession 重新取得的真实测量结果，并严格按照证据等级使用：

| 路线 | 真实数据来源 | 可核验量 | 允许的写法 | 不能替代 |
|---|---|---:|---|---|
| T178 三实验室共同 target | PMC 全文补充数据 + PRIDE/公开 accession | 3 个 laboratory anchors、99 个共同 target、2,724 observations、47 batches | development compatibility / source-local rank benchmark | lockbox、无作者复现、生物学独立验证 |
| T195 三实验室执行 | Dalian、UCD、Edinburgh 公开来源 | 9 个冻结 target、809 observations、85 batches、3 outer folds | author-run exploratory portability execution | 非作者 evaluator 和外部采用 |
| T181 论文附带 biological cohort | PMC7376165 Supplementary Data 5 | 141 biological units、666 合格 batches、17,026 observations、34 shared targets | paper-attached exploratory biological-cohort OOD | 新实验室复制、临床验证 |
| Silver paper OOD | PMC6592156 CC-BY-3.0 supplementary workbook | 30 batches、953 observations、50 shared targets | author-run OOD；无作者复现候选入口 | 真实 no-author receipt（需第三方重获和运行） |

机器可读冻结表：`docs/data/R4_T222_PAPER_DATA_FALLBACK_LEDGER.json`。

机器验证与 receipt：

```bash
uv run biointerfaceos data audit-r4-t222-paper-data-fallback --strict
uv run biointerfaceos data verify-r4-t222-paper-data-fallback --strict
```

本轮在 KAUST/当前 checkout 中验证为：4 条路线、4 个 source registry、8 个 source maps、4 个结果报告；所有路线的 `independent_validation`、`external_scientific_reproduction`、`external_user_adoption`、`doi_archived` 和 `scientific_submission_ready` 均保持 `false`。

这条路线解决的是“没有可审计真实公开数据”和“论文数据来源没有统一证据边界”的问题；它不能凭作者内部运行生成非作者身份、受保护 lockbox、外部采用或 DOI。强 Q1 生物学发现/临床效用表述仍然不成立，稿件应定位为可审计的计算方法、公开数据 benchmark 与 reproducibility resource，直到真实外部 receipt 到达。
