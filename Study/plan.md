# OpenHarness 学习计划（建议 10 章）

这份计划把 OpenHarness 拆成一条“从入口到核心循环，再到扩展点”的路线。你可以把它当成**读源码的地图**。

## 建议节奏（两种强度）

### A. 标准强度（10 天）
- 每天 1 章：读 30–60 分钟 + 跑练习 10–20 分钟 + 自测 10 分钟
- 第 10 天做综合验收

### B. 轻量强度（4 天）
- D1：第 1–3 章（入口与 Runtime）
- D2：第 4–6 章（Agent Loop + Messages + Tools）
- D3：第 7–8 章（Permissions + Hooks/Plugins/Skills）
- D4：第 9–10 章（Commands/Sessions + MCP/Tasks/UI/Swarm）+ 综合验收

## 章节目录（学习目标 → 关键文件 → 练习）

1. `Study/chapters/01_repo_map.md`
   - 目标：建立项目全景图，知道“从哪开始读”
   - 练习：`Study/exercises/ex01_repo_map.py`
2. `Study/chapters/02_settings_provider.md`
   - 目标：看懂 Settings / Profile / Provider/Auth 的业务逻辑
   - 练习：`Study/exercises/ex02_settings_provider.py`
3. `Study/chapters/03_runtime_startup.md`
   - 目标：掌握 CLI → UI → RuntimeBundle 的组装流程
   - 练习：`Study/exercises/ex03_backend_command.py`
4. `Study/chapters/04_agent_loop.md`
   - 目标：掌握 run_query 的“工具调用闭环”
   - 练习：`Study/exercises/ex04_agent_loop_fake.py`
5. `Study/chapters/05_messages_events.md`
   - 目标：掌握消息块（Text/ToolUse/ToolResult）与流式事件
   - 练习：`Study/exercises/ex05_messages_events.py`
6. `Study/chapters/06_tools.md`
   - 目标：掌握 BaseTool/ToolRegistry、Schema、read-only 语义
   - 练习：`Study/exercises/ex06_tools_schema.py`
7. `Study/chapters/07_permissions_sandbox.md`
   - 目标：掌握权限模式、路径规则、敏感路径防护、（可选）沙箱入口
   - 练习：`Study/exercises/ex07_permissions.py`
8. `Study/chapters/08_hooks_plugins_skills.md`
   - 目标：掌握 hooks + plugins + skills 的扩展点与加载流程
   - 练习：`Study/exercises/ex08_plugins_skills_hooks.py`
9. `Study/chapters/09_commands_memory_sessions.md`
   - 目标：掌握 slash commands、session snapshot、memory、microcompact
   - 练习：`Study/exercises/ex09_memory_sessions_compact.py`
10. `Study/chapters/10_mcp_tasks_ui_swarm.md`
   - 目标：掌握 MCP、后台任务、UI 协议、多 Agent/Swarm 的“接口层”
   - 练习：`Study/exercises/ex10_mcp_tasks_ui_swarm.py`

综合验收：
- `Study/chapters/99_final_assessment.md`

## 完成标准（你可以用来判断”我学会了吗？”）

当你能够做到下面 5 件事，就算入门成功：
1. 能从 `src/openharness/cli.py` 一路追到 `run_query()`，讲清楚每一步干什么
2. 能解释：**工具调用闭环**为什么要分”模型决定 what，harness 负责 how”
3. 能默写 `_execute_tool_call` 的 9 步执行链（PreHook → Lookup → Validate → PathResolve → CmdExtract → Permission → Execute → Carryover → PostHook）
4. 能写一个最小工具（BaseTool + Pydantic input_model），并被 `ToolRegistry` 注册、执行
5. 能解释至少 3 个扩展点：`/commands`、`hooks`、`plugins/skills/MCP`、`tasks`、`swarm`

