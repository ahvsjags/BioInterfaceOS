# R4-T268：T250 clean-room 安装与复现候选执行

日期：2026-08-15  
证据类别：`AUTHOR_SIDE_CLEANROOM_CANDIDATE_NOT_EXTERNAL_RECEIPT`

## 执行结果

在 KAUST 共享目录从公开 immutable tag 新建了 fresh clone：

- tag：`v0.1.3-r10.50`
- checkout commit：`07db8ceef9b785bc3fba0f79f346f9f633645a63`
- clean-room 目录：`/ibex/user/xup0a/BioInterfaceOS-r4-external-r10-50-20260815-fixed-home`
- 候选输出：`/ibex/user/xup0a/BioInterfaceOS-r4-paper-data-fallback-20260814/reports/review_round_4/t268_author_cleanroom_candidate/v1.0.0/`
- helper SHA-256：`ffb4a5f98e14f5ec6f01d7e012e81a187140ceb0ec9bb6e65b56ec6e3805570d`
- output-hash file SHA-256：`57fb5dcb15830bafc41dc7fc2a17f8191a2c6ccf590cd15d4ee1013b1832de39`

执行了：

```text
uv sync --locked --all-groups
uv run biointerfaceos data verify-r4-t250-four-lab-common-target --strict
uv run pytest -q tests/review_round_4/test_r4_t250_four_lab_common_target_execution.py
uv lock --check
```

结果：

```text
R4_T250_FOUR_LAB_COMMON_TARGET_VERIFY_VALID
observations=783 targets=7 laboratories=4 measurement_batches=115 models=3
1 passed
```

## 证据边界

该执行证明当前公开 tag 可在新目录安装并重建 T250 验证结果，但执行者仍是作者控制的 KAUST 环境。因此它不能计入：

```text
external_scientific_reproduction
external_user_adoption
protected_lockbox_evaluator_receipt
scientific_submission_ready
```

真正关闭无作者复现门禁仍需要一个无作者参与团队从公开入口运行同一 helper，并返回身份、COI、环境指纹、命令、输出 hash、失败账本和签名/immutable locator。
