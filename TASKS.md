# BioInterfaceOS Codex 逐任务目录（TASKS.md）

> 本文件由 `TASKS.tsv` 生成，供人阅读；状态修改以 `TASKS.tsv` 为准。每项任务必须满足验收条件才能标记为 DONE。

## Phase 0：仓库与状态系统

### T000 — Audit execution contract

**依赖**：无  
**优先级**：P0  
**初始状态**：READY

**输入**：AGENTS.md;GOAL.md;PLANS.md;PROJECT_STATE.yaml  
**输出**：reports/CONTRACT_AUDIT.md;validated task graph

**执行命令**：

```bash
python scripts/validate_execution_pack.py
```

**验收标准**：All required files exist; markdown headings parse; task IDs unique; dependencies resolve; no cyclic dependency; current state points to T000

**失败回退**：Repair only the execution pack; record every ambiguity in CONTRACT_AUDIT; do not start data work

### T001 — Initialize Git and protected project boundary

**依赖**：T000  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：audited execution pack  
**输出**：Git repository;.gitignore;.gitattributes;initial commit

**执行命令**：

```bash
git status --short && git log -1 --oneline
```

**验收标准**：Repository root is correct; initial contract committed; secrets, raw data, checkpoints and local configs ignored; no files outside root changed

**失败回退**：If Git identity is missing, create repository and staged diff, record exact commit command as a genuine blocker, then continue non-commit setup

### T002 — Create repository directory skeleton

**依赖**：T001  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：GOAL.md directory contract  
**输出**：src;tests;configs;schemas;registry;data;reports;docs;slurm;workflows;release directories

**执行命令**：

```bash
python scripts/bootstrap_repo.py --check
```

**验收标准**：All required directories and placeholder README files exist; paths remain inside project/data roots; rerun is idempotent

**失败回退**：Rollback only generated empty paths; fix script; never delete user files

### T003 — Create reproducible Python environment

**依赖**：T002  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：Python 3.11 requirement  
**输出**：pyproject.toml;uv.lock or pinned requirements;environment report

**执行命令**：

```bash
make env && python -m biointerfaceos --version
```

**验收标准**：Clean environment installs; dependency versions pinned; import smoke test passes; no undeclared system dependency for core CLI

**失败回退**：Use venv/pip fallback if uv unavailable; quarantine optional packages; core must install

### T004 — Implement CLI and doctor command

**依赖**：T003  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：package skeleton  
**输出**：src/biointerfaceos/cli.py;doctor report;CLI tests

**执行命令**：

```bash
biointerfaceos doctor --strict
```

**验收标准**：CLI exposes state, data, source, extract, split, benchmark, train, agent, claim, release, storage commands; doctor exits zero only when mandatory prerequisites pass

**失败回退**：Implement stubs only with explicit NOT_IMPLEMENTED exits; never report false success

### T005 — Add formatting typing tests and CI

**依赖**：T004  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：Python package  
**输出**：ruff;mypy;pytest configuration;CI workflow;Makefile

**执行命令**：

```bash
make check
```

**验收标准**：ruff check, format check, mypy and pytest pass on clean checkout; offline fixtures used; CI does not require secrets

**失败回退**：Pin or replace incompatible tooling; do not waive failing tests without decision record

### T006 — Implement project state and append-only ledgers

**依赖**：T004  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：PROJECT_STATE.yaml;task schema  
**输出**：state manager;task ledger;decision/blocker/experiment ledger initializers

**执行命令**：

```bash
biointerfaceos state validate && biointerfaceos state next
```

**验收标准**：State transition schema enforced; invalid DONE transition rejected; append-only JSONL detects truncation/rewrites; resume test passes

**失败回退**：Recover from latest valid record; preserve corrupt file; never silently rewrite history

### T007 — Define canonical schemas and configuration validation

**依赖**：T004  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：GOAL data contracts  
**输出**：Pydantic/JSON schemas;config loader;schema tests

**执行命令**：

```bash
biointerfaceos schema validate-all
```

**验收标准**：Material, bioenvironment, protocol, evidence, corona, response, source, agent and claim schemas validate fixtures; schema versions recorded

**失败回退**：Add migration path for schema changes; quarantine invalid records

### T008 — Implement storage accounting and quota guard

**依赖**：T006,T007  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：1.5 TB budget  
**输出**：storage audit;duplicate hash report;quota config

**执行命令**：

```bash
biointerfaceos storage audit --strict
```

**验收标准**：Directory usage and duplicate hashes reported; soft-limit write denied in test; raw deletion impossible by default; transient cleanup dry-run only

**失败回退**：Reduce cache or mark regenerable assets; never delete raw automatically

### T009 — Implement resilient anonymous network client

**依赖**：T003,T005  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：public API requirements  
**输出**：HTTP/FTP client;rate limiter;retry;resume;checksum;fixtures

**执行命令**：

```bash
pytest -q tests/network
```

**验收标准**：Timeout, bounded retry, backoff, user agent, pagination and resumable download tests pass; no credentials read or emitted

**失败回退**：Switch protocol or mirror only when officially allowed; mark source unavailable and continue

### T010 — Implement source manifest registry

**依赖**：T007,T009  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：source schema  
**输出**：registry/SOURCE_MANIFEST.parquet;manifest API;tests

**执行命令**：

```bash
biointerfaceos source manifest validate
```

**验收标准**：Admitted/rejected/quarantined assets represented; URL/accession/time/hash/license fields enforced; same asset deduplicated by content hash

**失败回退**：Quarantine incomplete rows; never guess license or hash

### T011 — Implement source and license policy engine

**依赖**：T010  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：GOAL access constraints  
**输出**：configs/source_policy.yaml;license parser;rejection registry

**执行命令**：

```bash
biointerfaceos source policy self-test
```

**验收标准**：Fixtures requiring login, registration, API key, approval, payment or unclear redistribution are correctly rejected/quarantined; allowed public fixtures admitted

**失败回退**：Default deny on ambiguity; record evidence and continue with substitutes

### T012 — Implement content-addressed asset store

**依赖**：T010  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：source manifest  
**输出**：CAS store;atomic downloader;hash index

**执行命令**：

```bash
pytest -q tests/assets && biointerfaceos assets verify
```

**验收标准**：Identical bytes stored once; partial download not promoted; hash mismatch rejected; provenance remains linked

**失败回退**：Preserve corrupt artifact in quarantine for diagnosis; retry official source

### T013 — Implement DuckDB analytical catalog

**依赖**：T007,T010  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：canonical schemas  
**输出**：DuckDB views;migrations;query smoke tests

**执行命令**：

```bash
biointerfaceos catalog build && biointerfaceos catalog check
```

**验收标准**：Parquet-backed views build idempotently; schema version stored; core joins return expected fixture rows

**失败回退**：Rebuild derived DB from Parquet; never treat DuckDB file as sole source of truth

### T014 — Implement immutable release and checksum system

**依赖**：T006,T012,T013  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：manifest;catalog;state  
**输出**：release freezer;checksums;release receipt

**执行命令**：

```bash
biointerfaceos release freeze --fixture && biointerfaceos release verify --fixture
```

**验收标准**：Frozen release is immutable; same inputs reproduce same manifest hash; overwrite rejected; receipt records git/data/config hashes

**失败回退**：Create a new version for fixes; never mutate a frozen release

### T015 — Implement lockbox firewall and contamination scanner

**依赖**：T006,T014  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：date split;lockbox rules  
**输出**：lockbox ACL abstraction;path guard;content hash scanner;tests

**执行命令**：

```bash
biointerfaceos lockbox self-test
```

**验收标准**：Development command cannot read lockbox payload; metadata whitelist enforced; forbidden fields and hashes trigger failure; audit receipt produced

**失败回退**：Stop affected task; quarantine contaminated outputs; rebuild development release from clean commit

## Phase 1：公共来源适配器

### T016 — Create source adapter interface and fixture harness

**依赖**：T011,T015  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：network client;policy engine  
**输出**：adapter protocol;fixture recorder;integration harness

**执行命令**：

```bash
pytest -q tests/sources/test_adapter_contract.py
```

**验收标准**：All adapters implement search, metadata, list_assets and fetch with policy checks; fixtures strip volatile/private fields

**失败回退**：Reject adapters that bypass policy; maintain independent failures

### T017 — Implement Europe PMC adapter

**依赖**：T016  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：Europe PMC REST/OAI public endpoints  
**输出**：Europe PMC adapter;query fixtures;pagination tests

**执行命令**：

```bash
biointerfaceos source test europe_pmc
```

**验收标准**：Reproducible search and full-text-link metadata; cursor pagination and rate limit work; license/provenance captured

**失败回退**：Use official alternative endpoint; if unavailable mark transient and continue

### T018 — Implement PMC Open Access adapter

**依赖**：T016  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：PMC OA file list/API  
**输出**：PMC OA adapter;OA license filter;JATS asset listing

**执行命令**：

```bash
biointerfaceos source test pmc_oa
```

**验收标准**：Only OA-subset/explicit-license assets admitted; JATS, figures and supplements linked; non-OA fixture rejected

**失败回退**：Retain metadata pointer only for non-redistributable content

### T019 — Implement PRIDE/ProteomeXchange adapter

**依赖**：T016  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：PRIDE API/FTP public endpoints  
**输出**：PRIDE adapter;project/file manifests;resume tests

**执行命令**：

```bash
biointerfaceos source test pride
```

**验收标准**：Project metadata and file list retrieved anonymously; accession/date/species/instrument/checksum captured; large-file dry-run works

**失败回退**：Try official PRIDE/ProteomeCentral mirrors; otherwise mark asset unavailable without blocking

### T020 — Implement GEO/SRA adapter

**依赖**：T016  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：GEO public FTP/NCBI metadata  
**输出**：GEO adapter;series/sample/file maps;SOFT/matrix fixtures

**执行命令**：

```bash
biointerfaceos source test geo
```

**验收标准**：GSE/GSM relations, processed files and raw links parse; anonymous access verified; restricted dbGaP-like records rejected

**失败回退**：Use public processed files where raw is impractical; keep evidence grade lower

### T021 — Implement PubChem PUG-REST adapter

**依赖**：T016  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：public compound identifiers  
**输出**：PubChem adapter;cache;rate-limit tests

**执行命令**：

```bash
biointerfaceos source test pubchem
```

**验收标准**：CID/name/SMILES/InChIKey/descriptors resolve with caching; request rate respects configured limit; ambiguity preserved

**失败回退**：Use local cache and batch endpoints; unresolved structures stay null

### T022 — Implement ChEMBL web-service adapter

**依赖**：T016  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：public ligand records  
**输出**：ChEMBL adapter;pagination/cache tests

**执行命令**：

```bash
biointerfaceos source test chembl
```

**验收标准**：Molecule IDs, structures and selected public properties resolve; duplicate salts handled; provenance recorded

**失败回退**：Fall back to PubChem/local structure evidence; never invent mapping

### T023 — Implement protein pathway cell-line ontology adapters

**依赖**：T016  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：UniProt;GO;Reactome;Cellosaurus public resources  
**输出**：versioned ontology snapshots;mapping API

**执行命令**：

```bash
biointerfaceos ontology sync --dry-run && pytest -q tests/ontology
```

**验收标准**：Version/date/license stored; protein, pathway, species and cell-line fixture mappings pass; obsolete IDs tracked

**失败回退**：Use frozen local snapshots; quarantine ambiguous mapping

### T024 — Implement public repository/code asset adapters

**依赖**：T016  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：Zenodo;Figshare;OSF;GitHub public metadata  
**输出**：repository adapter;license/commit capture

**执行命令**：

```bash
biointerfaceos source test repositories
```

**验收标准**：Public release assets, DOI, commit and license captured without token; rate-limit fallback works; code not executed during ingest

**失败回退**：Store pointer and metadata if rate limited; never use user credentials

### T025 — Audit specialized nanomaterial databases

**依赖**：T011,T016  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：candidate database list  
**输出**：reports/NANODATABASE_ADMISSION.md;registry source decisions

**执行命令**：

```bash
biointerfaceos source audit-specialized
```

**验收标准**：Each candidate has anonymous-access, license, exportability and schema assessment; credentialed sources rejected; only admitted adapters queued

**失败回退**：Do not make rejected databases blockers; search literature and open repositories instead

## Phase 2：系统检索与文献宇宙

### T026 — Build versioned query matrix

**依赖**：T017,T018,T019,T020,T025  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：GOAL search concepts  
**输出**：configs/search_queries.yaml;query validation report

**执行命令**：

```bash
biointerfaceos search validate-queries
```

**验收标准**：Queries cover material, corona, endpoint, data and assay axes; duplicates and impossible syntax flagged; frozen query version produced

**失败回退**：Revise query syntax without inspecting lockbox outcomes

### T027 — Run initial systematic search and seed registry

**依赖**：T026  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：query matrix  
**输出**：search_runs;candidate papers;candidate datasets

**执行命令**：

```bash
biointerfaceos search run --scope development
```

**验收标准**：All query/run timestamps, cursors and hit IDs saved; date firewall applied; deterministic rerun from cached pages; no locked semantic payload

**失败回退**：Retry bounded; save partial results and continue other query blocks

### T028 — Expand citations datasets and supplementary links

**依赖**：T027,T024  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：seed papers  
**输出**：citation graph;dataset links;code/supplement links

**执行命令**：

```bash
biointerfaceos search expand --depth 2 --scope development
```

**验收标准**：Forward/backward expansion is provenance-tracked; duplicates collapse to paper families; depth and stopping rule recorded

**失败回退**：Limit to public metadata; skip inaccessible citation services

### T029 — Compute search saturation and coverage gaps

**依赖**：T027,T028  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：search registry  
**输出**：reports/search_saturation.html;gap query proposals

**执行命令**：

```bash
biointerfaceos search saturation
```

**验收标准**：Novel eligible-study yield by batch/axis reported; missing years/materials/endpoints identified; stopping criteria evaluated

**失败回退**：Generate targeted queries; never claim exhaustive coverage

### T030 — Resolve paper families and study identities

**依赖**：T028  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：candidate sources  
**输出**：paper_families.parquet;study/lab keys;dedup report

**执行命令**：

```bash
biointerfaceos resolve paper-families
```

**验收标准**：Preprint/article/correction/supplement and dataset links grouped; conflicts preserved; same family cannot cross split in fixture test

**失败回退**：Manual-review queue for uncertain families; do not force merge

## Phase 3：多模态抽取与证据数据湖

### T031 — Implement policy-gated asset downloader

**依赖**：T012,T018,T030  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：admitted source manifest  
**输出**：download queue;asset receipts;quarantine

**执行命令**：

```bash
biointerfaceos data fetch --fixture && biointerfaceos assets verify
```

**验收标准**：Only admitted assets fetched; content type/size/hash verified; resume works; lockbox payload blocked

**失败回退**：Quarantine bad type/hash; retry official asset; continue independent items

### T032 — Implement JATS/XML full-text parser

**依赖**：T031  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：OA JATS fixtures  
**输出**：document graph;section/table/figure refs;tests

**执行命令**：

```bash
pytest -q tests/extract/test_jats.py
```

**验收标准**：Sections, paragraphs, tables, captions, references and supplementary links preserved with stable locators; round-trip evidence locator passes

**失败回退**：Store raw XML and parser warning; use PDF fallback only for missing fields

### T033 — Implement supplementary spreadsheet and archive parser

**依赖**：T031,T007  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：XLSX/CSV/TSV/ZIP fixtures  
**输出**：supplement inventory;normalized tables;safe archive extraction

**执行命令**：

```bash
pytest -q tests/extract/test_supplements.py
```

**验收标准**：Merged cells, multirow headers, sheets, units and formulas handled; zip-slip/malicious archive tests blocked; original cell coordinates retained

**失败回退**：Quarantine unsupported/encrypted files; record need for alternative source

### T034 — Implement PDF fallback parser

**依赖**：T031  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：public PDFs not represented by JATS  
**输出**：layout blocks;page locators;quality report

**执行命令**：

```bash
pytest -q tests/extract/test_pdf.py
```

**验收标准**：Text/tables/captions retain page/bbox; born-digital fixtures pass; scanned PDFs explicitly marked rather than silently OCRed

**失败回退**：Use structured/supplement source first; OCR only single critical pages with audit

### T035 — Implement table-to-experiment parser

**依赖**：T032,T033,T034  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：document tables;experiment schema  
**输出**：table cells to arms/measurements parser;fixtures

**执行命令**：

```bash
biointerfaceos extract tables --fixture && pytest -q tests/extract/test_table_semantics.py
```

**验收标准**：Header hierarchy, arm identity, sample size, mean/error/unit and footnotes mapped; cell evidence locator exact; ambiguity retained

**失败回退**：Send low-confidence tables to consensus queue; never flatten incompatible sub-tables

### T036 — Implement scientific figure panel and axis detector

**依赖**：T032,T034  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：figure assets/captions  
**输出**：panel map;axis/legend detector;uncertainty fields

**执行命令**：

```bash
pytest -q tests/extract/test_figures.py
```

**验收标准**：Panel labels, axes, scale type, legend and curve candidates detected on synthetic fixtures; confidence calibrated

**失败回退**：Mark unsupported 3D/heatmap/image assay panels; do not digitize automatically

### T037 — Implement curve/bar/scatter digitization with uncertainty

**依赖**：T036  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：eligible figures  
**输出**：digitized points;pixel calibration;error model;QC overlays

**执行命令**：

```bash
biointerfaceos extract figures --fixture && pytest -q tests/extract/test_digitize.py
```

**验收标准**：Synthetic recovery meets error thresholds; log axes/error bars supported; overlay artifact permits review; uncertainty propagated

**失败回退**：Exclude poor-resolution panels from quantitative main analysis; retain qualitative evidence

### T038 — Implement dual-path structured extraction

**依赖**：T032,T033,T035,T037  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：document graph;tables;figures  
**输出**：rule extraction;LLM/local extraction;consensus records

**执行命令**：

```bash
biointerfaceos extract experiment --fixture --dual
```

**验收标准**：Both paths output same schema; disagreements logged; no field accepted without evidence locator; mock/local backend works without private API

**失败回退**：Use deterministic path and review queue if model unavailable; never lower evidence requirements

### T039 — Implement evidence resolver and reverse trace

**依赖**：T038  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：candidate experiment records  
**输出**：evidence table;reverse trace CLI;conflict graph

**执行命令**：

```bash
biointerfaceos evidence trace --fixture
```

**验收标准**：Every accepted numeric field resolves to raw asset and exact locator; missing/broken locators rejected; conflicting values retained as separate assertions

**失败回退**：Demote or quarantine records with unresolved lineage

### T040 — Implement units normalization and uncertainty propagation

**依赖**：T039  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：raw numeric assertions  
**输出**：unit registry;normalized values;conversion tests

**执行命令**：

```bash
pytest -q tests/normalize/test_units.py
```

**验收标准**：Dimensionally valid conversions pass; concentration/dose/size/time/zeta/PDI handled; unknown basis not converted; uncertainty conversion correct

**失败回退**：Keep raw value and null normalized value; queue clarification from other evidence

### T041 — Implement material and formulation entity resolution

**依赖**：T021,T022,T039  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：material strings/structures  
**输出**：material entities;formulation graphs;alias candidates

**执行命令**：

```bash
biointerfaceos resolve materials --fixture
```

**验收标准**：Lipids, polymers, ligands, core/coating and mixture fractions mapped with provenance; ambiguous trade names not forced; fractions validated

**失败回退**：Create unresolved entity with candidate set; use higher-level family features only

### T042 — Implement protein identifier and orthology resolution

**依赖**：T023,T039  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：protein names/accessions/species  
**输出**：protein entities;ortholog groups;mapping confidence

**执行命令**：

```bash
biointerfaceos resolve proteins --fixture
```

**验收标准**：Species-specific accession and gene maps pass; isoform/obsolete ambiguity recorded; one-to-many orthology preserved

**失败回退**：Use protein groups/function modules; never map across species by name only

### T043 — Implement bioenvironment and protocol ontology

**依赖**：T023,T039,T040  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：fluid/species/protocol strings  
**输出**：bioenvironment/protocol entities;severity features

**执行命令**：

```bash
biointerfaceos resolve protocols --fixture
```

**验收标准**：Serum/plasma/source, concentration, time, temperature, wash, centrifugation, assay and replicate fields normalized; missingness explicit

**失败回退**：Create protocol cluster with unknown fields; do not impute as observed

### T044 — Implement endpoint and measurement ontology

**依赖**：T023,T039,T040  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：outcome strings  
**输出**：endpoint entities;measurement mappings;effect-size conversions

**执行命令**：

```bash
biointerfaceos resolve endpoints --fixture
```

**验收标准**：Uptake, viability, complement, inflammation, coagulation, biodistribution and delivery endpoints distinguish assay/basis/time; compatible effects harmonized

**失败回退**：Keep incompatible endpoint strata separate

### T045 — Implement physical and statistical plausibility checks

**依赖**：T040,T041,T043,T044  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：normalized experiment records  
**输出**：QC flags;injected-error tests

**执行命令**：

```bash
biointerfaceos qc records --fixture --strict
```

**验收标准**：Impossible fractions, signs, units, duplicate sample counts, SEM/SD confusion candidates and range anomalies flagged; false positives measured

**失败回退**：Quarantine critical errors; retain noncritical warning with weight

### T046 — Build immutable Bronze data release

**依赖**：T031,T032,T033,T034  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：raw admitted assets  
**输出**：bronze release;manifest;checksums

**执行命令**：

```bash
biointerfaceos data build-bronze && biointerfaceos release verify bronze
```

**验收标准**：All admitted raw/parsed assets represented; no normalization overwrite; license tiers separated; exact rebuild receipt exists

**失败回退**：Publish pointers only where redistribution prohibited

### T047 — Build normalized Silver data release

**依赖**：T039,T040,T041,T042,T043,T044,T045,T046  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：Bronze;normalizers  
**输出**：silver Parquet tables;catalog views;QC report

**执行命令**：

```bash
biointerfaceos data build-silver && biointerfaceos data validate silver
```

**验收标准**：Referential integrity passes; no duplicate primary keys; every value has evidence; critical QC zero or quarantined; schema/version hash frozen

**失败回退**：Fix mappings or exclude quarantined records; never silently drop

### T048 — Build audited Gold-auto subset

**依赖**：T047,T038  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：Silver;dual extraction  
**输出**：gold_auto release;agreement report

**执行命令**：

```bash
biointerfaceos data build-gold-auto
```

**验收标准**：Only high-confidence, dual-agreement or deterministic-source records admitted; disagreement and evidence-grade thresholds encoded; reverse trace passes

**失败回退**：Keep record in Silver; do not self-label expert gold

### T049 — Generate consensus and expert review packets

**依赖**：T048  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：disagreement/high-impact queue  
**输出**：review packets;annotation guide;sign-off schema

**执行命令**：

```bash
biointerfaceos review export --sample stratified
```

**验收标准**：Packets include blinded source context, exact question, candidate values and evidence; Gold-expert impossible without signed import

**失败回退**：Proceed with Gold-auto analyses; report absence of human review honestly

### T050 — Run extraction benchmark and error analysis

**依赖**：T048,T049  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：gold fixtures/consensus if available  
**输出**：metrics;calibration;error taxonomy;model card

**执行命令**：

```bash
biointerfaceos benchmark extraction
```

**验收标准**：Numeric/entity/arm/evidence metrics and confidence calibration reported by modality/material/year; thresholds G2 evaluated

**失败回退**：Narrow automatic fields or increase review; no main analysis until G2 passes

### T051 — Publish data coverage and missingness audit

**依赖**：T047,T050,T029  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：Silver;search registry  
**输出**：coverage report;missingness model;bias warnings

**执行命令**：

```bash
biointerfaceos report data-coverage
```

**验收标准**：Counts use independent units; coverage by study/lab/material/species/endpoint/date/evidence; missingness predictors and gaps reported

**失败回退**：Trigger targeted search or scope reduction; never pad with pseudo-replicates

## Phase 4：PRIDE/GEO 原始组学

### T052 — Triage PRIDE projects and freeze sample plans

**依赖**：T019,T030,T051  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：PRIDE candidates;paper families  
**输出**：PRIDE project cards;sample maps;split eligibility

**执行命令**：

```bash
biointerfaceos omics pride triage --scope development
```

**验收标准**：Each project has official date, files, raw/search availability, material arms, biofluid, replicates, outcomes and split decision; locked projects metadata-only

**失败回退**：Reject/park unclear sample maps; search additional public projects

### T053 — Implement raw mass-spec conversion workflow

**依赖**：T052  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：eligible public raw files  
**输出**：ThermoRawFileParser/mzML workflow;conversion receipts

**执行命令**：

```bash
biointerfaceos omics convert --fixture
```

**验收标准**：Small public/fixture RAW converts or supported mzML bypasses; checksums, instrument metadata and logs stored; resume works

**失败回退**：Use vendor-neutral provided mzML or processed evidence; record lower grade

### T054 — Implement Sage search workflow and toy recovery

**依赖**：T053,T023  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：mzML;species FASTA;search config  
**输出**：Sage configs;PSM/peptide/protein outputs;FDR tests

**执行命令**：

```bash
biointerfaceos omics search --fixture
```

**验收标准**：Target-decoy/FDR, enzyme/modifications and protein database version explicit; synthetic spike-in recovery passes; no project-specific cherry-picking

**失败回退**：Use declared alternative open search engine with same QC; document decision

### T055 — Implement label-free quantification and protein inference

**依赖**：T054  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：search outputs  
**输出**：protein x sample matrices;missingness/QC

**执行命令**：

```bash
biointerfaceos omics quantify --fixture
```

**验收标准**：Replicates, normalization, protein groups, contaminants and missing values handled; fixture expected ratios recovered

**失败回退**：Compare multiple declared quantification routes; retain uncertainty

### T056 — Harmonize protein-corona matrices across projects

**依赖**：T042,T052,T055  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：project matrices;protein mappings  
**输出**：harmonized composition/function matrices;batch metadata

**执行命令**：

```bash
biointerfaceos omics harmonize-corona
```

**验收标准**：Species/protein group mapping auditable; compositional transformations valid; project-specific scale retained; no ComBat across outcome leakage

**失败回退**：Analyze project-level and functional modules if protein-level merge invalid

### T057 — Run PRIDE quality control and author-result concordance

**依赖**：T056  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：harmonized matrices;paper claims  
**输出**：PRIDE QC report;concordance;failure ledger

**执行命令**：

```bash
biointerfaceos omics qc-pride
```

**验收标准**：At least three development projects attempted; successful projects meet replicate/FDR/intensity QC; concordance and discrepancies quantified; failed projects reported

**失败回退**：If G4 fails, use processed tables as lower evidence and narrow raw-omics claims

### T058 — Discover public GEO/SRA biointerface response datasets

**依赖**：T020,T026,T051  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：query matrix;endpoint gaps  
**输出**：GEO candidate registry;eligibility cards

**执行命令**：

```bash
biointerfaceos omics geo discover --scope development
```

**验收标准**：Nanomaterial/material exposure, cell/tissue, dose/time and public files verified; credentialed/restricted studies rejected; paper family links captured

**失败回退**：Use processed public matrices or omit module if no suitable data

### T059 — Ingest and normalize GEO processed data

**依赖**：T058,T042,T043,T044  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：eligible processed matrices  
**输出**：study-level expression objects;QC receipts

**执行命令**：

```bash
biointerfaceos omics geo process --mode processed
```

**验收标准**：Sample metadata and contrasts auditable; gene IDs normalized; within-study QC passes; studies not forcibly batch-merged

**失败回退**：Exclude unusable studies with reason; retain metadata

### T060 — Implement optional public RNA-seq raw reprocessing

**依赖**：T058  
**优先级**：P2  
**初始状态**：BLOCKED

**输入**：eligible manageable SRA FASTQ  
**输出**：RNA-seq workflow;counts;QC

**执行命令**：

```bash
biointerfaceos omics geo process --mode raw --fixture
```

**验收标准**：Fixture workflow reproduces expected counts; public raw study selected by value/storage budget; versioned reference used

**失败回退**：Skip raw reprocessing if storage/metadata insufficient; processed route remains

### T061 — Derive cell and immune response signatures

**依赖**：T059,T060  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：normalized expression;pathways  
**输出**：signature scores;uncertainty;cross-study validation

**执行命令**：

```bash
biointerfaceos omics derive-signatures
```

**验收标准**：Predefined and data-driven signatures separated; leave-study-out stability tested; pathway provenance versioned; no label leakage

**失败回退**：Use robust predefined modules only if learned factors unstable

### T062 — Link corona functional modules to cell-state evidence

**依赖**：T056,T061,T047  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：corona modules;response signatures;paper links  
**输出**：cross-omics evidence graph;matched/indirect strata

**执行命令**：

```bash
biointerfaceos omics link-modalities
```

**验收标准**：Directly matched and literature-level indirect links clearly separated; no pseudo-pairing; evidence strength encoded; candidate mechanisms generated not asserted

**失败回退**：Keep modalities as independent triangulation if no valid linkage

## Phase 5：切分、锁定与泄漏防控

### T063 — Create canonical group keys

**依赖**：T030,T041,T043,T047,T057  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：Silver/Gold;study maps  
**输出**：study/lab/paper/material/bioenvironment/date group keys

**执行命令**：

```bash
biointerfaceos split build-groups
```

**验收标准**：Keys deterministic and reviewed; unknown lab handled conservatively; same paper family/project cannot split; collision tests pass

**失败回退**：Use broader grouping for uncertain identity

### T064 — Detect formulation and semantic near-duplicates

**依赖**：T041,T063  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：material/formulation records  
**输出**：duplicate clusters;similarity thresholds;manual queue

**执行命令**：

```bash
biointerfaceos split detect-duplicates
```

**验收标准**：Exact, composition, structure and text near-duplicates detected on injected fixtures; threshold frozen without test labels; cross-split duplicates zero

**失败回退**：Group ambiguous neighbors together; sacrifice sample count over leakage

### T065 — Freeze development train and validation splits

**依赖**：T063,T064,T015  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：group keys;official dates  
**输出**：split manifest;feature blacklist;freeze receipt

**执行命令**：

```bash
biointerfaceos split freeze-dev
```

**验收标准**：Date rule, group constraints and endpoint availability applied; train <=2023-12-31, validation in 2024; hashes signed; no locked payload read

**失败回退**：Resolve date ambiguity conservatively into later split or exclude

### T066 — Run adversarial leakage and lockbox audit

**依赖**：T065  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：frozen splits;features;paths  
**输出**：leakage report;contamination scan;approval receipt

**执行命令**：

```bash
biointerfaceos split audit --strict
```

**验收标准**：Paper/accession/author/journal/layout/path features absent; study-only and ID-hash attacks assessed; lockbox forbidden read test passes; critical findings zero

**失败回退**：Invalidate and rebuild split/release if contamination found

## Phase 6：BioInterfaceBench

### T067 — Build BioInterfaceBench task instances

**依赖**：T048,T056,T062,T065  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：Gold-auto;omics;split manifest  
**输出**：E1/C1/U1/S1/B1/CF1/D1/A1 instance files

**执行命令**：

```bash
biointerfaceos benchmark build --dev
```

**验收标准**：Instances validate schema; public input/hidden target separation; group keys attached; minimum task sizes and missingness reported

**失败回退**：Drop underpowered task from primary benchmark and retain pilot status

### T068 — Implement executable graders and abstention metrics

**依赖**：T067  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：benchmark instances;metric configs  
**输出**：grader package;containers;unit tests

**执行命令**：

```bash
biointerfaceos benchmark grade --fixture
```

**验收标准**：Known perfect/wrong/abstain submissions score as expected; no network needed; uncertainty/calibration and grouped metrics correct

**失败回退**：Fix grader before any model comparison; bump benchmark version for semantic changes

### T069 — Implement data/statistical benchmark baselines

**依赖**：T067,T068  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：task instances  
**输出**：mean/family/kNN/linear/mixed-effect baseline results

**执行命令**：

```bash
biointerfaceos benchmark run-baselines --group simple
```

**验收标准**：All simple baselines run from one command; seeds/configs logged; primary OOD metrics and confidence intervals produced

**失败回退**：Keep failure as baseline limitation; do not skip without report

### T070 — Implement representation benchmark baselines

**依赖**：T067,T068,T021,T022  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：material text/structure/descriptor inputs  
**输出**：fingerprint/text/polymer embedding baseline results

**执行命令**：

```bash
biointerfaceos benchmark run-baselines --group representation
```

**验收标准**：At least descriptor, fingerprint, text and available polymer embedding baselines compared under identical splits; missing structure coverage reported

**失败回退**：Use available subset plus missingness indicator; no silent complete-case bias

## Phase 7：统计、世界模型与不确定性

### T071 — Fit hierarchical mixed-effect baseline

**依赖**：T069,T063  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：benchmark development data  
**输出**：M1 model;variance partition;diagnostics

**执行命令**：

```bash
biointerfaceos train m1 --config configs/models/m1.yaml
```

**验收标准**：Convergence/diagnostics pass; study/protocol/material variance reported; grouped CV and calibration computed; toy parameter recovery passes

**失败回退**：Simplify random effects or use Bayesian regularization; record nonidentifiability

### T072 — Fit direct black-box baseline

**依赖**：T069,T070  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：material/environment/protocol features  
**输出**：M2 models;feature audit;OOD results

**执行命令**：

```bash
biointerfaceos train m2 --config configs/models/m2.yaml
```

**验收标准**：Tree/MLP or declared models tuned only on train; validation OOD, calibration and SHAP/permutation checks reported; IDs excluded

**失败回退**：Use simpler model if data insufficient; preserve null result

### T073 — Fit static corona mediator model

**依赖**：T071,T072,T056  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：paired M,C,Y data  
**输出**：M3 model;direct/mediated prediction comparison

**执行命令**：

```bash
biointerfaceos train m3 --config configs/models/m3.yaml
```

**验收标准**：Paired-unit construction audited; mediator improves or fails transparently; alternative/random mediator controls run; uncertainty propagated

**失败回退**：Downgrade to associational decomposition if identification/data insufficient

### T074 — Fit compositional corona model

**依赖**：T073  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：protein/function compositions  
**输出**：M4 logistic-normal/ILR model;zero handling sensitivity

**执行命令**：

```bash
biointerfaceos train m4 --config configs/models/m4.yaml
```

**验收标准**：Simplex constraints hold; zero/pseudocount alternatives compared; OOD and calibration not worse than static baseline; toy compositions recovered

**失败回退**：Use functional balances and simpler model if protein-level sparse

### T075 — Fit dynamic corona world model

**依赖**：T074,T057  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：time-course corona data  
**输出**：M5 hierarchical kinetics/neural ODE;trajectory results

**执行命令**：

```bash
biointerfaceos train m5 --config configs/models/m5.yaml
```

**验收标准**：Data sufficiency gate checked; mass/simplex constraints hold; toy dynamics recovered; leave-study trajectory performance reported; simpler kinetic baseline included

**失败回退**：If G3 dynamic threshold fails, implement discrete/hierarchical kinetics and mark neural model waived

### T076 — Fit hierarchical causal world model

**依赖**：T073,T074,T075  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：DAG;paired data;random effects  
**输出**：M6 estimands;mediation sensitivity;posterior predictions

**执行命令**：

```bash
biointerfaceos train m6 --config configs/models/m6.yaml
```

**验收标准**：DAG/estimand preregistered; overlap, confounding sensitivity and alternative DAGs assessed; language automatically downgraded if gate fails

**失败回退**：Retain predictive mediator model; prohibit causal wording

### T077 — Add cross-domain invariant learning

**依赖**：T071,T074,T076  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：environment labels;core models  
**输出**：M7 ERM/groupDRO/IRM-like/hierarchical comparison

**执行命令**：

```bash
biointerfaceos train m7 --config configs/models/m7.yaml
```

**验收标准**：Identical tuning budget; at least two domain definitions; no validation/test environment label leakage; complexity accepted only if OOD improves

**失败回退**：Keep hierarchical ERM as main model if invariant methods fail

### T078 — Add calibrated uncertainty and abstention

**依赖**：T071,T072,T074,T076,T077  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：model ensembles;OOD distances  
**输出**：conformal/ensemble uncertainty;selective-risk curves

**执行命令**：

```bash
biointerfaceos train uncertainty --config configs/models/uncertainty.yaml
```

**验收标准**：Calibration evaluated by domain; selective risk decreases with abstention; coverage reported; OOD detector compared to simple distance

**失败回退**：Use conservative ensemble/conformal fallback; reject overconfident model

### T079 — Add multimodal material and document representations

**依赖**：T070,T074,T078  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：structures;text;figures;protocols  
**输出**：M7 multimodal fusion;missing-modality tests

**执行命令**：

```bash
biointerfaceos train multimodal --config configs/models/multimodal.yaml
```

**验收标准**：Fusion compared to each modality; missing modality masks; source identity leakage test; gains persist OOD and are not due to article text containing outcomes

**失败回退**：Remove outcome-contaminated text and retain material/protocol-only representations

## Phase 8：科研 Agent 系统

### T080 — Implement typed multi-agent runtime

**依赖**：T004,T006,T007,T068  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：Agent contracts in GOAL  
**输出**：agent runtime;budgets;replay/mock backends;logs

**执行命令**：

```bash
biointerfaceos agent self-test
```

**验收标准**：Schema validation, tool allowlist, budgets, deterministic replay, retries and append-only traces pass; no provider key required for CI

**失败回退**：Disable failing backend; core mock/rule runtime must remain

### T081 — Implement SourceScout and LicenseGate agents

**依赖**：T080,T017,T018,T019,T020,T024,T011  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：source adapters;policy  
**输出**：source/license agent workflows;benchmark cases

**执行命令**：

```bash
biointerfaceos agent eval source-license
```

**验收标准**：Agents recover eligible sources and reject restricted injected cases; every decision cites metadata evidence; no credential requests

**失败回退**：Fallback to deterministic adapters/policy; log agent value as zero if no gain

### T082 — Implement multimodal ExtractionAgent

**依赖**：T080,T038,T050  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：document extraction tools;gold cases  
**输出**：extraction agent;tool traces;eval

**执行命令**：

```bash
biointerfaceos agent eval extraction
```

**验收标准**：Agent selects appropriate parser, produces schema-valid evidence-grounded experiments and improves declared metric versus fixed pipeline or is rejected

**失败回退**：Use fixed extraction pipeline; do not lower acceptance for agent

### T083 — Implement Resolution and EvidenceAuditor agents

**依赖**：T080,T039,T041,T042,T043,T044  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：candidate records;ontologies  
**输出**：resolution/audit agents;conflict tests

**执行命令**：

```bash
biointerfaceos agent eval audit
```

**验收标准**：Injected unit/entity/evidence conflicts detected; false merge rate controlled; all corrections preserve original assertion

**失败回退**：Quarantine unresolved records; deterministic resolver remains

### T084 — Implement Mechanism and hypothesis agents

**依赖**：T080,T062,T076  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：training-only evidence graph;model residuals  
**输出**：hypothesis proposals;formal schemas;falsifiability grader

**执行命令**：

```bash
biointerfaceos agent eval hypothesis
```

**验收标准**：Proposals are nonduplicate, falsifiable, formalized and evidence-linked; lockbox contamination scan zero; no claim automatically accepted

**失败回退**：Use curated seed hypotheses only; mark agent exploratory

### T085 — Implement ModelBuilder and Statistician agents

**依赖**：T080,T068,T071,T078  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：task specs;model APIs  
**输出**：code/analysis planning agents;execution sandbox tests

**执行命令**：

```bash
biointerfaceos agent eval modeling
```

**验收标准**：Agent-generated plans compile/run in sandbox; tests and preregistration generated; metric hacking traps rejected; no split modification

**失败回退**：Agent may propose patches only; deterministic CI decides acceptance

### T086 — Implement RedTeam agent suite

**依赖**：T080,T066,T078  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：models;claims;data  
**输出**：leakage/negative-control/adversarial suite

**执行命令**：

```bash
biointerfaceos agent red-team --all
```

**验收标准**：All mandatory attacks execute; injected leak and unit error detected; findings severity and remediation logged; adverse results preserved

**失败回退**：Block release on critical finding; continue unrelated tasks

### T087 — Implement Reproducibility and Lockbox evaluator agents

**依赖**：T080,T014,T015,T068  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：frozen releases;graders  
**输出**：reproduction receipts;disabled lockbox evaluator

**执行命令**：

```bash
biointerfaceos agent eval reproducibility
```

**验收标准**：Fixture result rebuilt cleanly; lockbox evaluator cannot activate before signed freeze; no training methods exposed in evaluator interface

**失败回退**：Keep lockbox disabled and fix permission/interface

### T088 — Build end-to-end scientific-agent benchmark

**依赖**：T081,T082,T083,T084,T085,T086,T087,T067  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：agent workflows;benchmark tasks  
**输出**：agent task suite;single/multi/no-tool results;failure taxonomy

**执行命令**：

```bash
biointerfaceos benchmark agents --dev
```

**验收标准**：Completion, correctness, evidence, schema, safety, reproducibility and cost reported across all tasks; confidence intervals and failures included

**失败回退**：Publish benchmark/failure result even if multi-agent does not win

## Phase 9：科学规律发现

### T089 — Freeze hypothesis tournament and preregistration rules

**依赖**：T084,T088,T065  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：training-only evidence;claim schema  
**输出**：hypothesis ranking config;preregistrations;hash receipt

**执行命令**：

```bash
biointerfaceos claim preregister --dev
```

**验收标准**：K, weights, primary outcomes, exclusion, minimal effects and tests frozen before primary analyses; duplicates removed; lockbox scan zero

**失败回退**：Mark changes exploratory with new version; never overwrite

### T090 — Discover stable protein-corona functional axes

**依赖**：T056,T074,T089  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：development corona matrices  
**输出**：axis models;loadings;pathway enrichment;stability report

**执行命令**：

```bash
biointerfaceos discover functional-axes
```

**验收标准**：NMF/sparse/log-ratio alternatives compared; bootstrap and leave-study stability; random module controls; at least candidate axes with uncertainty

**失败回退**：Report failure and use predefined functional modules

### T091 — Estimate material-corona-outcome mediation laws

**依赖**：T073,T076,T089,T090  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：paired chain;DAG  
**输出**：claim-specific mediation estimates;sensitivity;replications

**执行命令**：

```bash
biointerfaceos discover mediation
```

**验收标准**：Preregistered estimands; study clustered uncertainty; alternative mediators/DAGs; claim wording passes gate; independent development replication attempted

**失败回退**：Downgrade to association; do not claim mediation

### T092 — Model human-mouse and biofluid transfer

**依赖**：T056,T078,T089,T090  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：cross-species/material overlap  
**输出**：transfer models;ranking/calibration report

**执行命令**：

```bash
biointerfaceos discover cross-species
```

**验收标准**：Direct, functional, OT and conditional models compared; overlap and pairing limitations explicit; leave-material validation; abstention available

**失败回退**：Restrict to population-level functional comparison or waive

### T093 — Discover unit-aware symbolic design laws

**依赖**：T071,T090,T089  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：normalized features;functional axes;outcomes  
**输出**：symbolic expressions;stability/Pareto/replication report

**执行命令**：

```bash
biointerfaceos discover symbolic-laws
```

**验收标准**：Nested study CV; dimensional constraints; GAM/tree controls; bootstrap expression stability; validation OOD; complexity penalty frozen

**失败回退**：Publish no simple law if unstable; retain flexible model

### T094 — Test protocol-correction and reversal hypotheses

**依赖**：T071,T089,T091  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：protocol ontology;claims  
**输出**：raw vs adjusted effects;heterogeneity maps;counterexamples

**执行命令**：

```bash
biointerfaceos discover protocol-effects
```

**验收标准**：Predefined protocol variables; within/comparable-study analyses; Simpson/reversal tests; no post-hoc subgroup cherry-picking; claim gate applied

**失败回退**：Report protocol dependence/boundary rather than universal reversal

### T095 — Run counterfactual ranking and contradiction analyses

**依赖**：T076,T089,T090,T091,T093,T094  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：causal/predictive models;contradiction graph  
**输出**：counterfactual rankings;contradiction resolutions;uncertainty

**执行命令**：

```bash
biointerfaceos discover counterfactuals
```

**验收标准**：Only supported interventions varied; positivity and OOD checked; rankings stable across models or abstained; contradictory literature strata explained computationally

**失败回退**：Label as model-based hypotheses and exclude unstable rankings

## Phase 10：反向设计

### T096 — Implement constrained multiobjective design baseline

**依赖**：T041,T078,T090,T095  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：public component space;surrogate models  
**输出**：enumeration/NSGA-II/BO engine;constraint tests;Pareto set

**执行命令**：

```bash
biointerfaceos design baseline
```

**验收标准**：Mixture/structure constraints pass ≥0.98; uncertainty and AD penalties active; observed controls recovered; Pareto output reproducible

**失败回退**：Restrict design space to observed components/ranges

### T097 — Implement target-corona conditional generative design

**依赖**：T096,T079  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：design baseline;representations;data sufficiency  
**输出**：latent/flow/diffusion optional generator;validity comparison

**执行命令**：

```bash
biointerfaceos design generative
```

**验收标准**：Data sufficiency gate passes; generator beats simple baseline on predefined validity/novelty/Pareto metrics without worse OOD uncertainty; ablations run

**失败回退**：WAIVE deep generator and keep BO/NSGA-II if gate fails

### T098 — Create candidate audit packets and retrospective validation

**依赖**：T096,T097  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：candidate sets;public later evidence metadata  
**输出**：candidate cards;neighbor/novelty/robustness report

**执行命令**：

```bash
biointerfaceos design audit-candidates
```

**验收标准**：Candidates deduplicated; AD, uncertainty, nearest evidence, perturbation stability and allowed wording included; any temporal match evaluated without tuning

**失败回退**：Label candidates exploratory; exclude high-OOD or unsafe predictions

## Phase 11：稳健性与负对照

### T099 — Run mandatory model and data ablations

**依赖**：T078,T079,T091,T093,T098  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：frozen dev models/claims  
**输出**：ablation matrix;paired statistics

**执行命令**：

```bash
biointerfaceos robustness ablations --all
```

**验收标准**：All GOAL ablations run with same budget/splits; effects and intervals reported; missing ablation justified by interface test not convenience

**失败回退**：Block associated claim/module if essential ablation absent

### T100 — Run OOD leave-group and sensitivity suite

**依赖**：T099  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：models;group keys  
**输出**：leave-study/lab/family/species/biofluid/time results

**执行命令**：

```bash
biointerfaceos robustness ood --all
```

**验收标准**：Primary metrics/calibration across all groups; low-n groups flagged; leave-largest-study and evidence-grade sensitivity included

**失败回退**：Narrow applicability domain or downgrade claim

### T101 — Assess publication selection and missingness bias

**依赖**：T047,T071,T091,T093  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：study effects;sample sizes;significance/evidence fields  
**输出**：selection models;funnel/sensitivity;missingness report

**执行命令**：

```bash
biointerfaceos robustness bias
```

**验收标准**：Selection/missingness assumptions explicit; multiple plausible models; conclusions compared; no p-value scraping presented as ground truth

**失败回退**：Downgrade strength and emphasize uncertainty

### T102 — Run negative controls and deliberate leakage attacks

**依赖**：T086,T099,T100,T101  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：data;models;claims  
**输出**：negative-control report;attack receipts;critical finding status

**执行命令**：

```bash
biointerfaceos robustness negative-controls --strict
```

**验收标准**：Label shuffles, random mediators, study/journal/year/layout, unit/missingness and duplicate attacks run; critical leak zero; expected attacks fail performance

**失败回退**：Invalidate affected release/model and rebuild from last clean state

## Phase 12：开发冻结与一次性时间盲测

### T103 — Freeze BioInterfaceBench development release

**依赖**：T067,T068,T069,T070,T102  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：dev benchmark;graders  
**输出**：versioned benchmark release;checksums;card

**执行命令**：

```bash
biointerfaceos benchmark freeze-dev
```

**验收标准**：Instance/grader/split hashes immutable; public and hidden layers separated; baseline receipts reproduce; semantic version assigned

**失败回退**：Create new version for changes; never overwrite

### T104 — Freeze development data and model release

**依赖**：T057,T062,T078,T079,T102  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：Silver/Gold;models;configs  
**输出**：data/model release;cards;checksums

**执行命令**：

```bash
biointerfaceos release freeze-dev
```

**验收标准**：All model-selection inputs, configs, checkpoints, thresholds and dependencies frozen; clean reproduction passes; license layers separated

**失败回退**：Fix only before final freeze and rerun robustness

### T105 — Draft Paper A benchmark manuscript

**依赖**：T103,T088  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：benchmark results;coverage/extraction reports  
**输出**：manuscripts/paper_a draft;figures/tables;claim matrix

**执行命令**：

```bash
make paper-a
```

**验收标准**：All numbers generated; dataset/benchmark claims evidence-linked; failures and limitations included; no lockbox result required

**失败回退**：Submit-ready benchmark route may proceed independently

### T106 — Draft Paper B method manuscript

**依赖**：T104,T088,T099,T100  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：model/agent results  
**输出**：manuscripts/paper_b draft;figures/tables;claim matrix

**执行命令**：

```bash
make paper-b
```

**验收标准**：Method novelty, OOD, calibration, ablation and agent evaluation complete; no unsupported causal or experimental claims

**失败回退**：Refocus on strongest validated method; remove failed module claims

### T107 — Draft Paper C scientific-law manuscript pre-lock

**依赖**：T090,T091,T092,T093,T094,T095,T100,T101  
**优先级**：P1  
**初始状态**：BLOCKED

**输入**：development discoveries  
**输出**：paper_c preregistered draft;predictions;figure definitions

**执行命令**：

```bash
make paper-c-prelock
```

**验收标准**：Development claims and predicted lockbox outcomes frozen; exact analyses/plots and allowed wording recorded; no lockbox payload viewed

**失败回退**：Narrow to candidate laws with strongest development evidence

### T108 — Create signed internal frozen release before lockbox

**依赖**：T103,T104,T105,T106,T107  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：all development artifacts  
**输出**：FROZEN_DEV receipt;commit/tag;lockbox plan

**执行命令**：

```bash
biointerfaceos release freeze-prelock --strict
```

**验收标准**：Working tree clean; all checks pass; claim/prereg/config/model/figure hashes recorded; lockbox access authorization token generated only for evaluator

**失败回退**：Do not unlock; resolve critical audit and create new freeze candidate

### T109 — Execute one-shot locked 2025-2026 evaluation

**依赖**：T108,T087  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：signed frozen release;metadata-only lockbox registry  
**输出**：first-run lockbox results;immutable receipt;raw logs

**执行命令**：

```bash
biointerfaceos lockbox evaluate --release FROZEN_DEV --once
```

**验收标准**：Evaluator verifies hashes, forbids train/tune calls, runs fixed commands once, writes first-run receipt; all outputs sealed before interpretation

**失败回退**：On mechanical failure preserve receipt; technical rerun only under declared protocol; never tune

### T110 — Audit lockbox results and update claim statuses

**依赖**：T109  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：sealed lockbox outputs;claim ledger  
**输出**：post-lock audit;claim transitions;failure analysis

**执行命令**：

```bash
biointerfaceos lockbox audit-results --strict
```

**验收标准**：Each preregistered prediction marked replicated/refuted/inconclusive; no threshold change; calibration and failure cases reported; contamination scan clean

**失败回退**：Downgrade/refute claims; do not exclude inconvenient test studies

## Phase 13：论文、复现与最终发布

### T111 — Generate final publication figures and tables

**依赖**：T105,T106,T107,T110  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：frozen dev and lockbox results  
**输出**：all final figures/tables;source-data files;receipts

**执行命令**：

```bash
make figures && make tables
```

**验收标准**：Every panel and cell maps to command/run/data/claim; vector/600-dpi exports as applicable; no manual number editing; source data license checked

**失败回退**：Regenerate from code; remove unverifiable panels

### T112 — Build reproducibility containers and clean-room package

**依赖**：T104,T110,T111  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：code;locks;releases  
**输出**：containers;workflow;reproduction receipts;public package

**执行命令**：

```bash
make reproduce-clean
```

**验收标准**：Clean environment rebuilds all redistributable data and main results within tolerances; network-free benchmark grading works; three independent run receipts targeted

**失败回退**：Document nonredistributable rebuild steps; fix dependency/environment drift

### T113 — Run manuscript claim-to-evidence and language audit

**依赖**：T111,T112  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：all manuscripts;claim/evidence ledgers  
**输出**：FINAL_CLAIM_AUDIT;revised manuscripts

**执行命令**：

```bash
biointerfaceos claim audit-manuscripts --strict
```

**验收标准**：Every quantitative/scientific sentence linked; causal/mechanistic wording obeys gate; experimental validation wording absent; citations and dates verified

**失败回退**：Block submission until critical wording/evidence gaps fixed

### T114 — Run final project acceptance and release

**依赖**：T113  
**优先级**：P0  
**初始状态**：BLOCKED

**输入**：all mandatory artifacts  
**输出**：reports/FINAL_AUDIT.md;public release;final tag

**执行命令**：

```bash
biointerfaceos project accept --strict
```

**验收标准**：All mandatory tasks done/justifiably waived; G0-G10 evaluated; critical findings zero; public package license-safe; final tag/checksums generated

**失败回退**：Do not mark COMPLETE; publish partial validated artifacts and exact unmet gates
