# Study/exercises — 每章最小可运行练习

从仓库根目录运行，例如：

```bash
python3 Study/exercises/ex01_repo_map.py
```

## 约定

- 脚本会自动把 `src/` 加入 `sys.path`，方便直接 import 本项目模块
- 默认不需要 API Key，不会发起真实模型调用
- 带 `TODO` 的地方是"你要动手改一改"的练习点（脚本本身仍可直接运行）
- 每个脚本末尾有"自我验证"提示，帮你判断是否真的理解了

## 练习清单与对应章节

| 练习 | 对应章节 | 核心验证点 |
|------|---------|-----------|
| ex01_repo_map.py | 第 1 章 | 你能说出每个子模块在哪、有多大 |
| ex02_settings_provider.py | 第 2 章 | 你理解 Settings 四层优先级和 profile 投影 |
| ex03_backend_command.py | 第 3 章 | 你知道 React TUI 如何拉起 Python backend |
| ex04_agent_loop_fake.py | 第 4 章 | **最重要**：你亲眼看到工具调用闭环的事件流 |
| ex05_messages_events.py | 第 5 章 | 你能手动构造 ConversationMessage 并理解角色/块的对应关系 |
| ex06_tools_schema.py | 第 6 章 | 你能写一个最小工具，理解 schema 对模型的作用 |
| ex07_permissions.py | 第 7 章 | 你能预测不同模式/路径下的权限决策结果 |
| ex08_plugins_skills_hooks.py | 第 8 章 | 你理解插件结构和 SKILL.md 的解析方式 |
| ex09_memory_sessions_compact.py | 第 9 章 | 你能解释 microcompact 的效果和 session 持久化白名单 |
| ex10_mcp_tasks_ui_swarm.py | 第 10 章 | 你了解 MCP 配置、后台任务和 coordinator 通知结构 |

## 学习建议

1. **先跑一遍原始脚本**：看看输出是什么，对照章节内容理解
2. **再做 TODO 练习**：动手修改代码，验证你的理解
3. **最后对照自我验证**：脚本末尾的验证提示帮你判断是否达标
4. **ex04 是核心**：如果只有时间做一个练习，就做 ex04
