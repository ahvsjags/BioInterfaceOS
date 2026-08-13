# R3 KAUST 作者服务器复跑记录

状态：`AUTHOR_RUN_COMPUTATIONAL_REPLAY_ONLY`。本记录只证明同一作者控制的 KAUST Ibex 环境能够从冻结、已纳入版本控制的 R3 输入重新产生结果；它不是独立 lockbox、独立验证或无作者团队的科学复现。

## 已执行事项

- 工作目录：`/ibex/user/xup0a/BioInterfaceOS-r3-real-data`。
- 复跑所用源提交：`d6147a2`；生成的结果随后作为提交 `543130d` 纳入同一 R3 分支。
- 环境：CPython 3.11.15、`uv 0.12.1`、项目锁定依赖、NumPy 2.4.6。
- `uv run pytest tests/review_round_3 -q`：9 passed（1.29 s）。
- 在新的、不可覆盖原收据的输出根 `reports/review_round_3/kaust_author_replay/v1.0.0/` 中，严格复跑冻结的共同 target 模型和银纳米粒外部 OOD；分别得到 2,724 和 953 条观测。
- 新输出含 18 个文件；两个最终收据 SHA-256 分别为：
  - `common_rank_model_evaluation/model_evaluation_receipt.json`：`65eea7d975f85b63a64f303d030aaff5d5efe0a2701978b185181e905ab31230`
  - `silver_external_ood/silver_external_ood_receipt.json`：`dfc6ecf181ee3b35b242c763785872d23e85e825e09bf4185bcf57a5beca5bbf`

## 比较结果与解释

将 KAUST 输出和原 R3 输出的模型结果、负对照、配对消融及样本计数逐项比较，所有数值在绝对误差 `<= 1e-12` 内一致。两套产物的文件 SHA-256 不相同是预期的：报告内记录了不同的输出相对路径，且原运行登记的是 NumPy 2.3.5、KAUST 锁定环境是 2.4.6。不得把这项作者复跑表述为字节完全一致，也不得将它提升为独立证据。

## 可复跑命令

```bash
cd /ibex/user/xup0a/BioInterfaceOS-r3-real-data
uv sync --locked --all-groups
uv run pytest tests/review_round_3 -q
```

随后使用 `R3ModelEvaluationWorkflow(..., output_root=<new-empty-directory>).run(strict=True)` 和 `R3SilverExternalOODWorkflow(..., output_root=<new-empty-directory>).run(strict=True)` 在新的输出目录执行。工作流拒绝复写已有输出，因此审计收据不会被运行者静默替换。

## 仍未关闭的强 Q1 门槛

本记录不改变 `scientific_submission_ready=false`。非作者 lockbox receipt、无作者外部科学复现、公开版本 DOI 和真实外部安装/采用证据仍需由相应的独立主体完成，并遵循 [外部交接包](R3_EXTERNAL_LOCKBOX_AND_REPRODUCTION_HANDOFF.md)。
