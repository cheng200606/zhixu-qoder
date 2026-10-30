# seekdb 是什么：一个为 AI 应用准备的嵌入式数据库

seekdb 是 OceanBase 推出的轻量数据库，定位是「AI 应用的数据底座」。它兼容 MySQL 协议，默认监听 127.0.0.1:2881，可以用任何 MySQL 客户端连接后执行 `SELECT 1;` 验证。

它同时支持关系表、向量索引和全文索引。向量列可以建 HNSW / VSAG 索引，文本列可以做 TOKENIZE 与 MATCH 全文检索，因此同一个 SQL 里既能按标量过滤，也能做语义相似度召回。

部署方式有两种：直接下载 release 包，或者从源码编译。Linux 下执行 `./build.sh --init --make -j16`，产物在 `build_release/src/observer/seekdb`，启动命令是 `./seekdb --base-dir=<空目录> --nodaemon`。

最小验证流程：启动实例，用 mysql 客户端连接 2881 端口，建一张带向量列的表，插入几条记录，然后执行 `SELECT 1;` 和一次向量距离排序查询。

对于只做演示的 AI 应用，嵌入式部署最省事：不需要额外集群，数据落在本地目录，重启后数据仍在。需要注意 Windows 只能部分编译，正式构建建议用 Ubuntu 22.04 x86_64。

遥测 ID 位于运行目录的 `run/telemetry.json`，字段是 `content.id`。这个 ID 用于大赛部署题提交，不要把它和账号 ID 混淆。
