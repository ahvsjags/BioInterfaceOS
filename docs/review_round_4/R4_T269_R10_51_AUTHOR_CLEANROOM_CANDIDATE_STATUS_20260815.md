# R4-T269：v0.1.3-r10.51 作者清洁室候选执行状态

## 结论

本文件记录的是作者控制的 KAUST fresh-clone / clean-room candidate run，不是非作者科学复现、lockbox 评估或外部采用证据。它用于证明固定 release tag 在另一份作者控制的工作目录中可以重新安装、验证并执行公开 T250 路线。

## 固定输入与运行环境

- immutable tag：`v0.1.3-r10.51`
- tag source commit：`beff3c6d7b7092fb38586cc4187423bf8a93b553`
- helper：`scripts/r4_external_reproduction_r10_51.sh`
- helper SHA-256：`c11e1aab3b27024546ebe3171943f88e31fd53a46333e0e6d06e082ebd76e1a0`
- fresh-clone run root：`/ibex/user/xup0a/BioInterfaceOS-r4-external-r10-51-20260815`
- execution host：KAUST / IBEX；执行者仍为作者控制环境
- output root：`/ibex/user/xup0a/BioInterfaceOS-r4-paper-data-fallback-20260814/reports/review_round_4/t268_author_cleanroom_candidate/v1.1.0/`

## 通过项

1. fresh clone checkout 到精确 tag source commit；
2. `uv sync --locked --all-groups` 完成；
3. T250 strict verify 通过：4 laboratory/source anchors、7 targets、783 observations、115 measurement batches；
4. T250 regression test 通过：`1 passed`；
5. helper 对输入、tag、测试和输出 hash 做了记录；
6. candidate output bundle SHA-256：`f830521c1bc82ed30eb286899b6d41c3149aed4d46aea3b0239ea01151ec9c79`。

## 证据边界

该结果只证明作者侧固定 release 的安装与执行可重复。它不能升级为：

- 非作者一次性 lockbox receipt；
- 无作者参与的原始输入起步科学复现；
- 外部用户独立安装与采用；
- 四个独立 biological cohorts；
- universal sequence superiority、机制验证或临床 utility。

T250 仍应表述为预冻结 all-source target intersection 条件下的 source-conditional portability；T265 biological-unit route 仍为 analysis-only supplement。`scientific_submission_ready` 继续为 `false`。

