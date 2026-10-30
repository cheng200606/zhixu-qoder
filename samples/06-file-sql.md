# 文件即数据库：read_csv、glob 与 COPY TO

这道题要在 seekdb 里实现文件表函数，让 SQL 可以直接查询 CSV、JSONL 和 Parquet 文件，不经过外部引擎。

需要实现的接口包括 read_csv、read_json（read_ndjson）、read_parquet、glob() 以及 COPY ... TO 导出。功能默认关闭，执行 `SET enable_file_sql=on` 后才可用，并且仍要通过 secure_file_priv 路径校验。

Schema 自动推断支持的列类型有 BIGINT、DOUBLE、BOOLEAN、VARCHAR、DATE、DATETIME 和 NULL。推断必须基于全量数据，sample_size 只接受 -1，传其他值要报错。

CSV 语义要跟 csv.reader 一致：引号、转义、CRLF、UTF-8、字段内换行都要正确处理；重复表头自动加 __2 后缀；空行忽略；坏行要报错，不能静默跳过。

JSONL 不同行字段不同时，输出取并集，缺失字段补 NULL。Parquet 要读 Footer 和 Row Group，支持列裁剪和多 Row Group 扫描。

红线有三条：禁止用 DuckDB、SQLite、Polars 等外部引擎代执行，否则整题 0 分；不得绕过 secure_file_priv 或突破只读边界，否则安全项 0 分；流式扫描不得把整个文件物化到内存，OOM 直接判失败。

测试入口是 file_sql_basic.test，数据放在 file_sql/data 目录。验收覆盖默认关闭、开启后可用、非法参数、全类型 CSV、聚合、JSONL 并集、DESCRIBE、Parquet、glob 和 COPY TO。
