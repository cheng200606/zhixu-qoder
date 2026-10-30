# AI 函数增强：六个子题与验收口径

seekdb 的 AI 函数题不是考察模型效果，而是考察 SQL 引擎里的参数处理、请求构造和结果校验。组委会提供 Mock AI Service，监听 0.0.0.0:8000，测试全部打向本地 Mock。

第一个子题是 AI_PROMPT 的类型与模板：JSON 参数要序列化后替换占位符，同一个占位符出现两次都要替换；非法下标要报错；嵌套 Prompt、Unicode 和转义不能乱码；LONGTEXT 模板配 TEXT 参数也要工作。

第二个子题是 AI_EMBED 单行语义：返回值必须是合法 JSON 数组；不传 dimension 时用模型默认维度；传了 dimension 要校验请求维度与返回维度一致，不一致就报错。

第三个子题是 AI_COMPLETE 的请求与响应：第三个参数为 NULL 时走默认配置；JSON config 要真正下发到请求体，temperature 和 max_tokens 不能丢；空响应必须报错，不能返回空串。

第四个子题是 Ollama Provider：endpoint 允许 access_key 为空；ollama、OLLAMA、Ollama 三种大小写都要识别并落库；请求要走 Ollama 原生的 /api/generate 和 /api/embed，不能套 OpenAI 的 chat/completions 结构。

第五个子题是 AI_RERANK 正确性：输入既可能是字符串数组，也可能是对象数组；对象数组要按指定字段取文本；返回的 id 要映射回原始下标或原始 id；排序必须稳定。

第六个子题是 AI_EMBED 跨行批量：同一批扫描中的多行输入要合并成一个请求；NULL 行不进请求也不占位；响应乱序时按 index 映射回原行；结果顺序与扫描行对齐。

实现硬约束：必须在 SQL 引擎内完成，不得在应用层绕过；禁止对模型名、输入和响应硬编码；异常输入不得崩溃、错位或泄漏。
