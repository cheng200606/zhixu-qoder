# PowerContext：让上下文跨会话交接

PowerContext 解决的问题是：工作做到一半交给另一个人或另一个 Agent 时，之前的推理、决定和约束往往留在旧对话里。PowerContext 把这些信息保存成可检索、可回查的长期记忆。

核心概念有三个。Scope 是工作范围，所有记忆都归属于某个 scope，不同项目之间天然隔离。Memory 是长期记忆条目，每条都有 kind、正文和引用（citation），支持修订与停用，历史版本不会消失。PreparedContext 是给模型的一轮上下文，服务端按查询和 UTF-8 字节预算挑选条目，输出带引用、可直接放进模型消息的文本。

检索支持 FTS 全文检索，也可以配置 Embedding 后启用向量与混合检索。没有配置模型时，FTS 仍然可用，适合做本地知识库和演示。

引用是 PowerContext 的关键设计：每条记忆都有 entry_id 与 entry_version_id，检索结果和 PreparedContext 都会带上 citation。应用可以据此回查原文，而不是相信模型复述。

持久化由服务端负责。默认可以用 SQLite 后端，适合单机应用；也可以连接 OceanBase / seekdb。服务重启后，同一个 scope 的 Memory 仍然可读，这正是「跨会话交接」的基础。

Python 客户端入口是 `PowerContextClient(base_url)`，常用方法包括 `create_scope`、`remember_memory`、`search_memory`、`prepare_context` 和 `list_memory_entries`。
