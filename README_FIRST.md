# BioInterfaceOS Codex 执行包：先读这里

这是一个供 Codex 持续执行医学材料 AI-for-Science 项目的仓库级任务合同。

## 文件用途

- `GOAL.md`：完整研究、数据、数学模型、Agent、验证和投稿合同；
- `TASKS.md`：115 个任务的人类可读版本；
- `TASKS.tsv`：Codex 更新状态的机器可读任务 DAG；
- `AGENTS.md`：Codex 每次进入仓库都应遵守的长期纪律；
- `PLANS.md`：复杂任务的 ExecPlan 规范；
- `PROJECT_STATE.yaml`：当前项目状态；
- `CODEX_START_PROMPT.md`：启动时粘贴给 Codex；
- `scripts/validate_execution_pack.py`：首先运行的一致性检查；
- `scripts/start_codex.sh`：在已安装并登录 Codex CLI 的机器上启动。

## 最简单用法

```bash
unzip BioInterfaceOS_Codex_Execution_Pack.zip
cd BioInterfaceOS_Codex_Execution_Pack
python scripts/validate_execution_pack.py
codex
```

进入 Codex 后粘贴 `CODEX_START_PROMPT.md`。

也可在审阅权限配置后运行：

```bash
./scripts/start_codex.sh
```

不要在本机使用无 sandbox 的高风险全权限参数。数据下载只允许访问匿名、无需注册/申请/API key 的公共来源；锁定时期数据在开发冻结前只能编目元数据。
