# Qoder 开发记录

> 第六届 OceanBase 数据库大赛 · Qoder 生态题
> 项目：知序 ZhiXu · 把散落的资料组装成 AI 能直接用的上下文

## 账号与开发环境

| 项目 | 内容 |
|---|---|
| 开发工具 | Qoder Desktop（Windows） |
| 账号类型 | 个人账号（非企业账号） |
| 账号显示名 | 夏程 |
| Qoder 账号 UID | `待填入`（在 Qoder 客户端「设置 → 账号」中查看 UID，填入此处与提交表单） |
| 会话标题 | 完成Qoder的赛题，按照要求进行提交 |
| 开发日期 | 2026-10-30 |

## 会话截图

会话全程在 Qoder Desktop 中完成，标题为「完成Qoder的赛题，按照要求进行提交」。

![Qoder 会话：选型、验证 PowerContext、搭建知序](https://zhixu-context-lj5e49q4pu7.qoder.website/assets/qoder-chat-01.png)

截图中的关键节点：

- 「Qoder 赛道要求做真实项目并发布站点。先摸清本地可用的运行环境（PowerContext / seekdb）和仓库状态。」
- 「仓库已有 2026-competition 分支和远端。现在确认 PowerContext 能否在本地真实跑起来，并查看其对外 API。」
- 「Qoder Sites 已登录（暂无站点），可以发布。」
- 「本地验证通过：PowerContext 1.2.0 的 Server 在 Windows 上可用，SQLite 持久化、FTS 检索、上下文组装和重启恢复都正常。现在开始搭『知序』项目。」
- 「应用框架完成，先跑端到端验收脚本，发现接口问题就修。」

会话中 Qoder 连续执行了多组工具调用（截图可见「执行工具 5 次 / 2 次 / 14 次」「执行工具 25 次，其中 1 次失败」），并显示「步骤 2/5 · 29 个文件已修改 +3,754」，对应本仓库新增的应用、验证脚本、样例资料、网站源码与文档。

## 网站发布截图

网站通过 Qoder Sites 发布，站点卡片显示「知序 ZhiXu · 5分钟前更新 · 已发布」，访问权限为「任何人可访问」。

![Qoder Sites 中已发布的知序站点](https://zhixu-context-lj5e49q4pu7.qoder.website/assets/qoder-sites-published.png)

## 关键开发环节

1. **技术选型。** 先验证本机能否真实运行 seekdb 与 PowerContext。seekdb 在本机无法完成构建/启动；PowerContext 1.2.0 可直接安装并在 Windows 上以 SQLite 持久化运行。最终选择 PowerContext 作为唯一的记忆与上下文后端，未使用 SQLite/JSON/内存等替代实现。
2. **摸清真实 API。** 阅读 `powercontext` 客户端与服务端接口，确认 `remember_memory`、`search_memory`、`prepare_context` 的请求/响应结构，以及 citation、`prepared-context.v1` 的实际字段。
3. **搭建应用。** 知序由 FastAPI 后端与原生前端组成：导入走 `remember_memory`，检索走服务端 FTS/auto 并回传 citation，上下文包直接使用 `PreparedContext.content`。Scopes 作为知识库，Memory 作为资料条目。
4. **端到端验收。** 编写 `verify.py`，真实启动两个服务、写入 8 篇资料、检索、组装上下文，再重启 Server 验证持久化，15 项全部通过，日志见 `verify-log.txt`。
5. **网站与发布。** 用 Qoder 生成并校对展示站点（桌面与移动端），通过 Qoder Sites 发布为公开站点，并验证线上 HTML、样式、图片均返回 200。
6. **材料整理。** README、验证样例、截图与开发记录均在 Qoder 会话内同步完成。

## 使用数据（会话内可见）

- Qoder 会话内共出现多轮工具执行记录（5、2、14、10、5、25 次等），包含终端命令、文件读写、MCP Sites 工具调用。
- 网站发布与状态查询通过 Qoder Sites 的 MCP 工具完成（`prepare_site`、`get_publish_status`、`publish_site`、`get_site_access`）。
- 界面校验使用无头浏览器截图，覆盖桌面与移动端；线上页面控制台无异常、无横向溢出。

## 说明

- 截图均取自 Qoder Desktop 本机会话与 Sites 面板，未包含聊天记录以外的个人数据。
- Qoder 账号 UID 需从客户端账号设置中读取；本文件与提交表单需填入同一个 UID。
