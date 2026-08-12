# T118 — R2 可重建软件回放发布

状态：完成（仅软件回放；不构成科学复现或实证验证）。

服务器端执行 `python -m biointerfaceos reproduce release --strict` 已通过。生成的
不可变收据位于
`reports/review_round_2/reproducibility/r2_software_replay/v1.1.0/`，并声明：

- `status=PASS_R2_SOFTWARE_REPLAY`；
- `source_asset_count=667`；
- `rebuilt_protocol_figures=3`；
- `software_replay=true`；
- `scientific_reproduction=false`；
- `scientific_submission_ready=false`。

发布记录包含默认拒绝的公开源码清单和 SHA-256、由 `pyproject.toml` 与 `uv.lock`
派生的 CycloneDX 风格 SBOM、确定性源码归档、纯公开临时工作树重放收据、容器配方
以及 JUnit 风格结果。临时工作树中只复制注册为 `PUBLIC` 的资产；数据、源注册表、
历史报告、历史发布载荷和旧稿件均不在范围内。两份 `release/` 边界说明文件作为
Apache-2.0 的说明文档例外保留，未携带任何历史发布载荷。

重放从公开规格重新生成三张 R2 协议图，并通过 `publication verify-r2 --strict`。
旧数值图表没有可公开、逐字段的真实数据源，因此不会被伪装为可重建的实证表或图；
它们继续由 T119 的撤回清单隔离。T120–T124 仍须取得真实、逐行溯源的数据和独立
验证，才可能产生科学结果或可投稿的实证图表。
