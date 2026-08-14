# R4-T237：固定 release 分支 CI 质量门禁审计

日期：2026-08-14  
审计对象：`r3-real-data-execution-20260813`，HEAD `ef53af8`，GitHub Actions `CI` workflow。

## 结论

当前 GitHub Actions 失败于 `make check` 的第一个步骤：

```text
uv run --frozen ruff check src tests
```

失败不是论文数据测试或 review-round 科学测试失败，而是仓库既有 `src/` / `tests/` 代码尚未满足 pyproject 中已经声明的 Ruff 规则。最新失败运行：

`https://github.com/ahvsjags/BioInterfaceOS/actions/runs/31775218094`

本地 review-round 4 测试仍然通过：`53 passed in 74.42s`。

## Ruff 统计

使用锁定版本 `ruff==0.12.12`，对当前工作树只读运行 `ruff check src tests --output-format json --exit-zero`：

| 规则 | 数量 |
| --- | ---: |
| E501 line too long | 865 |
| F401 unused import | 23 |
| I001 import block unsorted | 23 |
| UP035 | 5 |
| SIM105 | 3 |
| UP038 | 2 |
| B007 | 2 |
| 合计 | 923 |

`ruff check --fix --diff` 显示 56 条安全自动修复，另有 7 条只有 `--unsafe-fixes` 才会处理。`ruff format --check src tests` 显示 62 个文件需要重新格式化，312 个文件已经符合格式规则。

问题最多的模块包括：

- `src/biointerfaceos/r4_small_molecule_corona_ood.py`：65 条；
- `src/biointerfaceos/r4_pxd017052_nsclc_biological_ood.py`：59 条；
- `src/biointerfaceos/r4_pmc13106918_technical_ood.py`：55 条；
- `src/biointerfaceos/cli.py`：54 条；
- `src/biointerfaceos/r4_three_lab_common_target_audit.py`：46 条；
- `src/biointerfaceos/r4_t194_fulltext_core_facility_execution.py`：46 条。

## 后续质量门禁

在 Ruff 完成后，CI 还会继续执行：

1. `ruff format --check src tests`；
2. `mypy`；
3. 全量 `pytest`。

本地用 `mypy==1.17.1` 预检得到 168 条 `error:` 行，说明不能只修 Ruff 后就宣称 CI 已恢复。

## 隔离 worktree 预演

在当前 HEAD 的临时 detached worktree 中运行安全 `ruff check --fix` 和 `ruff format`，没有修改当前分支。预演结果为：

- Ruff 自动修复 56 条后，剩余 868 条 lint 错误；7 条 unsafe fixes 仍未启用；
- `ruff format --check src tests` 全部通过，`374 files already formatted`；
- 预演 diff 涉及 64 个文件，约 4,199 行新增和 1,225 行删除；
- 预演 worktree 的 mypy 输出仍有约 174 条 `error:` 行。

因此，格式化本身不会关闭 CI；下一步需要人工审阅长命令、hash、路径、receipt 字符串和统计字段的重排，并逐模块处理类型错误。预演 worktree 已删除，当前分支没有因预演产生源代码变更。

## 建议的修复顺序

1. 先在隔离分支运行安全的 `ruff check --fix`，审阅 56 条实际 diff；
2. 对 865 条 E501 和 62 个格式文件运行 Ruff formatter，并逐文件检查长行是否包含命令、哈希、路径或科学数值，避免机械重排改变语义；
3. 手动修复 F401/I001/UP/SIM/B 规则，不启用未经审阅的 unsafe fixes；
4. 按模块修复 mypy 类型错误，优先处理三实验室执行、OOD 和 receipt 校验模块；
5. 运行 `make check`、review-round 3/4 测试和数据 receipt 校验，再推送新的 CI commit。

## 边界

- 本审计没有修改任何 `src/` 或 `tests/` 文件；
- 没有通过放宽 Ruff/mypy 配置制造绿色 CI；
- 没有把 GitHub Actions 运行当成非作者 lockbox、外部复现或用户采用证据；
- 原始论文数据、`reports/CONTRACT_AUDIT.md` 和未跟踪分析目录保持不变。
