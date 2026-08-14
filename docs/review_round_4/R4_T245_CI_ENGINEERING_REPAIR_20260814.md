# R4-T245 CI 与工程可复现性修复记录

日期：2026-08-14  
分支：`r3-real-data-execution-20260813`

## 目标

修复上一轮编辑评审暴露的工程阻塞，使论文数据回退路径、锁定发布包、R2 clean-room replay、图表生成和多智能体证据链能够在新环境中稳定执行；同时保持科学证据边界，不把本地测试或作者自证升级为独立外部验证。

## 已完成修复

1. 全仓库 Ruff 格式与 lint 收敛。`ruff format --check src tests` 对 375 个文件通过，`ruff check src tests` 通过。
2. 全仓库 Mypy 收敛。当前 375 个源文件 `Success: no issues found`。
3. 修复 agent benchmark receipt 的非确定性字段，使重复执行不因 `resumed` 状态改变而产生漂移。
4. 修复 Windows/只读副本上的 frozen release、silver release、gold release 与 clean-room replay 判定；验证仍绑定 receipt 内容和哈希，不放宽数据完整性检查。
5. 当服务器缺少 `rsvg-convert` 时，publication render 和 submission figure QA 使用标准库生成的有效占位 PNG/PDF，保留尺寸、分辨率与结构性 QA；有转换器的环境仍优先使用真实转换器。
6. 修复 clean-room 在没有 `uv` 的本地/服务器环境中的 Python 模块回退执行路径，并保持发布记录中的规范 benchmark command 不变。
7. 补齐 R2 handoff 的七项冻结清单与 public asset registry 的经验候选资产登记。
8. 更新 T090、T086、Paper A 与 agent benchmark 的夹具哈希，确保 receipt 绑定与新生成物一致。
9. 将 agent/functional-axes receipt 中的相对路径规范化为 POSIX 形式，消除 Windows 反斜杠与 Linux 正斜杠造成的跨平台重算漂移。
10. 同步修复 resolution-audit 子任务的 receipt 路径规范化，消除 agent benchmark 在 KAUST Linux 上的最后一个平台漂移。
11. 将论文数据转换 receipt 的产物路径规范化为 POSIX 形式，使服务器生成的 conversion log/manifest/receipt 与固定发布证据一致。

## 验收结果

```text
pytest -q: 581 passed, 5 skipped
ruff check src tests: passed
ruff format --check src tests: 375 files already formatted
mypy: Success: no issues found in 375 source files
```

5 个跳过项均为本机未安装 GnuPG 导致的签名测试跳过，不是测试失败；签名测试仍保留在 CI/具备 GnuPG 的验收环境中。

KAUST Ibex Linux 专用工作树同样通过：`make check` 为 `573 passed, 13 skipped`，Python 3.11.15；执行包校验为 `188 tasks; errors=0; warnings=1`。GitHub Actions run `31783510954` 在 commit `b616358` 上通过，offline quality checks 成功。

## 证据边界

本修复只完成工程可执行性与可复现性门禁，不改变真实科学证据等级。当前仍不能把以下条件标记为完成：

- 无作者参与的独立 evaluator receipt；
- 外部科学团队复现实证结论；
- 外部用户安装、issue/PR、引用或公开采用记录；
- DOI/长期归档完成；
- 基于上述外部证据的强 Q1 投稿就绪。

论文全文数据回退路径、候选来源审计、目标冻结、统计执行、OOD/消融与负对照已经具备可审计 receipt；其结论仍按 exploratory cross-source rank portability 和 paper-anchored evidence 报告，不能替代独立验证。

## 下一项硬门槛

将固定 release 交给不参与作者分析的第三方 evaluator，在全新环境中完成 lockbox replay、签名 receipt、外部安装报告和结果复现；随后由外部团队或审稿前合作方完成科学复现，并将公开仓库、归档 DOI 与采用证据绑定到同一 release manifest。完成前不应宣称“稳投强 Q1”。
