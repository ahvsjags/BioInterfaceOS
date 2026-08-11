# BioInterfaceOS：医学材料 AI-for-Science × 因果世界模型 × 科研 Agent
## Codex 逐步执行总手册（GOAL.md）

> **版本**：1.0.0  
> **冻结日期**：2026-08-11  
> **项目性质**：纯计算、无湿实验、全公开匿名可访问数据  
> **默认资源上限**：4×A100、1.5 TB 可写存储；可向更多 GPU 扩展，但不得依赖额外算力才能完成最低可发表版本  
> **最高目标**：形成可投稿 Nature Machine Intelligence / Nature Communications / npj Computational Materials 的完整科学工作；方法和基准同步面向 ICLR / ICML / NeurIPS。Nature Biomedical Engineering / Nature Nanotechnology 仅在出现强普适科学规律和真正时间盲测成功时作为冲刺目标，不作保证。

---

# 0. 如何使用本文件

把本执行包放到一个空目录或现有 Git 仓库根目录，文件至少包括：

```text
AGENTS.md
GOAL.md
PLANS.md
PROJECT_STATE.yaml
TASKS.tsv
CODEX_START_PROMPT.md
```

Codex 进入仓库后应按以下顺序读取：

1. `AGENTS.md`：长期不变的工作纪律；
2. `GOAL.md`：完整科学与工程合同；
3. `PLANS.md`：复杂任务的 ExecPlan 写法；
4. `PROJECT_STATE.yaml`：当前进度；
5. `TASKS.tsv`：依赖有向图和验收标准；
6. 当前任务对应的 `docs/execplans/*.md`。

**本文件不是供 Codex“参考”的建议，而是项目验收合同。** Codex 只有在产物、测试、审计和门禁同时通过后，才能把任务改成 `DONE`。

---

# 1. 项目最终目标

## 1.1 旗舰科学问题

构建一个可审计的多模态因果世界模型，学习并检验：

\[
\boxed{
\text{材料物理身份}
\rightarrow
\text{动态蛋白冠/生物界面}
\rightarrow
\text{细胞与免疫状态}
\rightarrow
\text{摄取、毒性、补体、凝血和体内分布}
}
\]

给定：

- 材料组成、结构、粒径、PDI、形状、表面电荷、配体、PEG/聚合物密度、配比；
- 生物流体、物种、疾病状态、蛋白背景；
- 孵育时间、剂量、温度、混合、洗涤、离心、质谱和细胞实验协议；

系统需要预测并解释：

1. 软冠、硬冠和蛋白交换动力学；
2. 蛋白功能模块和细胞摄取、补体、炎症、凝血、毒性及分布之间的关系；
3. 哪些规律能跨论文、跨实验室、跨材料家族、跨物种和跨生物流体迁移；
4. 如何从目标生物身份反向设计材料表面或配方；
5. 何时模型必须拒绝外推。

## 1.2 项目不是以下内容

不得把项目退化为：

- 文献聊天机器人；
- 只做 RAG 问答；
- 只抽取论文表格；
- 随机切分下的纳米毒性分类；
- 仅凭大模型生成材料建议；
- 以“Agent 数量多”作为主要创新；
- 只报告一个最高分模型；
- 没有时间盲测和溯源的知识图谱。

## 1.3 三个可独立投稿的产物

### Paper A：BioInterfaceBench

目标：ICLR / NeurIPS Datasets & Benchmarks 等。

必须包括：

- 许可清晰、可复现下载的多模态数据；
- 文档抽取、蛋白冠、摄取、体内结局、反事实排序和反向设计任务；
- 严格的 study/lab/material/species/time OOD 切分；
- 容器化 grader；
- Agent 任务完成率、泄漏率、复现率和成本评测。

### Paper B：CausalBioInterface

目标：ICLR / ICML / NeurIPS / Nature Machine Intelligence 方法型工作。

必须包括：

- 动态蛋白冠中介；
- 组合数据建模；
- 层级研究效应和协议偏移；
- 因果中介与发表偏倚敏感性分析；
- 域外不确定性和拒绝机制；
- 多 Agent 假设—实验—反证闭环。

### Paper C：Transferable Biointerface Laws

目标：Nature Communications / Nature Machine Intelligence / npj Computational Materials；强结果再冲击更高层级。

必须以新的科学规律为中心，而不是模型性能。至少形成三类独立、可重复的规律，例如：

- 跨材料稳定的蛋白功能轴；
- 协议校正后经典规律消失或反转；
- 冠中介比例；
- 人—鼠血浆可迁移映射；
- 可解析动力学公式；
- 时间盲测正确预测材料排序；
- 低不确定性反向设计候选。

---

# 2. 不可违反的硬约束

## 2.1 数据访问硬约束

主分析只能使用满足以下全部条件的数据：

1. 匿名访问；
2. 无注册；
3. 无登录；
4. 无 API key；
5. 无申请；
6. 无人工审批；
7. 无机构认证；
8. 无数据使用协议签署；
9. 无付费；
10. 许可允许当前分析用途，且再分发边界明确。

遇到需要上述任一条件的数据源时：

- 不得列入 `BLOCKERS.md`；
- 标记为 `REJECTED_CREDENTIALLED` 或 `REJECTED_RESTRICTED_LICENSE`；
- 记录在 `registry/rejected_sources.parquet`；
- 寻找匿名公共替代源；
- 继续所有独立任务。

## 2.2 许可硬约束

- PMC 中并非所有文章均可自动批量复用；只用 PMC Open Access Subset 或明确许可全文。
- 文章正文、图片和补充文件分别记录许可。
- CC0/CC BY 可进入公开可再分发层；CC BY-NC 等进入非商业分析层并在发布时隔离；许可不明的内容只能保存元数据和来源链接，不可加入公开训练包。
- 不通过绕过付费墙、Cookie、验证码或网站限制获得内容。
- 只通过官方 API、FTP、OAI、云桶或明确允许的下载入口进行系统检索。

## 2.3 科学诚信硬约束

- 缺失值写 `null`，不猜测。
- 每个数字都要有证据定位。
- 自动提取结果不得冒充人工金标准。
- 失败实验、负结果和被否定假设必须保留。
- 不能用锁定测试集反复调参。
- 不能把作者、期刊、实验室、论文 ID、页面版式当预测特征。
- 因果语言必须通过因果门禁。
- 不得声称“穷尽全网”；必须报告检索范围、版本和饱和度。
- 不得保证 Nature 级别发表，只能按预设门槛评估是否具备投稿竞争力。

## 2.4 无湿实验硬约束

本项目不设计或要求湿实验。强验证由以下方式替代：

- 真正按发表日期冻结的时间盲测；
- 原始公开质谱/组学统一重分析；
- 跨材料、跨实验室、跨物种和跨生物流体 OOD；
- 多模态证据三角验证；
- 负对照和反事实一致性；
- 后续公开论文中的一回合验证；
- 公开代码、数据清单、容器和 grader。

---

# 3. 冻结的首版范围

## 3.1 材料家族

首版主训练范围：

1. 脂质体；
2. 脂质纳米颗粒（LNP）；
3. 聚合物纳米颗粒；
4. 聚合物胶束。

首版外部验证：

5. 金属、金属氧化物或其他无机纳米颗粒。

暂不把植入物、支架、水凝胶、骨材料全部混入主模型。它们在主线稳定后作为迁移扩展。

## 3.2 终点

按优先级：

1. 蛋白冠组成、功能模块、软/硬冠和时间变化；
2. 细胞摄取；
3. 细胞活力/毒性；
4. 补体、炎症、免疫激活；
5. 凝血和血小板相关终点；
6. 器官或肿瘤富集；
7. 治疗或递送效率作为次级终点。

## 3.3 时间切分

固定为：

- 训练候选：公开日期不晚于 **2023-12-31**；
- 验证：**2024-01-01 至 2024-12-31**；
- 锁定测试：**2025-01-01 至 2026-08-11**。

在冻结任务完成前，Agent 不得检索、下载、摘要或浏览锁定测试文章的标题、摘要、图表、补充材料或关联数据。仅允许保存日期区间规则，不允许保存测试内容。

## 3.4 最小可发表主链

若全范围数据不足，自动缩小到：

\[
\text{脂质体/LNP/聚合物载体}
\rightarrow
\text{人或鼠血浆蛋白冠}
\rightarrow
\text{细胞摄取或肿瘤/器官富集}
\]

不得为了维持“大而全”而牺牲协议恢复、证据质量和 OOD 验证。

---

# 4. Codex 自主执行协议

## 4.1 每个任务的循环

Codex 对每个任务执行：

1. 读取任务、依赖、当前状态和相关文档；
2. 创建或更新 ExecPlan；
3. 检查输入是否存在、版本是否正确；
4. 实现最小可测试垂直切片；
5. 运行单元测试；
6. 运行小样本集成测试；
7. 扩大到真实数据；
8. 运行验收；
9. 保存日志和失败产物；
10. 更新状态、任务表、决策和账本；
11. 创建聚焦 Git commit；
12. 进入下一依赖满足任务。

## 4.2 状态枚举

```text
NOT_STARTED
READY
RUNNING
FAILED_RETRYABLE
FAILED_FINAL
BLOCKED_EXTERNAL
DONE
WAIVED
```

`DONE` 必须有：

- 预期文件；
- 测试命令；
- 测试输出；
- 数据或代码哈希；
- 账本记录；
- Git commit。

## 4.3 失败处理

- HTTP 429/5xx：指数退避、抖动、尊重 `Retry-After`。
- 404：检查 API 版本、标识符和替代官方端点。
- 401/403/登录页：拒绝该源，不能尝试绕过。
- 解析失败：保留原始资产，进入隔离队列，换结构化来源或备用解析器。
- GPU OOM：减小 batch、梯度累积、混合精度、检查点和 CPU 卸载；不能直接跳过关键模型。
- 单一数据集失败：继续其他独立数据源。
- 三次不同方案均失败：记录根因、风险和可替代任务，再继续。

## 4.4 不允许的“完成方式”

- 只写空函数、TODO 或 mock 就标完成；
- 只在 notebook 中运行；
- 只在随机切分下达到高分；
- 删除失败日志；
- 看到测试集后重新训练；
- 用 LLM 自评替代自动 grader；
- 把数据下载成功等同于数据可用；
- 用“论文说了”代替数字证据。

---

# 5. 仓库与数据湖结构

Codex 必须创建并维护：

```text
BioInterfaceOS/
├── AGENTS.md
├── GOAL.md
├── PLANS.md
├── PROJECT_STATE.yaml
├── TASKS.tsv
├── Makefile
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── config/
│   ├── project.yaml
│   ├── source_policy.yaml
│   ├── storage.yaml
│   ├── splits.yaml
│   ├── ontology.yaml
│   ├── extraction.yaml
│   ├── proteomics.yaml
│   ├── transcriptomics.yaml
│   ├── benchmark.yaml
│   ├── agents.yaml
│   └── models/
├── src/biointerfaceos/
│   ├── cli.py
│   ├── config.py
│   ├── ids.py
│   ├── logging.py
│   ├── registry/
│   ├── sources/
│   ├── literature/
│   ├── extraction/
│   ├── normalization/
│   ├── proteomics/
│   ├── transcriptomics/
│   ├── evidence/
│   ├── benchmark/
│   ├── models/
│   ├── causal/
│   ├── uncertainty/
│   ├── design/
│   ├── agents/
│   └── reporting/
├── schemas/
├── registry/
│   ├── SOURCE_MANIFEST.parquet
│   ├── rejected_sources.parquet
│   ├── EXPERIMENT_LEDGER.parquet
│   ├── CLAIM_LEDGER.parquet
│   └── RELEASES.parquet
├── data/
│   ├── raw/
│   │   ├── literature/
│   │   ├── supplementary/
│   │   ├── pride/
│   │   ├── geo/
│   │   └── external/
│   ├── bronze/
│   ├── silver/
│   ├── gold_auto/
│   ├── gold_consensus/
│   ├── gold_expert/
│   ├── features/
│   ├── splits/
│   └── locked_test/
├── benchmarks/
│   ├── tasks/
│   ├── graders/
│   ├── baselines/
│   └── releases/
├── models/
│   ├── checkpoints/
│   ├── releases/
│   └── model_cards/
├── agents/
│   ├── prompts/
│   ├── tools/
│   └── policies/
├── experiments/
│   ├── configs/
│   ├── runs/
│   └── frozen/
├── docs/
│   ├── execplans/
│   ├── data_dictionary/
│   ├── methods/
│   └── manuscript/
├── reports/
│   ├── task_ledger.jsonl
│   ├── DECISIONS.md
│   ├── BLOCKERS.md
│   ├── source_audit/
│   ├── qc/
│   ├── benchmark/
│   └── final/
├── release/
├── scripts/
├── slurm/
├── containers/
└── tests/
```

## 5.1 数据层定义

- **Raw**：从官方来源获取的原始字节，不修改；
- **Bronze**：解包、格式探测、基础元数据；
- **Silver**：自动结构化、标准化和初步去重；
- **Gold-auto**：由结构化表格、机器可读 XML 或明确规则直接验证；
- **Gold-consensus**：两个独立抽取路径一致，且通过规则；
- **Gold-expert**：真实专家签名确认；没有签名不得使用该标签。

## 5.2 内容寻址

每个资产 ID：

\[
\text{asset\_id}=\operatorname{SHA256}(\text{source}+\text{canonical URL}+\text{content hash})
\]

每个实验 ID：

\[
\text{experiment\_id}=\operatorname{SHA256}(\text{paper family}+\text{material arm}+\text{bioenvironment}+\text{protocol}+\text{time}+\text{dose})
\]

任何派生表必须保存：

- 输入版本；
- 代码 commit；
- 配置哈希；
- 生成时间；
- 输出 SHA256。

---

# 6. 环境与工程底座

## 6.1 默认环境

- Python 3.11；
- Linux 为主；
- CPU 下载与解析；
- GPU 用于视觉/语言抽取、深度模型和 Agent 并行实验；
- `uv` 管理 Python 依赖，缺失时回退到 `venv + pip`；
- DuckDB + Parquet 作为本地数据主干；
- Docker 或 Apptainer 用于可复现发布；无容器权限时必须有纯环境回退。

## 6.2 首次引导命令

Codex 应创建等价于以下行为的 `make bootstrap`：

```bash
set -euo pipefail
python3.11 -m venv .venv  # 仅在 uv 不可用时
# 安装项目、测试、数据、模型和文档依赖
# 创建目录和空账本
# 运行 doctor
```

不得把未经固定版本的 `pip install package` 作为发布步骤。开发期可解析兼容版本，首个可复现 release 必须生成 lock 文件。

## 6.3 Python 依赖组

至少分组：

```text
core: pydantic, typer, rich, structlog, pyyaml, tenacity
storage: pyarrow, duckdb, pandas, polars
validation: pandera, pint
network: httpx, aiohttp
xml_html: lxml, beautifulsoup4
pdf: pymupdf, pdfplumber
chemistry: rdkit
ml: scikit-learn, xgboost, catboost, torch, lightning
stats: statsmodels, pymc, arviz
omics: anndata, scanpy, biopython, pyteomics
viz: matplotlib
quality: pytest, pytest-cov, hypothesis, ruff, mypy, pre-commit
```

只有确实需要时才引入新依赖，并记录原因和许可证。

## 6.4 `make doctor`

必须检查：

- Python 版本；
- 可写目录；
- 剩余存储；
- Git 状态；
- CPU、RAM、GPU；
- `sbatch`、Docker、Apptainer 是否存在；
- 网络 DNS 和官方源连通性；
- 关键外部二进制版本；
- 锁定测试目录在冻结前为空；
- 无凭证环境变量被意外写入日志。

输出：`reports/doctor.json` 和 `reports/doctor.md`。

## 6.5 统一命令面

Codex 必须提供 CLI：

```bash
biointerface doctor
biointerface source audit
biointerface literature discover
biointerface literature ingest
biointerface extract run
biointerface normalize run
biointerface pride discover
biointerface pride ingest
biointerface pride reprocess
biointerface geo discover
biointerface geo ingest
biointerface dataset build
biointerface split build
biointerface benchmark run
biointerface model train
biointerface model evaluate
biointerface agent run
biointerface claims audit
biointerface freeze create
biointerface locked-test fetch
biointerface locked-test evaluate
biointerface release build
```

所有命令必须支持：

```text
--config
--dry-run
--resume
--limit
--log-level
--seed
```

---

# 7. 存储预算与按需回取

默认硬预算：1.5 TB。建议配额：

| 类别 | 上限 |
|---|---:|
| 元数据、JATS XML、清单 | 50 GB |
| 开放 PDF、图片、补充材料 | 200 GB |
| PRIDE 原始及处理数据 | 600 GB |
| GEO/SRA 和表达矩阵 | 250 GB |
| 特征、缓存、检查点 | 300 GB |
| 安全余量 | 100 GB |

Codex 必须实现 `storage_guard`：

- 下载前根据 Content-Length 或清单估算；
- 超配额时不启动；
- 优先下载元数据和作者处理表；
- 只有入选主实验的数据才回取原始质谱；
- 可重建中间文件可清理，但要先验证重建命令；
- Raw 文件删除需要显式 release 策略，默认不删除；
- 每日或每批任务生成 `reports/storage_usage.parquet`。

不得执行“先把所有 PDF 和所有质谱全下载再说”。

---

# 8. 统一数据模型

## 8.1 最小实验单元

每一行对应具体实验臂：

\[
e=(M,B,P,t,D,C,R,Y,S)
\]

其中：

- \(M\)：材料物理身份；
- \(B\)：生物环境；
- \(P\)：实验协议；
- \(t\)：时间；
- \(D\)：剂量；
- \(C\)：蛋白冠或界面状态；
- \(R\)：细胞/免疫状态；
- \(Y\)：终点；
- \(S\)：研究、实验室、平台和证据来源。

## 8.2 核心表

### `sources`

| 字段 | 含义 |
|---|---|
| source_id | 稳定 ID |
| source_name | Europe PMC、PMC OA、PRIDE 等 |
| base_url | 官方入口 |
| access_mode | anonymous / rejected |
| registration_required | bool |
| api_key_required | bool |
| license_policy | 许可规则 |
| robots_or_terms_checked_at | 检查时间 |
| adapter_version | 适配器版本 |
| status | admitted / quarantined / rejected |

### `documents`

| 字段 | 含义 |
|---|---|
| document_id | 统一文献 ID |
| doi, pmid, pmcid | 外部 ID |
| title | 题目，仅用于检索和审计，不进入预测特征 |
| publication_date | 首次公开日期 |
| paper_family_id | 正文、预印本、修订版、补充和后续论文聚类 |
| oa_status | OA 状态 |
| license | 许可 |
| eligible_split | train/val/locked_test/excluded |

### `assets`

| 字段 | 含义 |
|---|---|
| asset_id | 内容寻址 ID |
| document_id | 所属文献 |
| asset_type | JATS/PDF/XLSX/CSV/FIGURE/RAW/MS/COUNT |
| canonical_url | 官方 URL |
| local_path | 本地路径 |
| sha256 | 字节哈希 |
| size_bytes | 大小 |
| redistribution | allowed/noncommercial/manifest_only |
| download_status | 状态 |

### `evidence`

| 字段 | 含义 |
|---|---|
| evidence_id | 证据 ID |
| asset_id | 资产 ID |
| locator_type | section/table/cell/figure/panel/page/line |
| locator | 精确位置 |
| raw_text | 原始文本或单元格 |
| raw_value | 原始数值字符串 |
| normalized_value | 标准化值 |
| normalized_unit | 标准单位 |
| extraction_method | deterministic/model/digitized/manual |
| extraction_confidence | 0–1 |
| evidence_grade | A/B/C/D |
| reviewer_status | unreviewed/consensus/expert |

### `materials`

至少包括：

```text
material_id
material_family
core_composition
lipid_components
polymer_repeat_unit
canonical_smiles_or_psmiles
component_molar_fractions
surface_ligands
peg_mw
peg_density
particle_size_nm
pdi
zeta_mv
shape
porosity
coating
cargo
synthesis_summary
missingness_mask
```

### `bioenvironments`

```text
bioenvironment_id
species_taxid
species_name
biofluid
serum_or_plasma
healthy_or_disease
sex
age_group
protein_concentration
anticoagulant
temperature_c
ph
cell_line_accession
cell_type
organ_or_tissue
```

### `protocols`

```text
protocol_id
incubation_time_min
incubation_temperature_c
material_concentration
fluid_fraction
mixing_method
centrifugation_g
centrifugation_min
wash_count
separation_method
ms_platform
acquisition_mode
quantification_method
cell_assay
readout_platform
normalization_method
```

### `corona_measurements`

```text
experiment_id
protein_accession
ortholog_group
functional_module
corona_type
abundance_value
abundance_unit
relative_or_absolute
time_min
measurement_error
limit_of_detection
missingness_type
```

### `response_measurements`

```text
experiment_id
outcome_family
outcome_name
value
unit
time
baseline
fold_change
uncertainty
sample_size
replicate_type
```

### `claims`

```text
claim_id
claim_text
claim_type
hypothesis_id
supporting_evidence_ids
contradicting_evidence_ids
analysis_run_ids
split_scope
causal_status
red_team_status
replication_status
claim_gate_status
```

## 8.3 证据等级

- A：原始样本级数据；
- B：作者补充表或机器可读表；
- C：图像数字化；
- D：正文定性描述。

训练损失需要考虑证据误差，不得等权使用。

## 8.4 图像数值误差

\[
\tilde y=y+\epsilon_{axis}+\epsilon_{pixel}+\epsilon_{trace}+\epsilon_{legend}
\]

图像提取结果必须保存坐标校准、像素分辨率、重复追踪差异和最终区间。

---

# 9. 数据源准入与官方接口

## 9.1 准入流程

每个数据源先运行：

```text
probe → access test → license classification → rate-limit policy → sample download → checksum → parser smoke test → admit/reject
```

输出 `source_audit`，包含 HTTP 状态、是否跳转到登录页、许可文本位置、可否匿名下载、样本哈希和适配器测试。

## 9.2 允许优先实现的来源

### A. Europe PMC

用途：检索、元数据、开放全文 XML、补充材料、引用和数据库链接。

官方接口模板：

```text
https://www.ebi.ac.uk/europepmc/webservices/rest/search
https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML
https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/supplementaryFiles
```

实现要求：

- 使用 cursor 分页；
- 显式限制开放全文和日期；
- 记录 API 返回的 OA 和许可字段；
- 不把摘要许可自动等同于全文许可；
- 记录请求和响应哈希；
- 尊重速率限制和服务条款。

### B. PMC Open Access Subset

用途：JATS XML、PDF、图片和补充文件。

只使用官方 FTP、OAI-PMH、OA Web Service、E-Utilities、BioC 或 Cloud 服务。不得系统抓取普通网页。

### C. PRIDE / ProteomeXchange

用途：蛋白冠、LNP、脂质体和聚合物载体原始或处理质谱。

官方 API 模板：

```text
https://www.ebi.ac.uk/pride/ws/archive/v3/projects/<PXD>
https://www.ebi.ac.uk/pride/ws/archive/v3/search/projects
```

首批优先项目：

- PXD017776：脂质体组成—人血清蛋白冠—细胞摄取；
- PXD063915：不同脂质纳米颗粒—小鼠血浆冠—肿瘤富集；
- PXD054751：LNP、DNA 与蛋白冠；
- PXD057444：离子化聚合物胶束与 LNP；
- PXD033976：软冠/硬冠动态演化。

先下载：

1. 项目元数据；
2. 文件清单和校验值；
3. SDRF/样本设计；
4. 作者结果表；
5. 搜索结果；
6. 最后才是入选项目 RAW。

### D. GEO / SRA

用途：纳米材料暴露、巨噬细胞、内皮、肝脏、肿瘤摄取、异物反应的公开组学。

- GEO 公共数据无需登录；
- 优先处理作者 count matrix 和 metadata；
- 只有核心验证所需时才下载 FASTQ；
- SRA 原始数据使用官方 SRA Toolkit；
- 记录 GSE/GSM/SRP/SRR 映射。

### E. PubChem PUG-REST

用途：配体、脂质、小分子结构和性质标准化。

官方接口：

```text
https://pubchem.ncbi.nlm.nih.gov/rest/pug/
```

限制请求不超过官方建议速率；大批量优先 bulk 下载或批处理，不能高频单条调用。

### F. ChEMBL Web Services

用途：配体、分子、细胞、靶点和生物活性先验。

官方接口：

```text
https://www.ebi.ac.uk/chembl/api/data/
```

必须处理分页和版本号。

### G. UniProt、GO、Reactome、Cellosaurus

用途：蛋白标准化、功能模块、通路、物种和细胞系映射。

只使用公共下载/API，保存版本和发布日期。

### H. 公开代码和聚合物先验

可作为表示学习或复现来源：

- ScienceAgentBench；
- AstaBench；
- AI Scientist-v2；
- MatterGen；
- FlowMM；
- TransPolymer；
- PolyIE；
- Open Macromolecular Genome。

克隆时必须记录 commit、license 和本项目实际借鉴的模块。不得直接拼接其代码后声称新方法。

### I. 纳米材料专门数据库

NanoCommons、eNanoMapper、caNanoLab、NBI Knowledgebase、PROTCROWN、PC-DB 逐个运行准入审计：

- 有匿名下载且许可明确：进入主源；
- 可浏览但不能合法批量下载：仅作为候选索引；
- 需要登录/申请：拒绝；
- 许可不明：隔离，不进入公开 release。

## 9.3 明确排除

- UK Biobank 等申请型队列；
- 任何需要账号的 Kaggle 下载；
- DrugBank 等许可受限数据；
- 付费全文；
- 绕过验证码或反爬限制；
- 数据出售平台或来历不明的镜像；
- 需要云厂商私有凭证的对象；
- 只有截图而无法确认单位、实验臂和来源的数据。

---

# 10. 系统检索与“全网数据”覆盖策略

## 10.1 检索词组

至少建立以下概念组：

### 材料

```text
nanoparticle, nanomaterial, nanocarrier, liposome, lipid nanoparticle,
LNP, polymeric nanoparticle, polymeric micelle, nanomedicine,
gold nanoparticle, silica nanoparticle, iron oxide nanoparticle
```

### 生物界面

```text
protein corona, biomolecular corona, hard corona, soft corona,
corona dynamics, plasma adsorption, serum adsorption,
biointerface, opsonization, apolipoprotein, complement
```

### 结局

```text
cellular uptake, internalization, cytotoxicity, viability,
complement activation, coagulation, platelet, inflammation,
biodistribution, tumor accumulation, organ accumulation,
pharmacokinetics, delivery efficiency
```

### 数据线索

```text
proteomics, mass spectrometry, LC-MS/MS, PRIDE, ProteomeXchange,
GEO, RNA-seq, single-cell, supplementary table, raw data
```

## 10.2 初始核心查询

```text
(material terms) AND (protein corona terms)
(material terms) AND (protein corona terms) AND (uptake terms)
(material terms) AND (protein corona terms) AND (biodistribution terms)
(material terms) AND (complement OR coagulation OR platelet)
(material terms) AND (proteomics OR mass spectrometry)
```

按材料家族、物种、血清/血浆、时间和终点展开。

## 10.3 引用追踪

对每个高价值种子文献执行：

- backward references；
- forward citations；
- database links；
- accession extraction；
- 预印本和正式版聚类；
- 同实验室连续论文聚类；
- 补充材料和 GitHub/Zenodo 关联。

## 10.4 饱和判据

不得用“搜了很多”作为完成。连续两轮查询扩展同时满足以下条件才可冻结 discovery v1：

1. 新增合格实验臂 < 2%；
2. 无新增材料家族—终点组合；
3. 无新增匿名公共原始数据项目；
4. 新文献主要是重复、综述或缺乏可恢复协议；
5. 检索流和排除原因可复现。

## 10.5 文献家族去重

同一工作可能有预印本、正式版、纠错、补充和数据论文。建立 `paper_family_id`，整族只能进入一个切分。禁止同一实验以不同版本泄漏到训练和测试。


---

# 11. 文献、表格、补充材料与图像抽取流水线

## 11.1 抽取优先级

按可靠性从高到低：

1. 机器可读 CSV/TSV/Parquet；
2. XLSX/ODS 中的原始表格；
3. JATS XML 表格；
4. HTML 表格；
5. PDF 矢量表格；
6. 图像数字化；
7. 正文定性描述。

同一数值有高等级证据时，不用低等级覆盖；但保留所有证据以检测冲突。

## 11.2 JATS/全文解析

输出：

```text
sections.parquet
paragraphs.parquet
tables.parquet
figures.parquet
references.parquet
accessions.parquet
```

每个节点保存：

- 文档 ID；
- section path；
- XML XPath；
- 文本 offset；
- 表格行列；
- 图号/面板；
- 相关材料、协议和终点候选。

单元测试至少覆盖：

- 命名空间差异；
- 多级表头；
- 合并单元格；
- 脚注；
- 科学计数法；
- ±、范围、百分数；
- Unicode 微符号和负号。

## 11.3 补充文件解析

对每个补充文件：

1. MIME 探测，不信任扩展名；
2. 病毒/压缩炸弹安全检查；
3. 解包到内容寻址目录；
4. 识别 sheet、表头和单位行；
5. 保存原单元格值、公式、显示值；
6. 识别实验臂和重复；
7. 生成表级和行级 provenance；
8. 不自动执行宏或嵌入脚本。

XLSX 必须同时保存：

- workbook hash；
- sheet 名；
- cell range；
- raw value；
- displayed value；
- formula（如有）；
- merged-cell 信息。

## 11.4 PDF 解析

只有在无结构化版本时使用 PDF。步骤：

1. 判断文本型还是扫描型；
2. 文本型优先直接读取字形与坐标；
3. 表格使用两种独立解析器；
4. 结果不一致进入审计队列；
5. OCR 仅作为最后手段；
6. OCR 结果必须与轴标签、单位和正文交叉验证；
7. 保存页码和 bounding box。

不得因为 OCR 输出“看起来合理”就入 Gold。

## 11.5 图像曲线数字化

实现可复现的半自动 pipeline：

```text
panel detection
→ plot-type classification
→ axis detection
→ tick and scale calibration
→ legend/series association
→ line/bar/point extraction
→ uncertainty estimation
→ cross-check with caption and text
```

支持首版：

- bar + error bar；
- scatter；
- line/time curve；
- dose-response；
- biodistribution bar/point；
- heatmap 仅抽取明确色标值。

必须输出：

```text
figure_id
panel_id
series_id
x_value
x_unit
y_value
y_unit
lower_error
upper_error
pixel_uncertainty
calibration_residual
extraction_overlay_path
```

验收：

- 在合成图上的中位相对误差满足预设阈值；
- 在人工可核对小集上报告误差分布；
- 不能识别时应拒绝而非猜测；
- 所有点可回放到 overlay。

## 11.6 双路径结构化抽取

对正文和表格中的材料—协议—结果关系，至少运行两条独立路径：

- 路径 A：规则、词典、表格结构和单位约束；
- 路径 B：结构化模型/LLM，输出严格 Pydantic schema。

进入 `gold_consensus` 的条件：

1. 关键实体一致；
2. 数值和单位一致或可解释换算；
3. experiment arm 一致；
4. provenance 完整；
5. 通过范围和逻辑检查；
6. 无跨表/跨图误配。

模型提示必须要求：

- 只从给定证据抽取；
- 缺失填 null；
- 返回引用片段和定位；
- 不使用背景知识补齐；
- 区分作者观察和讨论推测；
- 区分材料制备值和蛋白冠后测量值。

## 11.7 关键抽取字段

### 材料

- core、shell、coating、cargo；
- 脂质/聚合物成分和摩尔比；
- 粒径与测量方法；
- PDI；
- zeta；
- 形状；
- PEG 分子量和密度；
- 配体类型和密度；
- 分子结构或 p-SMILES；
- 合成/纯化摘要。

### 生物环境

- serum/plasma；
- 物种；
- 健康/疾病；
- 浓度/体积分数；
- 抗凝剂；
- 温度、pH；
- 细胞系或组织。

### 协议

- 孵育时间；
- 材料浓度；
- 混合；
- 离心 g 值而非仅 rpm；
- 转子信息；
- 洗涤次数；
- 分离方法；
- 质谱平台和定量方法；
- 摄取/毒性读数和归一化。

### 结果

- 蛋白丰度；
- enrichment；
- 摄取；
- viability；
- complement/cytokine/coagulation；
- organ/tumor accumulation；
- 样本量和误差条定义。

---

# 12. 实体标准化、单位和本体

## 12.1 单位系统

使用 `pint` 和领域规则。标准单位建议：

```text
particle_size: nm
zeta: mV
concentration_mass: mg/mL
concentration_molar: mol/L
incubation_time: min
temperature: degC
centrifugation: x g
biodistribution: %ID/g 或原始单位并保留换算上下文
uptake: assay-specific normalized value + explicit unit
```

单位转换保存：

- raw value；
- raw unit；
- normalized value；
- normalized unit；
- conversion rule ID；
- conversion uncertainty。

rpm 只有转子半径可恢复时才换算 x g；否则保留 rpm 并设置 `conversion_unavailable=true`。

## 12.2 物理合理性检查

范围检查只用于标记，不应静默删除。例如：

- size ≤ 0：错误；
- size > 10,000 nm：极端/可能非纳米，审计；
- PDI < 0：错误；
- zeta 超出 ±200 mV：审计；
- fraction 总和偏离 1：检查百分数、mol% 和缺失组分；
- viability 超出常规范围：检查 baseline、fold-change 或百分数定义；
- 孵育时间为 0：区分即时测量和缺失。

所有异常进入 `qc_flags`，原值不丢失。

## 12.3 材料实体解析

建立层级：

```text
material family
→ formulation
→ component
→ chemical structure
→ surface architecture
→ batch/experimental arm
```

规则：

- “PEGylated LNP”不是唯一材料 ID；
- 配比改变即不同 formulation；
- 冠前/冠后粒径不能混为同一属性；
- 商品名仅作 synonym，不进入模型；
- 结构未知时使用可解释的 composition descriptors，不伪造 SMILES。

## 12.4 蛋白标准化

每条蛋白记录映射：

```text
reported_name
reported_accession
canonical_uniprot
species_taxid
ortholog_group
protein_family
GO terms
Reactome pathways
functional corona module
```

跨物种比较优先使用 ortholog group 和功能模块，不直接把人鼠 accession 当同一蛋白。

## 12.5 功能模块

初始模块至少包括：

- complement；
- coagulation；
- apolipoproteins/lipid transport；
- immunoglobulins；
- acute phase；
- adhesion/ECM；
- cytoskeleton；
- albumin/high abundance carriers；
- innate immune recognition；
- protease/inhibitor；
- unknown/other。

模块定义必须版本化，保留多标签，不用单一路径强行唯一归类。

## 12.6 细胞和终点标准化

- 细胞系映射 Cellosaurus；
- 原代细胞保存 donor、组织和物种；
- 摄取区分表面结合与内化；
- 细胞毒性区分 assay；
- 体内富集区分时间、剂量、组织和度量；
- “higher targeting”定性文字不能替代定量结果。

---

# 13. PRIDE 原始蛋白组统一重分析

## 13.1 选择原则

一个 PRIDE 项目进入 raw reprocessing 必须满足：

- 与主链直接相关；
- 样本设计可恢复；
- 文件大小在预算内；
- 物种和 FASTA 可确定；
- 有至少一个下游终点或可形成跨项目冠比较；
- 不属于锁定测试日期范围，除非已完成 freeze。

## 13.2 数据摄取顺序

```text
project metadata
→ file manifest
→ checksums
→ sample design / SDRF
→ author result tables
→ search outputs
→ selected raw files
```

生成：

```text
data/bronze/pride/projects.parquet
data/bronze/pride/files.parquet
data/bronze/pride/sample_sheet.parquet
reports/qc/pride/<PXD>_design_audit.md
```

没有明确样本—材料臂映射时，不进行自动生物结论。

## 13.3 原始文件转换

对 Thermo RAW：

- 使用固定版本的 ThermoRawFileParser 转 mzML；
- 保存工具版本、命令、stdout/stderr、输入输出 SHA256；
- 检查 scan 数、MS level、retention time 和文件完整性；
- 转换失败保留 RAW 和日志。

其他厂商格式使用开放工具或作者提供 mzML；不得引入需要注册的闭源软件作为唯一流水线。

## 13.4 搜索与定量

首选开放、可复现路径：

- Sage 进行数据库检索、FDR 和可用的 LFQ；
- 或 OpenMS 开放工作流作为复核；
- 物种特异 UniProt reference proteome 固定版本；
- target-decoy；
- PSM、peptide、protein 层分别控制 FDR；
- 默认主结果 q ≤ 0.01；
- 固定酶切、修饰、质量容差来自项目方法，无法恢复时使用敏感性配置并明确标记。

必须保存：

```text
search_config.json
fasta_manifest.json
psm.parquet
peptide.parquet
protein.parquet
lfq.parquet
qc.json
```

## 13.5 缺失与组成数据

蛋白冠相对丰度满足组成约束。不能直接对未检出值统一补零再普通 MSE。

候选方法：

- detection/censoring 模型；
- logistic-normal；
- Dirichlet-multinomial；
- zero-aware CLR/ILR；
- presence/absence 与 abundance 双头。

任何插补都必须作为消融，不得成为隐藏默认。

## 13.6 跨项目协调

分开建模：

- DDA vs DIA；
- spectral count vs LFQ intensity；
- human vs mouse；
- serum vs plasma；
- hard vs soft corona；
- 不同 separation protocol。

通过层级测量模型和功能模块对齐，不强行把所有原始丰度拼成一张无批次矩阵。

## 13.7 PRIDE QC

至少报告：

- 文件和样本完整率；
- PSM/peptide/protein 数；
- FDR；
- replicate correlation；
- missingness；
- intensity distribution；
- top protein/module；
- 作者结果与重分析一致性；
- 对下游结局的可链接率。

若重分析与作者表差异大，不能择优使用；必须形成根因分析。

---

# 14. GEO/SRA 与细胞状态模块

## 14.1 用途

组学不是为了堆模态，而是用于验证冠功能模块是否与细胞状态一致：

\[
C \rightarrow R \rightarrow Y
\]

优先细胞：

- macrophage/monocyte；
- endothelial；
- hepatocyte；
- tumor cell；
- dendritic cell；
- platelet/neutrophil 相关体系；
- 植入物扩展中的 fibroblast。

## 14.2 项目发现

查询需同时含：

- 材料/纳米载体；
- 暴露/摄取/免疫；
- RNA-seq/scRNA-seq；
- 明确公开日期。

只纳入样本条件、材料和剂量可恢复的项目。

## 14.3 处理优先级

1. 作者 count matrix；
2. GEO 预计算 count；
3. 公开 processed matrix；
4. 只有必要时 FASTQ。

Bulk：

- raw counts；
- 样本 QC；
- 合理 normalization；
- differential expression；
- pathway/module score；
- study-specific effect。

Single-cell：

- 样本级而非细胞级切分；
- donor/replicate 作为统计单位；
- pseudo-bulk 主分析；
- 细胞类型映射；
- 避免把同一 donor 的细胞泄漏到不同集合。

## 14.4 输出

```text
omics_studies.parquet
omics_samples.parquet
expression_features.parquet
cell_state_modules.parquet
differential_results.parquet
```

所有差异结果记录模型、设计矩阵、对比、校正方法和多重检验。

---

# 15. 金标准、抽取评测与审计样本

## 15.1 三种 Gold 不得混淆

### Gold-auto

可由机器可读原始表和确定性规则直接核验，例如：

- CSV 单元格；
- XLSX 明确表头；
- JATS 表格；
- PRIDE metadata。

### Gold-consensus

两个独立路径一致并通过约束。仍属于自动/模型共识，不是专家金标准。

### Gold-expert

需要真实专家审阅并生成：

```text
reviewer_id
reviewed_at
scope
accepted_fields
rejected_fields
comments
signature_or_approval_artifact
```

Codex 只能生成 review packet，不能自行签名。

## 15.2 抽样策略

审计集分层覆盖：

- 材料家族；
- 终点；
- 表格/图像/正文；
- 年份；
- 高/低置信度；
- 单位复杂度；
- 冲突证据；
- 高影响结论。

## 15.3 抽取指标

- entity precision/recall/F1；
- relation F1；
- experiment-arm linking accuracy；
- numeric exact/relative error；
- unit accuracy；
- provenance locator accuracy；
- abstention precision；
- confidence calibration；
- conflict detection recall。

## 15.4 最低门槛

在进入大规模建模前，关键字段必须达到项目配置阈值。建议起始门槛：

- 材料家族、物种、生物流体、时间、剂量、终点类型 F1 ≥ 0.90；
- 数值+单位联合正确率 ≥ 0.90；
- experiment arm 关联 ≥ 0.85；
- provenance 定位 ≥ 0.95；
- 高置信自动数据的错误率 ≤ 5%。

达不到时，优先修抽取和缩小范围，不继续堆复杂模型。

---

# 16. 数据切分、锁定测试和泄漏防控

## 16.1 分组键

所有切分同时考虑：

```text
paper_family_id
study_id
lab_id
material_family
formulation_cluster
species
biofluid
publication_date
```

## 16.2 必做切分

- random sanity split；
- leave-paper-family-out；
- leave-study/lab-out；
- leave-material-family-out；
- leave-species-out；
- leave-biofluid-out；
- 时间切分。

主结论不能来自随机切分。

## 16.3 化学和配方近重复

对配体、脂质和聚合物计算结构或组成相似度；近重复 formulation 按 cluster 切分。只改名称但组成相同的材料不能跨集合。

## 16.4 锁定测试流程

冻结前：

- `data/locked_test/` 必须为空；
- Source Agent 的日期过滤必须拒绝 2025-01-01 后内容；
- 测试文章 ID 不进入 embedding、RAG、预训练或提示缓存；
- 不允许通过参考文献标题间接读取测试结果。

冻结任务生成：

```text
experiments/frozen/FREEZE.json
```

包括：

```text
git_commit
data_release_hash
split_hash
model_config_hash
analysis_plan_hash
random_seeds
predeclared_metrics
predeclared_claims
frozen_at
```

冻结后：

1. 单独下载锁定数据；
2. 不改模型结构、超参数或主要分析；
3. 执行一次正式评估；
4. 如发现代码 bug，只能做不依赖测试结果方向的修复，并记录前后结果；
5. 不成功结果也必须报告。

## 16.5 泄漏测试

自动运行：

- paper ID / title / author / journal 单独预测；
- lab ID 单独预测；
- 文件名和目录名预测；
- 图像版式预测；
- accession 预测；
- 近重复检索；
- 全文 n-gram 跨 split 重叠；
- 预训练语料污染敏感性分析；
- label permutation。

发现显著泄漏时，相关结果全部作废并重建 split。

---

# 17. BioInterfaceBench 任务与 grader

## 17.1 任务族

### Task E1：文档到结构化实验

输入：开放正文、表格、图和补充文件。  
输出：材料—环境—协议—结果 JSON。  
评分：实体、关系、数值、单位、provenance、拒绝质量。

### Task C1：材料与环境到蛋白冠

预测：单蛋白 presence/abundance、功能模块和动态轨迹。

### Task U1：蛋白冠到细胞摄取

重点：跨 study/material/species 排序。

### Task S1：安全性

毒性、补体、炎症和凝血，多任务且不允许标签混淆。

### Task B1：体内富集

器官/肿瘤富集和排序。

### Task CF1：反事实排序

只改变一个可解释因素时，预测方向和区间。

### Task D1：受约束反向设计

生成候选材料表面/配方，并通过有效性、适用域、不确定性和多目标 grader。

### Task A1：科研 Agent

给定冻结数据和目标，Agent 需要：

- 提出可检验假设；
- 编写并运行分析；
- 输出可复现结果；
- 识别反例；
- 不产生非法结论。

## 17.2 预测指标

按任务使用：

- AUROC/AUPRC；
- RMSE/MAE；
- Spearman/Kendall；
- NDCG；
- ECE/Brier；
- interval coverage/width；
- selective risk；
- OOD detection AUROC；
- decision curve 或 Pareto hypervolume。

报告 bootstrap CI，按 study 聚类重采样，不能把同一研究的多个点当独立样本。

## 17.3 Agent 指标

- task completion；
- executable code rate；
- clean-container reproduction；
- unsupported claim rate；
- leakage violation rate；
- failed-experiment preservation；
- cost/compute；
- scientific gain beyond fixed pipeline；
- red-team detection recall。

## 17.4 grader 原则

- 程序化评分优先；
- LLM judge 只能作为补充且要校准；
- 输入、容器、预算、工具固定；
- 输出必须包含文件，而非只给文字；
- grader 不暴露答案；
- benchmark release 固定 hash。

---

# 18. 基线系统

所有复杂模型之前先完成：

## 18.1 数据与统计基线

- global mean / majority；
- material-family mean；
- study-aware mean；
- linear regression / logistic regression；
- mixed-effects model；
- elastic net；
- random forest；
- XGBoost；
- CatBoost。

## 18.2 表征基线

- hand-crafted physicochemical descriptors；
- Morgan/chemical fingerprints；
- polymer sequence encoder；
- simple text embedding；
- simple image embedding；
- early/late multimodal fusion。

## 18.3 机制基线

- 材料 → outcome 直接模型；
- 材料 → corona；
- corona → outcome；
- 两阶段中介；
- 简化竞争吸附 ODE；
- 完整世界模型。

## 18.4 Agent 基线

- 固定脚本；
- 单 Agent 工具使用；
- RAG + code execution；
- 多 Agent 无树搜索；
- 多 Agent + tree search + red team。

每个基线都要使用相同 split、特征可见性和指标。

---

# 19. 核心数学模型

## 19.1 竞争吸附动力学

对蛋白/功能模块 \(i\) 的占据率：

\[
\frac{d\theta_i}{dt}=
 k_i^{on}(M,B)c_i(t)\left(1-\sum_j\theta_j\right)
-k_i^{off}(M,B)\theta_i
+\sum_{j\ne i}q_{ji}\theta_j
-\sum_{j\ne i}q_{ij}\theta_i
\]

约束：

\[
\theta_i\ge0,\qquad \sum_i\theta_i\le1
\]

先实现功能模块级模型，再评估是否有足够数据上升到单蛋白级。

## 19.2 组合分布

蛋白冠丰度向量 \(C\) 使用 simplex 分布：

\[
C \sim \operatorname{LogisticNormal}(\mu,\Sigma)
\]

或：

\[
C \sim \operatorname{Dirichlet}(\alpha)
\]

选择由 posterior predictive、校准和 OOD 表现决定。

## 19.3 神经受控微分方程

\[
\frac{dz(t)}{dt}=F_\psi(z(t),E_M(M),E_B(B),E_P(P),D,t)
\]

\[
\hat C(t)=G_C(z(t)),\quad
\hat R(t)=G_R(z(t)),\quad
\hat Y=G_Y(z(T))
\]

加入：

- 非负性；
- 容量/质量约束；
- 饱和；
- 软冠快变量、硬冠慢变量；
- 已知功能竞争先验；
- 协议和测量模型。

## 19.4 因果结构

\[
C=f_C(M,B,P,t,U_C)
\]

\[
R=f_R(C,M,B,P,D,U_R)
\]

\[
Y=f_Y(R,C,M,B,P,D,U_Y)
\]

研究层级：

\[
y_e\sim\mathcal N(\mu_e+u_{study}+u_{assay}+u_{species}+u_{biofluid},\sigma_e^2)
\]

中介分析必须报告：

- total effect；
- direct effect；
- indirect effect；
- heterogeneity；
- sensitivity to unmeasured confounding。

不能只运行一个 mediation package 就宣称机制成立。

## 19.5 发表选择模型

\[
P(O_e=1\mid y_e,n_e,study_e)=
\operatorname{sigmoid}(\alpha_0+\alpha_1|z_e|+\alpha_2n_e+\alpha_{study})
\]

通过 selection model、small-study effect 和敏感性分析评估偏倚。

## 19.6 多模态材料编码

\[
h_M=\operatorname{Fuse}(E_{chem},E_{polymer},E_{descriptor},E_{image},E_{protocol\ text})
\]

模态缺失使用显式 mask 和 modality dropout，不能把零向量误当真实零属性。

## 19.7 总损失

\[
\mathcal L=
\lambda_C\mathcal L_{corona}
+\lambda_Y\mathcal L_{outcome}
+\lambda_D\mathcal L_{dynamics}
+\lambda_H\mathcal L_{hierarchy}
+\lambda_I\mathcal L_{invariance}
+\lambda_U\mathcal L_{calibration}
+\lambda_K\mathcal L_{constraints}
\]

权重选择只能在训练/验证阶段完成。

## 19.8 不确定性

\[
U=U_{aleatoric}+U_{epistemic}+U_{extraction}+U_{domain}+U_{measurement}
\]

实现：

- deep ensemble 或 posterior approximation；
- heteroscedastic likelihood；
- extraction error propagation；
- conformal calibration；
- distance/density OOD；
- selective prediction。

---

# 20. 模型递进顺序与强制消融

## 20.1 模型阶段

### M0：数据 sanity

目标：确认标签、切分和指标无错。

### M1：层级统计模型

目标：量化 study/protocol effect，建立可解释基线。

### M2：直接黑箱

\[
(M,B,P,D,t)\rightarrow Y
\]

### M3：静态中介

\[
(M,B,P)\rightarrow C\rightarrow Y
\]

### M4：组合冠模型

显式建 simplex 和缺失。

### M5：动态世界模型

软/硬冠和时间轨迹。

### M6：层级因果世界模型

随机效应、中介、selection sensitivity。

### M7：多模态与跨域不变学习

加入结构、文本和图像；验证是否真正改善 OOD。

### M8：条件生成与反向设计

只在 M6/M7 稳定后开始。

## 20.2 每阶段进入下一阶段的条件

- 当前阶段在至少一个主要 OOD split 上优于前一阶段；
- 校准不恶化；
- 不是由单一 study 驱动；
- bootstrap 方向稳定；
- 泄漏测试通过；
- 复杂度增益有合理科学解释。

否则保留较简单模型。

## 20.3 强制消融

- 无 corona mediator；
- 无 protocol；
- 无 study random effect；
- 无 raw proteomics；
- 无 digitized figures；
- 单蛋白 vs 功能模块；
- 无 dynamics；
- 无 invariance；
- 无 uncertainty rejection；
- 无 Agent tree search；
- 无 red team；
- 仅高等级证据 vs 全证据加权。

## 20.4 统计比较

- 按 study 聚类 bootstrap；
- 配对比较相同测试实例；
- 多重比较校正；
- 报告效应量和区间；
- 不只报告 p 值；
- 预先定义主要指标和 secondary metrics。


---

# 21. 科研 Agent 系统：从“会聊天”升级为可审计的自动科学流程

## 21.1 总体原则

Agent 层不得替代数据层、统计层和评测层。系统采用：


default deterministic orchestrator + typed agent contracts + executable graders + append-only ledgers

即：

1. 调度、状态迁移、依赖检查、文件写入和门禁由确定性代码完成；
2. LLM Agent 只处理确实需要语义推理、假设生成、文档理解或代码提案的环节；
3. Agent 输出必须通过 JSON Schema/Pydantic 校验后才能进入数据库；
4. 每次 Agent 调用都记录模型、提示模板哈希、输入证据 ID、工具轨迹、输出、成本、错误和重试；
5. 任何自然语言判断都不能直接让任务变成 `DONE`；
6. 最终科学结论由预注册统计检验和外部验证决定，而不是由“评审 Agent 觉得合理”决定。

## 21.2 运行时分层

```text
Layer 0  Task DAG / state machine / lockbox firewall
Layer 1  deterministic tools: search, download, parse, normalize, model, test
Layer 2  specialist agents with typed inputs and outputs
Layer 3  hypothesis tournament and experiment manager
Layer 4  claim gate and release gate
```

核心模块路径固定为：

```text
src/biointerfaceos/agents/
├── contracts.py
├── registry.py
├── runtime.py
├── budgets.py
├── supervisor.py
├── source_scout.py
├── license_gate.py
├── extraction_agent.py
├── resolution_agent.py
├── evidence_auditor.py
├── mechanism_agent.py
├── statistician_agent.py
├── model_builder_agent.py
├── red_team_agent.py
├── reproducibility_agent.py
└── lockbox_evaluator.py
```

## 21.3 统一 Agent 输入输出合同

所有 Agent 必须实现：

```python
class Agent(Protocol):
    name: str
    version: str

    def run(self, request: AgentRequest, context: AgentContext) -> AgentResult:
        ...
```

`AgentRequest` 至少包含：

```text
request_id
agent_name
task_id
objective
allowed_tools
forbidden_tools
input_evidence_ids
input_artifact_hashes
budget
schema_version
seed
```

`AgentResult` 至少包含：

```text
request_id
status
structured_payload
claims
citations/evidence_ids
artifacts
executed_tools
validation_results
uncertainties
failure_modes
next_actions
model_metadata
prompt_hash
started_at
finished_at
```

状态只允许：

```text
SUCCESS
PARTIAL
RETRYABLE_FAILURE
NONRETRYABLE_FAILURE
REJECTED_BY_POLICY
REJECTED_BY_SCHEMA
```

## 21.4 工具权限

每个 Agent 使用最小工具集合。

| Agent | 允许 | 禁止 |
|---|---|---|
| SourceScout | 官方搜索/API、元数据读取 | 登录、验证码、抓取受限全文 |
| LicenseGate | 许可文本解析、策略匹配 | 猜测许可 |
| Extraction | 已准入资产读取、结构化输出 | 修改原始资产 |
| Resolution | 本体、词典、规则、相似度 | 无证据合并冲突实体 |
| Mechanism | 读取 Gold/Silver 数据、提出可证伪假设 | 读取锁定测试标签 |
| ModelBuilder | 写代码、运行训练与测试 | 修改冻结 split |
| Statistician | 预注册分析、统计检验 | 事后替换主指标 |
| RedTeam | 负对照、泄漏检查、反例搜索 | 删除不利结果 |
| LockboxEvaluator | 冻结后读取锁定包、执行固定命令 | 调参、改变阈值、训练 |

## 21.5 专家 Agent 职责

### A01：SourceScout

输入查询矩阵，输出候选资产，不直接下载大文件。职责：

- 发现论文、补充材料、公开数据库记录、原始组学和代码；
- 保存检索式、页码、游标和检索日期；
- 建立 DOI/PMCID/PXD/GSE/URL 关系；
- 对候选源做匿名访问预检；
- 输出 `candidate_source`，不做许可最终判定。

### A02：LicenseGate

- 区分元数据访问、分析使用、模型训练和再分发权限；
- 记录许可证据原文位置和解析置信度；
- 许可不明确时进入隔离区，不自动提升；
- 输出 `ADMIT_PUBLIC_REDISTRIBUTABLE`、`ADMIT_ANALYSIS_ONLY`、`QUARANTINE` 或 `REJECT`。

### A03：ExtractionAgent

内部可调用文本、表格、补充文件和图像四个子代理，但最终统一到实验模式：


a paper family → one or more experiments → material arms → protocol → measurements → evidence

每个字段必须返回：

- 原始字符串；
- 规范化值；
- 单位；
- 证据位置；
- 抽取方式；
- 置信度；
- 冲突标记。

### A04：ResolutionAgent

- 材料别名解析；
- 脂质/聚合物/配体结构解析；
- 蛋白到 UniProt 与基因标识映射；
- 细胞系、物种、生物流体和终点本体化；
- 将不确定合并保留为候选集合，不能强行单值化。

### A05：EvidenceAuditor

- 比较规则抽取、LLM 抽取、表格解析和原始数据重处理；
- 发现单位冲突、样本数不一致、图文冲突和复制错误；
- 对关键结论执行证据逆向追踪；
- 只允许审计通过的记录进入 Gold-auto。

### A06：MechanismAgent

- 从训练/验证数据提出可证伪机制假设；
- 输出明确的暴露、中介、结局、混杂、预期方向和失败条件；
- 为每个假设生成最小可执行分析计划；
- 不得使用锁定测试信息；
- 不得把文献共现直接解释为机制。

### A07：StatisticianAgent

- 检查 estimand、样本单位、聚类结构、重复测量和多重比较；
- 选择层级模型、bootstrap、置换或敏感性分析；
- 在实验运行前冻结主要指标、阈值和排除规则；
- 拒绝没有识别条件的因果措辞。

### A08：ModelBuilderAgent

- 根据 ExecPlan 实现基线或模型；
- 先写单元测试和 toy recovery test；
- 每次训练登记配置、种子、commit、数据哈希和资源消耗；
- 对异常高分主动触发泄漏审计。

### A09：RedTeamAgent

至少尝试：

- 标签置换；
- study-only、journal-only、year-only 和 protocol-only 预测；
- 删除最大研究；
- 近重复污染检测；
- 单位缩放攻击；
- 缺失模式攻击；
- 证据等级分层；
- 反例和方向翻转搜索；
- 锁定信息污染扫描；
- 提示注入和恶意补充文件文本测试。

### A10：ReproducibilityAgent

- 在干净环境从 manifest 重建指定结果；
- 验证容器、依赖锁、随机种子和结果容差；
- 对图表做来源追踪；
- 生成 `reproduction_receipt.json`。

### A11：LockboxEvaluator

该 Agent 在冻结任务完成前必须处于禁用状态。解锁后只允许：

1. 校验 lockbox 哈希；
2. 加载冻结模型、配置和阈值；
3. 执行预先写好的评测命令；
4. 输出结果和审计日志；
5. 不得训练、微调、筛选或修改图表定义。

## 21.6 Agent 调度状态机

```text
DISCOVER
  ↓
ADMISSION_GATE
  ↓
INGEST
  ↓
EXTRACT
  ↓
RESOLVE
  ↓
AUDIT
  ↓
HYPOTHESIS_PROPOSAL
  ↓
PREREGISTRATION_GATE
  ↓
EXECUTABLE_EXPERIMENT
  ↓
STATISTICAL_REVIEW
  ↓
RED_TEAM
  ↓
REPLICATION
  ↓
CLAIM_GATE
  ↓
RELEASE_GATE
```

伪代码：

```python
while queue.has_dependency_satisfied_item():
    item = queue.pop()
    result = runtime.execute(item)
    schema.validate(result)
    ledger.append(result)
    if result.status == "RETRYABLE_FAILURE":
        retry_with_bounded_policy(item)
    elif result.status in {"NONRETRYABLE_FAILURE", "REJECTED_BY_POLICY"}:
        release_independent_successors(item)
    else:
        run_declared_graders(item)
        advance_only_if_all_gates_pass(item)
```

## 21.7 模型提供方抽象

项目代码不得绑定单一商业 API。实现：

```text
LocalTransformersBackend
OpenAICompatibleBackend   # 可选，凭据由运行者自行配置，不写入仓库
MockBackend               # CI
ReplayBackend             # 完整复放既有调用
RuleBasedBackend           # 可确定性完成的任务
```

发布基准必须能在不提供私有 API key 的情况下运行：

- 数据、grader、规则基线和 replay 样例完全开放；
- 需要 LLM 的基线允许用户选择本地模型；
- 不将任何 API key 写入配置、日志或容器；
- `.env` 永远进入 `.gitignore`。

## 21.8 Agent 预算和停止条件

每个请求需要限制：

- 最大工具调用数；
- 最大候选假设数；
- 最大代码修复轮数；
- 最大重复查询数；
- 最大 GPU 预算；
- 最大输出记录数。

出现以下情况停止当前分支而不停止整个项目：

- 连续三次实质不同的尝试仍失败；
- 无法满足输入 schema；
- 证据等级不足；
- 预计信息增益低于阈值；
- 新实验与已有实验配置哈希相同；
- 需要读取锁定内容；
- 需要受限数据。

## 21.9 Agent 评测

除任务正确率外必须报告：


autonomous completion rate


evidence-grounded precision


schema-valid rate


citation/evidence resolution rate


reproducible-run rate


unsafe-source rejection recall


locked-data contamination rate


unnecessary-tool-call rate


cost per accepted scientific claim

任何 Agent 基线若不能从输出追溯到证据，不得进入主要结果表。

---

# 22. 假设锦标赛、预注册与 Claim Gate

## 22.1 Claim Ledger

创建 `registry/CLAIM_LEDGER.parquet`，字段至少为：

```text
claim_id
claim_version
plain_language_claim
formal_estimand
claim_type
exposure
mediator
outcome
population
comparison
expected_direction
minimal_effect_of_interest
primary_metric
primary_split
exclusion_rules
candidate_confounders
identification_assumptions
supporting_evidence_ids
contradicting_evidence_ids
preregistration_hash
analysis_commit
status
gate_results
allowed_wording
forbidden_wording
```

`status` 只允许：

```text
PROPOSED
DUPLICATE
NOT_FALSIFIABLE
PREREGISTERED
RUNNING
REFUTED
INCONCLUSIVE
ASSOCIATIONAL_SUPPORTED
MECHANISTIC_SUPPORTED
CAUSAL_SUPPORTED
LOCKBOX_REPLICATED
RETRACTED
```

## 22.2 假设锦标赛流程

### Stage 1：生成

MechanismAgent 从以下输入生成候选：

- 稳定残差；
- 跨研究异质性；
- 蛋白功能模块；
- 时序变化；
- 图谱中的矛盾边；
- 文献声称与统一重处理不一致；
- OOD 失败模式；
- 反事实模型结果。

### Stage 2：去重与新颖性

对假设文本、形式化变量和预期方向做语义与结构去重。不得把同一规律换术语后计为多个发现。

### Stage 3：可证伪性

每个候选必须回答：

1. 什么观察会支持它？
2. 什么观察会推翻它？
3. 最小可检测效应是什么？
4. 需要哪些独立研究？
5. 何种域外验证才算迁移？
6. 哪些已知混杂会产生相同模式？

无法回答即标为 `NOT_FALSIFIABLE`。

### Stage 4：预注册

在运行主要分析前写入：

```text
preregistrations/<claim_id>.yaml
```

并记录文件哈希和 Git commit。预注册后允许修复代码错误，但不得无痕改变主要指标、方向、排除规则或阈值。任何改变生成新版本并标记为探索性。

### Stage 5：实验执行

Experiment Manager 只运行预注册命令。结果无论正负均进入 `EXPERIMENT_LEDGER`。

### Stage 6：反证

RedTeamAgent 优先寻找：

- 一个研究驱动的效应；
- 协议混杂；
- 物种混杂；
- 发表年份混杂；
- 缺失机制；
- 不同归一化导致的方向变化；
- 证据等级依赖；
- 数据数字化误差可解释的效应。

### Stage 7：独立复制

主发现至少在未参与假设产生的 study/lab/material family 中复制；锁定测试复制单独标记。

## 22.3 假设优先级函数


the score is computed before the primary experiment


do not retroactively change weights for a favored hypothesis


define

\[
S(h)=
\alpha N(h)
+\beta F(h)
+\gamma I(h)
+\delta R(h)
+\eta D(h)
-\lambda C(h)
-\mu L(h)
\]

其中：

- \(N\)：新颖性；
- \(F\)：可证伪性；
- \(I\)：潜在信息增益；
- \(R\)：可独立复制性；
- \(D\)：设计价值；
- \(C\)：计算和数据复杂度；
- \(L\)：泄漏/混杂风险。

前 K 个假设进入主分析，其余保留为探索性，K 在配置中冻结。

## 22.4 Claim Gate 分层

### 关联性支持

必须同时满足：

- 预注册分析通过；
- study-clustered 区间不跨预设无效区；
- leave-one-study-out 方向稳定；
- 负对照不产生同等效应；
- 至少两个独立研究或实验室；
- 证据来源可完整追踪。

允许措辞：`associated with`、`predicts out of study`。

### 机制性支持

在关联性门禁之上：

- 中介变量在时间或实验逻辑上位于暴露与结局之间；
- 加入中介后直接路径有预期变化；
- 替代中介和随机蛋白模块不能复现；
- 机制模型优于直接黑箱且在 OOD 维持；
- 原始组学或独立模态支持该中介。

允许措辞：`consistent with a mediating mechanism`，除非进一步通过因果门禁。

### 因果性支持

只有满足全部条件才允许 `causal`：

1. DAG 和 estimand 预先冻结；
2. 识别假设明确且可讨论；
3. 关键混杂可测或有合理代理；
4. positivity/overlap 通过；
5. study/protocol selection 被建模；
6. 未测混杂敏感性达到预设强度；
7. 至少一个自然实验、配对干预、剂量/时间结构或可信工具变量提供额外识别；
8. 替代 DAG 和负对照不能解释结果；
9. 独立 OOD 复制；
10. 结论不依赖单一模型规格。

不满足时，系统必须自动把措辞降级。

## 22.5 初始种子假设

以下仅是供系统检验的种子，不是既定事实：

- `H-SEED-001`：蛋白冠功能模块在材料理化属性与摄取之间提供可迁移的增量中介信息；
- `H-SEED-002`：控制离心、洗涤、血清比例和孵育时间后，某些表面电荷或粒径的经典效应显著减弱或方向改变；
- `H-SEED-003`：早期软冠功能轴比终点硬冠丰度更能预测后续细胞相互作用；
- `H-SEED-004`：人和鼠血浆之间存在可学习、带不确定性的材料排序映射，而非统一线性比例；
- `H-SEED-005`：以低补体/低凝血功能轴和目标摄取轴共同约束，比直接优化单一摄取分数产生更稳健的候选；
- `H-SEED-006`：实验协议变量解释的跨论文方差不低于一部分材料类别变量，忽略协议会造成虚假设计规律。

Codex 必须允许所有种子被否定，并主动寻找反例。

## 22.6 矛盾图

构建：

```text
nodes: normalized scientific claims
edges: supports / contradicts / refines / incomparable
```

每个矛盾对要比较：

- 材料是否同类；
- 生物流体和物种；
- 剂量和时间；
- 冠分离协议；
- 终点定义；
- 统计单位；
- 证据等级。

目标不是让 LLM“解释矛盾”，而是生成可计算的异质性假设并验证。

---

# 23. 可迁移科学规律与符号建模

## 23.1 规律发现的四条并行路线

1. **功能轴发现**：从高维蛋白冠组成中寻找低维、可解释功能轴；
2. **层级效应分解**：量化材料、环境、协议、study 和 assay 的贡献；
3. **符号规律发现**：在单位与物理约束下寻找简洁方程；
4. **跨域不变量**：识别在实验室、物种和材料家族变化下保持的关系。

## 23.2 组成数据变换

蛋白冠是组成数据，禁止直接对原始百分比使用普通欧氏模型作为唯一分析。

对组成 \(x=(x_1,\dots,x_D)\)：

\[
\operatorname{clr}(x)_i=
\log\frac{x_i+\epsilon}{g(x+\epsilon)}
\]

其中 \(g\) 为几何均值。主分析优先使用：

- ILR balances；
- logistic-normal；
- Dirichlet-multinomial/Dirichlet regression；
- zero-aware Bayesian replacement；
- 功能模块聚合后的 log-ratio。

所有伪计数策略必须在敏感性分析中比较。

## 23.3 功能轴发现

并行实现：

- NMF；
- sparse PCA；
- PLS/CCA；
- supervised sparse log-ratio；
- graph-regularized factorization；
- multi-study factor analysis；
- 稳定选择。

功能轴只有满足以下条件才进入论文：

1. bootstrap 对齐后的载荷稳定；
2. 至少三个独立 study 中出现；
3. 不由单一高丰度蛋白决定；
4. GO/Reactome 富集在多种背景下稳定；
5. 对 OOD 结局有增量预测；
6. 随机同尺寸蛋白集不能达到同等结果。

## 23.4 方差分解

层级模型：

\[
y_{ijkl}=
\mu+
\alpha_i^{material}+
\beta_j^{bioenv}+
\gamma_k^{protocol}+
\delta_l^{study}+
\epsilon_{ijkl}
\]

报告 posterior/variance partition：

\[
\mathrm{VPC}_q=
\frac{\sigma_q^2}{\sum_r\sigma_r^2+\sigma_\epsilon^2}
\]

不得将 study effect 简单当噪声删除；它是检验可迁移性的关键量。

## 23.5 跨域不变量

候选关系 \(f\) 需要在环境 \(e\) 中满足：

\[
\min_f \sum_e R_e(f)
+\lambda\operatorname{Var}_e[R_e(f)]
+\rho\Omega(f)
\]

环境至少包括：

- study/lab；
- material family；
- species；
- biofluid；
- protocol cluster；
- publication era。

比较 ERM、group DRO、IRM 类惩罚、domain adversarial 和 hierarchical partial pooling。若复杂不变学习不优于层级统计基线，则保留简单模型。

## 23.6 符号回归

目标是得到可解释、可验证而非仅拟合好的方程。

候选变量包括：

- size、PDI、zeta、shape descriptors；
- ligand/PEG density；
- hydrophobicity proxies；
- serum concentration；
- incubation time；
- functional balances；
- protocol severity；
- dose；
- species/biofluid embeddings 的受限低维项。

流程：

1. 由单位系统生成允许的变量组合；
2. 构建无量纲或同量纲候选；
3. 在 train 内做 study-grouped nested CV；
4. 使用复杂度惩罚的 symbolic regression；
5. bootstrap 重复并对表达式规范化；
6. 统计表达式结构和系数稳定性；
7. 在 validation、leave-family-out 和 lockbox 上检验；
8. 与 GAM、spline、tree ensemble 和神经网络比较；
9. 对每个项做删项和反例测试。

目标函数示例：

\[
J(f)=
\operatorname{OODLoss}(f)
+\lambda_1\operatorname{Complexity}(f)
+\lambda_2\operatorname{Instability}(f)
+\lambda_3\operatorname{UnitViolation}(f)
\]

可使用 PySR 作为可选实现，同时提供不依赖 Julia 的简单遗传/枚举回退。任何软件包不可用时不能使整个项目停止。

## 23.7 规律稳定性门槛

一条规律至少满足：

- 在生成域以外的两个域复制；
- study-clustered bootstrap 至少 80% 同方向；
- 留一研究后不由单个研究决定；
- 去除最低证据等级后仍成立；
- 图像数字化误差传播后仍成立；
- 多种合理归一化后方向一致；
- 负对照无同等效应；
- 明确适用域和失败域；
- 公式或功能轴足够简单，可由第三方复算。

## 23.8 人—鼠与生物流体迁移

建立带不确定性的映射：

\[
C^{human}=
T_\phi(C^{mouse},M,P)+\epsilon
\]

比较：

- 直接相关；
- ortholog 聚合后线性映射；
- 功能模块映射；
- optimal transport；
- conditional flow；
- hierarchical multi-task model。

主指标应是材料排序和校准，而不只是蛋白级相关系数。缺少真正配对材料时，不得声称个体级翻译，只能报告群体级迁移能力。

---

# 24. 受约束反向设计

## 24.1 设计对象

首版支持三种对象：

### 脂质/脂质体配方

```text
component identities
molar fractions summing to 1
ionizable lipid descriptors
helper lipid
cholesterol fraction
PEG-lipid identity and fraction
N/P ratio when available
size/PDI/zeta target window
```

### 聚合物纳米颗粒/胶束

```text
repeat unit or monomer graph
block architecture
molecular-weight range
block ratio
functional groups
surface ligand
ligand density
formulation descriptors
```

### 表面物理身份

```text
core family
size
shape
surface charge
hydrophobicity proxy
roughness/curvature proxy
coating chemistry
ligand/PEG density
```

## 24.2 设计目标

多目标效用：

\[
U(m)=
+w_u\hat Y_{uptake}(m)
+w_b\hat Y_{target}(m)
-w_t\hat Y_{tox}(m)
-w_c\hat Y_{complement}(m)
-w_g\hat Y_{coag}(m)
-w_o U_{epistemic}(m)
-w_a D_{OOD}(m)
-w_s C_{synthesis}(m)
\]

必须同时输出 Pareto 前沿，禁止用任意权重隐藏安全性权衡。

## 24.3 硬约束

- 配比非负且和为 1；
- 结构可解析；
- 重复单元或脂质组件存在公开结构证据；
- 描述符在模型适用域或明确标注外推；
- 不产生与训练项完全重复的“新候选”；
- 不以无法公开验证的商业配方为主要结果；
- 不把计算候选称为已合成或已验证；
- 高毒性、高补体或高凝血预测超过阈值时自动淘汰；
- 不确定性超过阈值时进入 `ABSTAIN`。

## 24.4 模型递进

### D0：枚举与规则过滤

从公开组件和观测范围内生成合法组合，验证约束系统。

### D1：多目标 Bayesian optimization / NSGA-II

先在可靠 surrogate 上工作。优先证明多目标、适用域和不确定性流程正确。

### D2：潜空间优化

在预训练材料编码空间进行梯度或进化优化，解码后执行合法性投影。

### D3：条件扩散或流匹配

只有在：

- 训练样本规模足够；
- D1/D2 基线稳定；
- 结构有效率达标；
- OOD surrogate 校准达标；

之后才实现。不得为了“最火模型”跳过数据充分性检查。

## 24.5 目标生物身份反演

旗舰设计路线：

\[
Y^*
\rightarrow
C^*_{functional}
\rightarrow
M^*
\]

第一步寻找达到目标结局的蛋白功能轴区域；第二步求解能诱导该轴且满足安全约束的材料。比较：

- 直接 \(M\rightarrow Y\) 优化；
- 中介约束优化；
- 中介与直接路径联合优化。

若中介约束候选在 OOD 下更稳定，构成方法与科学贡献。

## 24.6 候选审计包

每个候选生成：

```text
candidate_id
machine-readable composition/structure
nearest observed neighbors
novelty distances
predicted corona functional profile
predicted outcomes
aleatoric and epistemic uncertainty
applicability-domain status
constraint checks
counterfactual rationale
supporting training evidence
known failure modes
reproduction command
```

最终论文候选不按单一最高分选择，而按：

- Pareto 代表性；
- 低不确定性；
- 非平凡新颖性；
- 跨模型一致性；
- 机制可解释性；
- 对协议和环境扰动的稳健性。

## 24.7 无湿实验条件下的验证边界

只能声称：

- computationally proposed；
- predicted under the declared applicability domain；
- retrospectively or temporally supported by public evidence；
- robust across model and domain perturbations。

不得声称：

- synthesizable in practice，除非仅表示通过公开规则筛选；
- safe；
- clinically effective；
- experimentally validated；
- ready for translation。

---

# 25. 4×A100、1.5 TB 与 Slurm 执行规范

## 25.1 资源原则

- CPU 执行检索、下载、解析、表格抽取、标准化和多数统计模型；
- GPU 只用于确实有收益的视觉/语言模型、多模态编码和深度世界模型；
- 先跑 toy、1-study 和 10% 数据 smoke test，再提交完整任务；
- 不用 4 张 A100 训练可由单卡完成的基线；
- 原始组学和 PDF 不永久复制多份；
- 任何运行超过预算先通过 dry-run 估计；
- 每个 Slurm 作业写出 config、commit、输入哈希和结果目录。

## 25.2 资源配置文件

创建：

```text
configs/resources/local.yaml
configs/resources/slurm_cpu.yaml
configs/resources/slurm_gpu1.yaml
configs/resources/slurm_gpu4.yaml
```

至少定义：

```yaml
cpus: 8
memory_gb: 64
gpus: 0
scratch_gb: 50
walltime: "04:00:00"
partition: null
account: null
```

不得在仓库中硬编码 KAUST 账户或项目组名称；通过环境变量或本地非版本配置提供。

## 25.3 Slurm CPU 模板

```bash
#!/usr/bin/env bash
#SBATCH --job-name=bioif_cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --output=logs/slurm/%x-%j.out
#SBATCH --error=logs/slurm/%x-%j.err

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
source .venv/bin/activate
export PYTHONHASHSEED=0
biointerfaceos "$@"
```

## 25.4 单 GPU 模板

```bash
#!/usr/bin/env bash
#SBATCH --job-name=bioif_gpu1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=128G
#SBATCH --gres=gpu:a100:1
#SBATCH --time=24:00:00
#SBATCH --output=logs/slurm/%x-%j.out
#SBATCH --error=logs/slurm/%x-%j.err

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
source .venv/bin/activate
export PYTHONHASHSEED=0
export TOKENIZERS_PARALLELISM=false
nvidia-smi
biointerfaceos "$@"
```

GPU 资源字符串在不同集群可能不同，Codex 必须通过 `sinfo`/已有模板检测并写入本地配置，而不是猜测。

## 25.5 四 GPU 模板

```bash
#!/usr/bin/env bash
#SBATCH --job-name=bioif_gpu4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=384G
#SBATCH --gres=gpu:a100:4
#SBATCH --time=48:00:00
#SBATCH --output=logs/slurm/%x-%j.out
#SBATCH --error=logs/slurm/%x-%j.err

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
source .venv/bin/activate
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK}"
torchrun --standalone --nproc_per_node=4 -m biointerfaceos.cli "$@"
```

## 25.6 作业依赖

数据流水线优先使用 Snakemake 或等价 DAG，模型扫描使用 job array。示例：

```bash
jid_data=$(sbatch --parsable slurm/cpu.sh data build-silver)
jid_split=$(sbatch --parsable --dependency=afterok:${jid_data} slurm/cpu.sh split freeze-dev)
sbatch --dependency=afterok:${jid_split} --array=0-19 slurm/gpu1.sh train sweep --index '${SLURM_ARRAY_TASK_ID}'
```

任何下游任务不得在上游退出码非零时运行。

## 25.7 存储配额

默认 1.5 TB 预算建议：

| 层 | 软上限 |
|---|---:|
| registry/metadata/JATS | 30 GB |
| supplements/PDF/image cache | 180 GB |
| PRIDE raw/transient | 650 GB |
| processed omics | 180 GB |
| analytical parquet/features | 120 GB |
| checkpoints | 180 GB |
| runs/logs/reports | 80 GB |
| safety reserve | 80 GB |

`biointerfaceos storage audit` 必须：

- 输出目录用量；
- 找出重复哈希；
- 标记可再生成文件；
- 超软上限时拒绝新大文件；
- 永不自动删除 raw；
- 只在 manifest 证明可重新下载且校验哈希存在时清理 transient。

## 25.8 断点续传和失败恢复

大文件下载必须：

- `.part` 临时文件；
- Range/FTP resume；
- checksum；
- 原子 rename；
- 指数退避；
- 失败资产单独重试；
- 下载状态写 manifest。

训练必须：

- 周期性 checkpoint；
- optimizer/scheduler/RNG 状态保存；
- resume 测试；
- 最佳模型与最后模型分开；
- 中断不改变 split 和随机种子。

## 25.9 计算预算门禁

每个完整模型运行前生成：

```text
estimated_gpu_hours
estimated_cpu_hours
estimated_peak_memory
estimated_storage_delta
number_of_trials
expected_information_gain
```

若复杂模型预计成本超过最佳基线十倍，但没有明确可检验的新能力，只保留为小规模消融，不进入全面搜索。

---

# 26. Codex 任务 DAG 与逐步执行法

## 26.1 `TASKS.tsv` 是唯一任务状态源

字段定义：

```text
id
phase
title
depends_on
status
priority
inputs
outputs
command
acceptance
failure_policy
```

状态：

```text
READY
BLOCKED
IN_PROGRESS
DONE
FAILED_RETRYABLE
FAILED_FINAL
WAIVED
```

规则：

- `depends_on` 中所有任务为 `DONE` 或 `WAIVED` 才可执行；
- Codex 每次只把一个主任务设为 `IN_PROGRESS`；
- 任务完成后必须逐字运行 `command` 和对应测试；
- `acceptance` 未全部满足不得改为 `DONE`；
- 失败不得删除任务，只能记录失败和回退；
- 任务含科学决策时创建独立 ExecPlan；
- 任务含数据冻结、解锁或发布时必须二次审计。

## 26.2 Phase 0：仓库与状态系统（T000–T015）

目标：在任何真实数据进入前，先建立可重启、可审计、可测试的工程骨架。

结束时必须可以：

```bash
make bootstrap
make check
biointerfaceos doctor
biointerfaceos state next
biointerfaceos storage audit
```

并观察：

- CLI 正常；
- schema 可验证；
- ledgers 可追加不可覆盖；
- lockbox 目录默认不可由开发命令读取；
- CI 在无网络的小样本上通过。

## 26.3 Phase 1：来源准入与官方适配器（T016–T025）

目标：完成 Europe PMC、PMC OA、PRIDE、GEO、PubChem、ChEMBL 和基础本体的匿名访问适配器。

每个适配器都要有：

- 官方入口；
- 速率限制；
- timeout/retry；
- pagination；
- ETag/Last-Modified 或内容哈希；
- 许可字段；
- mock fixture；
- 集成测试；
- 失败时不影响其他来源。

## 26.4 Phase 2：系统检索（T026–T030）

目标：生成可复现候选文献宇宙，而不是手工挑选论文。

结束产物：

```text
registry/search_queries.parquet
registry/search_runs.parquet
registry/paper_families.parquet
reports/search_saturation.html
reports/coverage_by_year_material_endpoint.html
```

饱和分析至少按：年份、材料、终点、数据类型和引用层级分层。

## 26.5 Phase 3：多模态摄取与抽取（T031–T051）

目标：把准入资产转为带证据定位的 Bronze/Silver/Gold-auto 数据。

强制顺序：

```text
structured XML/table/source-data
→ supplementary spreadsheet
→ text extraction
→ PDF fallback
→ figure digitization only when necessary
```

完成条件：抽取 benchmark、证据追踪、单位和实体测试均达门槛；不能只看抽取了多少篇。

## 26.6 Phase 4：公开原始组学（T052–T062）

目标：统一重处理公开 PRIDE 项目，并将 GEO/SRA 作为细胞状态支持模块。

PRIDE 优先级：

1. 明确有 material arm、biofluid、replicate 和 corona 定量；
2. 能与摄取/富集终点连接；
3. 原始文件和搜索结果均公开；
4. 训练/验证时期优先，锁定时期只编目元数据。

完成后要证明从原始文件到 protein × sample 矩阵可复现。

## 26.7 Phase 5：切分与防泄漏（T063–T066）

目标：先冻结开发切分和模型选择规则，再建 benchmark。

必须通过：

- DOI/PMCID/PXD/GSE/paper family grouping；
- formulation near-duplicate grouping；
- lab/study isolation；
- feature blacklist；
- date provenance；
- lockbox access test；
- adversarial leakage baseline。

## 26.8 Phase 6：BioInterfaceBench（T067–T070）

目标：构造实例、grader 和简单基线，证明任务可运行。

每个实例包括：

```text
instance_id
public inputs
hidden targets
split/group keys
evidence provenance
metric config
abstention policy
```

发布版不得带隐藏锁定标签。

## 26.9 Phase 7：统计与机器学习基线（T071–T079）

顺序不可颠倒：

```text
mixed effects
→ direct black box
→ static mediator
→ compositional mediator
→ dynamics
→ causal hierarchy
→ invariance
→ uncertainty
→ multimodal
```

每一步必须证明新模块在主要 OOD 指标上增加能力，否则停止扩展。

## 26.10 Phase 8：科研 Agent（T080–T088）

目标：让 Agent 完成可执行科研任务，并与单 Agent、无工具、规则系统比较。

不得只展示一个成功案例；必须报告任务全集的成功、失败、成本、证据率和复现率。

## 26.11 Phase 9：规律发现（T089–T095）

目标：通过预注册假设、功能轴、层级中介、跨物种映射和符号回归形成科学结论。

每个候选规律先进入 `CLAIM_LEDGER`，再经过：

```text
association → mechanism → causal → lockbox
```

逐级门禁。

## 26.12 Phase 10：反向设计（T096–T098）

先完成可审计的多目标基线，再做生成模型。输出只能称为计算候选。

## 26.13 Phase 11：全套稳健性（T099–T102）

包括：

- 模块消融；
- study/material/species/time OOD；
- 发表偏倚；
- 数字化误差传播；
- 缺失机制；
- 多种归一化；
- 负对照；
- 故意泄漏攻击。

## 26.14 Phase 12：开发冻结与一次性锁定评测（T103–T110）

在 T108 之前：

- 只可保存锁定时期候选的 accession、日期、许可和文件大小；
- 禁止正文、摘要语义嵌入、补充表、原始数据标签进入开发环境；
- 测试资产放在独立路径和权限组；
- 所有开发结果、阈值、图定义和 claim 预先冻结。

T109 只能运行一次主评测。代码错误导致运行失败时：

- 保留失败日志；
- 只允许修复与模型选择无关的机械错误；
- 由审计脚本证明输出定义未变；
- 新运行标记为 `LOCKBOX_RERUN_TECHNICAL`，不能冒充首次运行。

## 26.15 Phase 13：论文与发布（T111–T114）

最终完成：

- 数据卡；
- 模型卡；
- benchmark card；
- Agent card；
- license inventory；
- claim-to-evidence matrix；
- reproduction receipts；
- 三篇论文草稿；
- 匿名审稿包；
- 公共发布包和仅分析层分离。

---

# 27. 项目门禁、验收阈值与转向条件

## G0：工程可运行

通过条件：

- 干净环境安装成功；
- `make check` 全通过；
- CLI、manifest、ledger、CAS 和 release hash 正常；
- 所有网络适配器有 mock 测试；
- 状态可从中断恢复。

## G1：数据许可与溯源

通过条件：

- 100% 资产有 source URL/accession、retrieval time、hash、license status；
- 100% 模型输入可追踪到 evidence；
- 未决许可资产与发布层物理隔离；
- 受限源拒绝测试通过；
- 抽查不存在付费墙绕过或凭据依赖。

## G2：抽取质量

最低门槛：

- 关键数值字段 precision ≥ 0.95；
- 关键数值字段 recall ≥ 0.85；
- 单位规范化准确率 ≥ 0.98；
- 材料 arm 匹配 F1 ≥ 0.90；
- evidence-location resolution ≥ 0.98；
- 表格 cell 到 experiment 映射 F1 ≥ 0.90；
- 图像数字化抽样的归一化误差中位数 ≤ 5%，90 分位 ≤ 12%；
- 自动冲突发现 recall 在注入测试中 ≥ 0.90。

阈值不足时不得用自动抽取数据做主要科学结论，只能扩大审计或收窄字段。

## G3：数据充分性

采用“科学问题所需有效样本”而非单纯论文数。

主链最低要求：

- 至少 150 个独立 study/paper families 被结构化；
- 至少 1,000 个材料—环境—协议实验单元；
- 至少 500 个有 corona 定量的独立 sample/arm；
- 至少 250 个可连接 corona 与下游结局的匹配单元；
- 至少 10 个独立实验室；
- 至少 3 个主材料家族；
- 至少 2 个物种/生物流体域用于迁移评估。

这些是目标门槛，不得通过伪重复达到。若配对中介单元少于 150 或来自少于 8 个独立研究：

- 禁止强因果中介结论；
- 转为“动态冠预测＋关联机制＋benchmark”主线；
- 保留中介模型为探索性。

若动态时间序列少于 100 条轨迹或少于 5 个研究：

- 不训练高容量 Neural ODE；
- 使用层级动力学或离散早/晚状态；
- 将“动态世界模型”降级为次要结果。

## G4：原始组学重处理

通过条件：

- 至少 3 个开发时期 PRIDE 项目可从 raw/search files 重建；
- 每个项目 sample mapping、replicate 和 material arm 可审计；
- FDR/定量/QC 统一；
- 至少 2 个项目与作者处理结果有合理一致性；
- 差异有技术解释；
- 失败 raw 项目保留并报告，不被静默删除。

## G5：切分与锁定

通过条件：

- 近重复跨 split 数量为 0；
- 同一 paper family 跨 split 数量为 0；
- 明确 study/lab 泄漏为 0；
- feature blacklist 测试通过；
- study-only adversary 在真正 OOD 不能产生异常高分；
- lockbox 读取测试在冻结前必须失败；
- 开发 release hash 已签名保存。

## G6：预测模型

进入主要结果的最低条件：

- 至少两个主要 OOD split 上优于预先指定的最佳简单基线；
- study-clustered bootstrap 的差值区间支持改善；
- 校准误差不恶化；
- 在高不确定性样本拒绝后风险单调下降；
- 去掉最大研究后结论不反转；
- 无锁定污染；
- 模型复杂度与科学能力增益匹配。

若深度模型不满足，保留层级统计/树模型为主模型，并诚实报告负结果。

## G7：科学规律

至少形成三条候选规律，其中至少一条满足：

- 在两个未参与生成的域复制；
- 在 2025–2026 lockbox 中方向和主要效应成立；
- 统一原始组学提供机制支持；
- 不能由协议、study 或发表偏倚解释；
- 可用简洁方程或稳定功能轴表达；
- 明确适用域与反例。

若没有 lockbox 复制，不冲击以“普适规律”为核心的高层级期刊，转投 benchmark/method/negative result 路线。

## G8：Agent 科学能力

通过条件：

- 端到端任务完成率显著高于单 Agent 与无工具基线；
- 证据引用正确率 ≥ 0.95；
- schema-valid rate ≥ 0.98；
- 成功任务复现率 ≥ 0.90；
- 锁定污染率 = 0；
- 受限来源拒绝 recall ≥ 0.99；
- 报告所有失败类别和成本；
- Agent 发现至少一个由固定自动流程独立验证的非平凡假设。

## G9：反向设计

通过条件：

- 结构/配方硬约束有效率 ≥ 0.98；
- 去重后有非平凡候选；
- 候选在 ensemble 和扰动下排序稳定；
- 适用域内候选与外推候选明确分开；
- 多目标 Pareto 优于观测基线的结论有不确定性区间；
- 不使用湿实验措辞；
- 至少有公开时间后验材料作为 retrospective temporal validation，或明确报告没有。

## G10：可复现发布

通过条件：

- 干净容器可重建主要表图；
- 公共数据包不含许可受限内容；
- 所有主文数字由命令生成；
- claim-to-evidence matrix 100% 完整；
- locked first-run receipt 保存；
- 论文、代码、数据卡、模型卡和 benchmark card 一致；
- 三次不同机器/节点复跑主要结果在声明容差内。

## 27.1 Kill / Pivot Criteria

项目不得因“必须冲 Nature”而掩盖负结果。触发后按下表转向：

| 触发 | 禁止继续声称 | 合理转向 |
|---|---|---|
| 配对 M→C→Y 数据不足 | 强中介/因果规律 | 多模态数据基准与 corona 预测 |
| 深度模型 OOD 不优于统计基线 | 世界模型性能突破 | 层级统计规律与负结果 |
| 协议效应压倒材料效应 | 普适材料规律 | 协议标准化、测量偏差和 benchmark |
| lockbox 失败 | 前瞻性成功 | 失败分析、边界条件和校准研究 |
| 反向设计全在 OOD | 可行候选 | 适用域与拒绝学习方法 |
| Agent 只提高写作不提高科研正确率 | 自动科学发现 | 科研 Agent 评测与失败图谱 |
| 许可无法支持发布 | 开放训练数据集 | manifest、代码和可重建索引 |

每次转向需要写 `reports/PIVOT_<date>.md`，包含证据、影响、保留产物和新门禁。

---

# 28. 论文图表、发布物与结果组织

## 28.1 Paper A 图表

### Figure A1：数据宇宙与溯源

- 检索—许可—摄取—抽取—审计流程；
- 论文、补充、图像、PRIDE、GEO 数量；
- 证据等级和许可分层；
- 不声称“全网穷尽”。

### Figure A2：数据覆盖

- 年份 × 材料 × 终点；
- lab/study/biofluid/species；
- 缺失矩阵；
- 训练/验证/锁定分布。

### Figure A3：抽取基准

- 规则、文本 Agent、表格 Agent、视觉 Agent、融合；
- precision/recall/evidence resolution；
- 错误分类。

### Figure A4：BioInterfaceBench

- 任务族；
- OOD 切分；
- grader；
- Agent 完成率和成本。

## 28.2 Paper B 图表

### Figure B1：因果世界模型

材料—环境—协议—动态冠—状态—结局；显示随机效应和不确定性。

### Figure B2：模型递进

M1–M8 的 ID/OOD、校准、拒绝曲线与复杂度。

### Figure B3：动态冠

预测轨迹、功能轴、soft/hard exchange、toy recovery 和真实项目验证。

### Figure B4：中介与跨域

直接效应、间接效应、敏感性、人—鼠迁移。

### Figure B5：Agent 科研闭环

假设锦标赛、实验树、反证和复现；展示成功与失败。

### Figure B6：反向设计

Pareto 前沿、目标冠反演、适用域和候选审计。

## 28.3 Paper C 图表

### Figure C1：跨研究变异的来源

材料、环境、协议、study 和 assay 的方差分解。

### Figure C2：稳定功能轴

蛋白载荷、功能富集、跨域稳定性和下游关联。

### Figure C3：协议校正后的规律

经典粗相关与校正后的效应；展示反转或边界条件。

### Figure C4：可解析规律

符号公式、复杂度—误差 Pareto、外部复制和失败域。

### Figure C5：时间盲测

冻结前预测、锁定结果、校准与错误案例。

### Figure C6：可计算设计原则

目标生物身份到材料变量的设计图谱，不将候选称为实验验证。

## 28.4 强制表格

- Data sources and licenses；
- Cohort/study characteristics；
- Extraction benchmark；
- OOD split definitions；
- Baseline comparison；
- Ablations；
- Robustness and negative controls；
- Claim gate matrix；
- Candidate design audit；
- Reproducibility matrix。

## 28.5 发布目录

```text
release/
├── public/
│   ├── manifests/
│   ├── schemas/
│   ├── redistributable_data/
│   ├── benchmark/
│   ├── graders/
│   ├── model_cards/
│   └── reproduction/
├── analysis_only/
│   ├── rebuild_instructions/
│   └── source_pointers/
├── manuscripts/
│   ├── paper_a/
│   ├── paper_b/
│   └── paper_c/
└── checksums.txt
```

## 28.6 每个主文结论的最小发布对象

```text
claim_id
manuscript sentence
figure/table cell
analysis command
config hash
data release hash
model/run ids
supporting evidence ids
contradicting evidence ids
claim gate result
allowed wording
```

---

# 29. 第一次启动 Codex 的精确步骤

## 29.1 在目标存储建立仓库

```bash
mkdir -p /path/to/BioInterfaceOS
cd /path/to/BioInterfaceOS
cp -a /path/to/BioInterfaceOS_Codex_Execution_Pack/. .
git init
git add AGENTS.md GOAL.md PLANS.md PROJECT_STATE.yaml TASKS.tsv CODEX_START_PROMPT.md
git commit -m "chore: initialize BioInterfaceOS execution contract"
```

用户应把 `/path/to/BioInterfaceOS` 替换成实际可写目录。不得让 Codex猜测集群项目盘路径后写到系统目录。

## 29.2 交互式启动

```bash
cd /path/to/BioInterfaceOS
codex
```

然后粘贴 `CODEX_START_PROMPT.md` 全文。

## 29.3 非交互、仓库内自动执行

推荐在受控项目目录和 sandbox 中运行：

```bash
cd /path/to/BioInterfaceOS
codex exec \
  --sandbox workspace-write \
  --ask-for-approval never \
  "$(cat CODEX_START_PROMPT.md)"
```

网络是否允许由本机 Codex sandbox 配置决定。不要使用 `--yolo` 或关闭 sandbox。对于需要公共网络下载的任务，可在经过审阅的项目配置中启用 workspace 网络访问；文件写入仍限制在仓库和显式数据根。

## 29.4 每次新会话继续

同一启动命令可重复使用。Codex 必须从：

```text
PROJECT_STATE.yaml
TASKS.tsv
reports/task_ledger.jsonl
docs/execplans/
```

恢复，而不是依赖上一次聊天上下文。

可使用更短的恢复提示：

```text
Read AGENTS.md and all project state files. Resume the first dependency-satisfied incomplete task, maintain its ExecPlan, pass acceptance checks, update ledgers and continue.
```

## 29.5 首轮人工只检查三件事

Codex 完成 T000–T015 后，用户只需查看：

```bash
make check
biointerfaceos doctor
biointerfaceos state summary
```

不应在基础设施通过前就启动大规模下载或 GPU 训练。

## 29.6 推荐的权限边界

- 仓库：可写；
- 单独的数据根：通过明确 `--add-dir` 或绑定挂载可写；
- 其他主目录：只读或不可见；
- SSH key、浏览器 Cookie、系统凭据目录：不可见；
- 删除操作：只允许项目内 transient，并经过 manifest 检查；
- 网络：只访问 registry 中准入的公共域名；
- 锁定测试根：冻结前对开发 Agent 不可读。

---

# 30. 顶会/顶刊方法复现与借鉴清单

## 30.1 复现不是拼装

对每个参考项目执行：

1. 记录论文、官方仓库、commit、许可和依赖；
2. 在其原始小数据或官方示例上复现；
3. 写 `docs/reproductions/<name>.md`；
4. 说明移植的抽象思想，而非直接复制全部框架；
5. 用 BioInterfaceBench 小任务验证增益；
6. 没有增益则停止移植；
7. 遵守原代码许可和署名。

## 30.2 必学参考

### ScienceAgentBench

借鉴：论文衍生真实数据任务、可执行代码评测、端到端科研能力，而不是问答分数。

交付：

- 复现至少一个公开任务；
- 将 grader 抽象映射到 BioInterfaceBench；
- 比较无工具、工具 Agent 和多 Agent。

### AstaBench / Asta Agent

借鉴：大规模科研任务分类、可组合工具使用、研究 Agent 基线和可执行评测。

交付：

- 任务 taxonomy 对照表；
- 失败类型对照；
- 在本项目任务上复现统一评测格式。

### AI Scientist-v2

借鉴：实验管理、循环改进、报告生成和自动复现；不得继承其可能产生不可靠科学结论的部分作为真值。

### MatterGen

借鉴：条件生成、多目标引导、有效性过滤、材料候选评测。不得把晶体生成假设直接套到脂质或聚合物配方。

### FlowMM

借鉴：流匹配、条件生成和几何/约束处理。需重新定义医学材料设计空间。

### TransPolymer

借鉴：聚合物序列/重复单元预训练表示和性质迁移。

### PolyIE

借鉴：聚合物论文实体关系抽取、材料命名和标注设计。

### OMG / PI1M 类公开聚合物空间

借鉴：公开聚合物结构先验、去重、表示预训练和候选新颖性比较。只有匿名可下载且许可清楚的数据版本可进入项目。

## 30.3 复现验收卡

```yaml
name: reference_name
paper: ...
official_repo: ...
commit: ...
license: ...
original_task_reproduced: true|false
expected_metric: ...
observed_metric: ...
tolerance: ...
minimal_component_to_reuse: ...
new_project_task: ...
measured_gain: ...
decision: ADOPT|ADAPT|REJECT
```

不允许因为方法来自顶会就默认采用。

---

# 31. 初始数据种子与锁定规则

## 31.1 PRIDE 种子

以下只作为启动 discovery 的 accession，最终日期、许可、文件和 split 必须由官方元数据适配器确认：

| Accession | 初始用途 | 开发可见性 |
|---|---|---|
| PXD017776 | 脂质体组成—人血清冠—摄取种子 | 可进入训练候选 |
| PXD033976 | 软/硬冠和动态演化种子 | 可进入训练候选 |
| PXD054751 | LNP/DNA/蛋白冠候选 | 先按官方日期决定 train/validation |
| PXD057444 | 聚合物胶束/LNP 与靶向候选 | 若日期落入 lockbox，只保留元数据 |
| PXD063915 | 纳米粒—鼠血浆冠—体内/肿瘤关联候选 | 锁定候选，只编目元数据 |

不得依据本手册的文字替代官方 metadata。`public_date`、`announce_date`、关联论文 online date 和文件时间全部保存；split 采用预先定义的主日期规则并做敏感性分析。

## 31.2 文献种子

第一轮查询围绕：

```text
("protein corona" OR "biomolecular corona")
AND
(liposome OR "lipid nanoparticle" OR polymeric nanoparticle OR micelle)
AND
(uptake OR biodistribution OR complement OR coagulation OR toxicity)
```

再按材料、环境和结局拆分，禁止只用一条超长查询。

## 31.3 锁定候选的元数据白名单

冻结前仅允许：

```text
accession
DOI/PMCID
public/announce date
title only when needed for scope triage
license status
repository
file count
file sizes
checksums
high-level controlled keywords
```

禁止：

```text
abstract embeddings
full text
supplementary values
figure data
sample labels
protein matrices
outcome labels
paper conclusions
```

如果 title 本身泄露目标排序或关键结论，将 title 哈希化并由独立 curator 只返回 eligibility flag。

---

# 32. 数据和实验版本规范

## 32.1 版本 ID

```text
data_release_id = bioif-data-YYYYMMDD-<gitshort>-<manifesthash8>
benchmark_id    = bioif-bench-vMAJOR.MINOR.PATCH
model_id        = <family>-<config_hash8>-<seed>-<data_release_id>
run_id          = <UTC timestamp>-<task>-<config_hash8>
claim_id        = BIOIF-CLAIM-000001
```

## 32.2 不可变发布

一旦 `release freeze`：

- 目录只读；
- manifest 和 checksums 保存；
- 修复生成新版本；
- 论文图表引用固定 release ID；
- 不允许同名覆盖。

## 32.3 结果容差

对确定性处理：字节级或表级哈希一致。

对随机模型：

- 固定种子结果在声明数值容差内；
- 多种子聚合以统计区间复现；
- GPU 非确定性操作被登记；
- 主要结论不能依赖一个幸运种子。

---

# 33. 风险登记表

至少维护以下风险：

| 风险 | 早期信号 | 缓解 | 转向 |
|---|---|---|---|
| 公共数据规模不足 | 配对单元长期不足 | 扩大引用追踪、提取 source data、收窄问题 | benchmark/动态冠 |
| 许可不清 | 大量 quarantine | 仅发布 manifest 和重建脚本 | 分层发布 |
| PDF/图表误差 | 审计误差高 | 提高结构化源优先级、人工共识包 | 排除关键图像字段 |
| study effect 过强 | OOD 崩溃 | 层级模型、协议建模 | 协议标准化论文 |
| 锁定数据污染 | 文件/embedding 命中 | 权限隔离、哈希扫描 | 重建全新锁定集 |
| 原始质谱异质 | 搜索失败、样本映射不清 | 项目级适配器、processed fallback | 少项目深分析 |
| Agent 幻觉 | 证据解析失败 | schema、工具证据、规则复核 | Agent 仅生成候选 |
| 计算失控 | sweep 暴涨 | 预算门禁、Successive Halving | 简化模型 |
| 结果不新颖 | 仅性能小提升 | 规律发现、矛盾与边界 | 顶会 benchmark |
| 因果识别不足 | overlap/混杂失败 | 降级措辞、敏感性 | 关联机制 |

风险每个 release 更新，不得只在项目末尾补写。

---

# 34. 项目最终完成定义

只有同时满足以下条件才能把项目状态改为 `COMPLETE`：

1. T000–T114 的 mandatory 任务均为 `DONE` 或有审计通过的 `WAIVED`；
2. 所有数据来自匿名、无需申请注册的准入源；
3. 数据和数字有完整 evidence lineage；
4. 主要模型在预设 OOD 和校准门禁下有效，或负结果被完整报告；
5. 至少三条科学规律通过相应层级门禁，或明确转向 benchmark/method 主线；
6. Agent 评测覆盖成功和失败，不以演示代替统计；
7. lockbox 只按预注册流程解锁并保留 first-run receipt；
8. 无湿实验措辞不越界；
9. 公共 release 不含许可受限资产；
10. 第三方在干净环境能重建主要结果；
11. 三篇论文材料与代码、数据、图表、claim ledger 一致；
12. `reports/FINAL_AUDIT.md` 中没有未解释的 critical finding。

项目“完成”不等于论文一定接收。它表示研究问题、数据、方法、验证、审计和发布已经达到可独立送审的完整状态。

