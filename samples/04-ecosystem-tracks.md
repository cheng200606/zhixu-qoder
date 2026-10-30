# 生态题清单与提交材料

生态题共 7 个方向，每个 20 分，合计 140 分。所有生态题都基于 2026-competition-ecosystem 分支，资产放在对应目录，提交仓库 URL、分支和 commit。

AMD 赛道做 hipVS 加速 CAGRA 构建，必须基于 V5 冻结 commit，提交带令牌的仓库地址，硬门槛包括编译、GPU 抽检、召回率、显存不超基线 1.25 倍。

MiniMax 赛道做 SDD 上下文管理模块：导入规格、代码和测试资料，按任务选出上下文，交给 MiniMax 完成一次真实代码修改，再跑功能与回归测试，并保存任务状态。材料放 minimax 目录。

Qoder 赛道用 Qoder 作为主要开发工具做提效项目，核心功能用 seekdb 或 PowerContext 实现，最后用 Qoder Sites 发布公开网站。提交内容：网站网址、代码仓库、运行说明、验证样例、Qoder 开发记录（对话截图或录屏加账号 UID）。网站必须任何人可访问，内容要与代码一致，项目要能跑起来，不能用自制 SQLite 或内存冒充 seekdb、PowerContext。

阶跃星辰赛道做浏览器端迷你知识库：本地 embedding、写入 seekdb、混合检索必须由 seekdb 完成，禁止云端推理和前端拼接两路结果。

Dify 赛道做有趣的智能应用，实际接入 seekdb 或 PowerContext，提交可导入的 DSL、运行说明和完整验证样例。

高德地图赛道只交一个 SKILL.md：说明如何使用地点搜索和步行路线规划，给出筛选规则、回答格式和失败处理话术，文件里不能写 API Key。

魔搭社区赛道最简单：上传一个自己写的 Skill，提交它的网址或编号，不要交主页或账号 ID。
