# 知序 ZhiXu · 把散落的资料组装成 AI 能直接用的上下文

> 第六届 OceanBase 数据库大赛 · Qoder 生态题（20 分）
>
> 用 Qoder 开发，核心记忆、检索与上下文组装全部由 **PowerContext 1.2.0 Server** 完成。

## 项目网站与仓库

| 项目 | 地址 |
|---|---|
| 网站（Qoder Sites，任何人可访问） | <https://zhixu-context-lj5e49q4pu7.qoder.website> |
| 提交仓库 | <https://github.com/cheng200606/powercontext2026> |
| 提交分支 | `2026-competition-ecosystem`（基于官方同名分支，项目资产在 `qoder/`） |
| 提交 commit | 见测评平台填写值（`2026-competition-ecosystem` 的最新提交） |
| 公开镜像（便于浏览） | <https://github.com/cheng200606/zhixu-qoder> |
| Qoder 账号 UID | `aliyun-1322590677332578` |

提交仓库为比赛私有仓库，评测方按参赛信息中登记的 PAT 读取；上表中的公开镜像与本项目内容相同，方便直接浏览代码。

## 解决什么问题

备赛、做项目时，资料散落在笔记、文档、会议纪要里。要用 AI 时，要么反复手工复制，要么让模型在没有出处的情况下编造。

知序把资料写进 **PowerContext 长期记忆**，检索时返回可回查的 `citation`，再按 UTF-8 字节预算调用 `prepare_context`，生成一段带引用、可直接粘贴给任意 AI 的上下文包。

三个关键动作都是真实 API 调用，不是本地拼装：

1. 导入 → `PowerContextClient.remember_memory`（写入 Memory 条目）
2. 检索 → `PowerContextClient.search_memory`（服务端 FTS / auto 检索，返回 citation）
3. 组装 → `PowerContextClient.prepare_context`（服务端按预算裁剪，返回 `powercontext.prepared-context.v1`）

## 架构

```
浏览器（原生 HTML/CSS/JS）
        │  /api/*
        ▼
知序 FastAPI（127.0.0.1:18000）
        │  powercontext.client（HTTP）
        ▼
PowerContext Server 1.2.0（127.0.0.1:18080）
        │
        ▼
SQLite 持久化（data/powercontext.db）
```

- Scope = 知识库，Memory = 资料条目，PreparedContext = 上下文包。
- 没有本地 JSON / 内存索引 / 第二套数据库；条目列表、检索、引用回查都来自 PowerContext。
- 本机未配置 Embedding 模型，因此检索方式为 `auto` / `fts`。配置模型后，同一段 `mode="auto"` 代码会自动使用向量或混合检索，应用无需修改。

## 运行说明

环境：Python 3.12（3.11+ 均可）、Windows / macOS / Linux。首次安装需要联网下载依赖。

```bash
git clone https://github.com/cheng200606/zhixu-qoder.git
cd zhixu-qoder
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

上面的公开镜像与本项目完全同源。若使用提交仓库，则下载 `2026-competition-ecosystem` 分支后在 `qoder/` 目录执行同样的命令：

```bash
git clone -b 2026-competition-ecosystem https://github.com/cheng200606/powercontext2026.git
cd powercontext2026/qoder
```

`run.py` 会同时启动 PowerContext Server（18080）和知序（18000），并打开浏览器；按 `Ctrl+C` 一起停止。

打开 <http://127.0.0.1:18000> 后：

1. 点击左下「一键载入示例知识库」，会创建 `OceanBase 大赛资料库` 并写入 8 篇示例资料。
2. 在搜索框输入 `上下文 引用`，回车。
3. 切到「上下文包」，预算保持 2400 bytes，点「组装上下文」。
4. 点「复制」即可把带引用的上下文粘贴给任意 AI。
5. 也可以「导入」自己的 txt / md / pdf；PDF 按页写入。

数据保存在 `data/powercontext.db`。关闭进程再启动，同一知识库与资料仍在。

### 分开启动（便于观察日志）

```bash
python -m zhixu.pc_server    # 终端 1：PowerContext Server
python -m zhixu.app          # 终端 2：知序
```

PowerContext 原生 API 文档：<http://127.0.0.1:18080/docs>

## 验证样例

自动化验收（会真实启动两个服务、写入 8 篇资料、检索、组装上下文、重启 Server 再检索）：

```bash
python verify.py
```

本次运行结果（完整日志见 [`docs/verify-log.txt`](docs/verify-log.txt)）：

```text
[PASS] PowerContext Server 就绪
[PASS] 知序 Web 应用就绪
[PASS] 状态接口返回连接成功
[PASS] 后端为 PowerContext 1.2.0 且支持 FTS — version=1.2.0 modes=['auto', 'fts']
[PASS] 创建 Scope
[PASS] 导入 8 篇示例资料到 PowerContext 记忆 — {'seeded': 8, 'skipped': False, 'count': 8}
[PASS] 条目列表可回查 — count=8
[PASS] FTS 检索命中并返回 citation — mode=fts hits=5
[PASS] 检索引用可回查到已存条目
[PASS] PreparedContext 状态 ready 且不超预算 — bytes=1800
[PASS] 上下文包含引用条目 — citations=1
[PASS] Server 重启就绪
[PASS] 重启后同一 Scope 仍可检索 — hits=5
[PASS] 重启后知识库仍在
[PASS] SQLite 数据库文件已落盘
通过 15 项，失败 0 项。
```

手工验证一组（初始数据 → 操作 → 预期）：

| 步骤 | 操作 | 预期 |
|---|---|---|
| 1 | 点击「一键载入示例知识库」 | 左侧资料数变为 8，提示「已导入 8 篇示例资料」 |
| 2 | 搜索 `上下文 引用` | 返回多条命中，每条带 `score`、`FTS` 标记和 `mem_ent_…` 引用 ID |
| 3 | 切到「上下文包」，预算 2400，点「组装上下文」 | 状态 `ready · 2xxx bytes · 1 条引用`，右侧引用清单显示 `RAG 设计笔记` |
| 4 | 点「复制」 | 剪贴板得到 `BEGIN_POWERCONTEXT_PREPARED_CONTEXT_V1` 包裹的带引用上下文 |
| 5 | 关闭进程后重新 `python run.py`，刷新页面 | 知识库与 8 条资料仍在，重复步骤 2 仍能命中 |
| 6 | 切到「原始响应」 | 显示知序收到的 PowerContext 原始 JSON（含 citation / content_bytes） |

界面证据：

| 截图 | 内容 |
|---|---|
| [`01-home.png`](https://zhixu-context-lj5e49q4pu7.qoder.website/assets/01-home.png) | 知识库、8 条资料、PowerContext 连接状态 |
| [`02-search.png`](https://zhixu-context-lj5e49q4pu7.qoder.website/assets/02-search.png) | FTS 检索结果与引用 ID |
| [`03-context.png`](https://zhixu-context-lj5e49q4pu7.qoder.website/assets/03-context.png) | PreparedContext 内容、字节数与引用清单 |
| [`04-raw.png`](https://zhixu-context-lj5e49q4pu7.qoder.website/assets/04-raw.png) | PowerContext 原始响应 |
| [`05-import.png`](https://zhixu-context-lj5e49q4pu7.qoder.website/assets/05-import.png) | 资料导入（txt / md / pdf） |

## 真实接入证据

- 状态接口 `GET /api/status` 返回 `pc_version=1.2.0`、`search_modes=["auto","fts"]`、数据库路径；界面顶部显示「PowerContext 已连接」。
- 检索结果中的 `citation.entry_id` 与「资料」列表中的条目一一对应，可在 PowerContext 的 `/v1/memory/entries/list` 回查。
- 上下文包直接来自 `PreparedContext.content`，含 `BEGIN_POWERCONTEXT_PREPARED_CONTEXT_V1` 标记与 `content_bytes`，没有二次拼接。
- `docs/verify-log.txt` 同时保留 PowerContext Server 的请求日志（`POST /v1/memory/remember`、`POST /v1/memory/search`、`POST /v1/context/prepare`）。

## Qoder 开发记录

- 开发工具：Qoder Desktop（个人账号，非企业账号）
- 记录文件：[`docs/qoder-dev-record.md`](docs/qoder-dev-record.md)，含关键环节对话截图与账号 UID
- 界面截图：托管在网站的 `assets/` 目录，README 与开发记录直接引用其公开地址
- 网站：通过 Qoder Sites 发布，线上页面即最终交付

## 目录结构

```
.
├── run.py                 # 一键启动两个服务
├── verify.py              # 端到端验收脚本
├── requirements.txt
├── zhixu/
│   ├── pc_server.py       # 真实 PowerContext Server（SQLite）
│   ├── app.py             # FastAPI：导入、检索、上下文、状态
│   └── static/            # 原生前端
├── samples/               # 8 篇示例资料
└── docs/
    ├── verify-log.txt
    └── qoder-dev-record.md
```
