# 第 3 章：从 CLI 到 Runtime（启动与组装）

这一章要解决的问题：**“我敲 `oh` 之后，代码到底是怎么一路走到 QueryEngine 的？”**

## 你将学会什么

- `src/openharness/cli.py` 的入口分流：交互模式 / print 模式 / backend-only / task-worker / resume
- `build_runtime()` 如何组装 RuntimeBundle：settings → plugins → mcp → tools → hooks → engine → commands
- RuntimeBundle 为什么要保存一堆”可刷新”的东西（settings_overrides / tool_metadata / app_state）

## 前置知识

- 第 1 章的目录全景图（知道 `cli.py`、`ui/`、`engine/` 的位置）
- 第 2 章的 Settings 优先级与 Profile 投影机制
- 了解 Python 的 `async/await` 基本概念（知道 `build_runtime()` 是异步函数）

## 关键文件（必读）

- `src/openharness/cli.py`：`main()`（Typer callback）
- `src/openharness/ui/app.py`：`run_repl()` / `run_print_mode()` / `run_task_worker()`
- `src/openharness/ui/runtime.py`：`build_runtime()` / `start_runtime()` / `close_runtime()`
- `src/openharness/ui/react_launcher.py`：React TUI 如何拉起 backend

## 启动路径总览（只记三条）

1) **交互模式（默认）**
- `cli.py: main()` → `ui/app.py: run_repl()` → React TUI 或 backend host

2) **非交互 print 模式**
- `cli.py: main(print_mode=...)` → `ui/app.py: run_print_mode()`
- 适合脚本/CI：把输出当成管道数据

3) **后台 task worker**
- `cli.py: main(task_worker=True)` → `ui/app.py: run_task_worker()`
- 用于后台 agent/task 子进程（stdin 驱动，一次性）

## build_runtime() 做了什么（按顺序拆解）

打开 `src/openharness/ui/runtime.py`，你会看到 `async def build_runtime(...)` 基本按这个顺序走：

1. 合并 settings（含 CLI overrides）得到最终 runtime settings
2. 解析 `cwd`，规范化 extra skill/plugin roots
3. `load_plugins(...)`（可扩展点：commands/hooks/skills/mcp servers）
4. 解析/创建 API client（`_resolve_api_client_from_settings`）
5. `McpClientManager(connect_all)`（连接 MCP 工具/资源）
6. `create_default_tool_registry(mcp_manager)`（工具注册）
7. `HookExecutor(...)`（hook reloader + 执行器）
8. `build_system_prompt(...)`（`src/openharness/prompts/system_prompt.py`，系统提示词拼装——把环境信息、工具列表、权限规则等组装成模型"看到的全部指令"）
9. 创建 `QueryEngine(...)`（核心循环入口）
10. 恢复 messages/tool_metadata（如果是 resume）
11. （可选）启动 docker sandbox
12. 返回 `RuntimeBundle(...)`（交互层用它来处理每一行输入）

你会发现 OpenHarness 的“架构味道”很清晰：
- runtime 负责把“配置/扩展/上下文”组装成可运行的对象图
- engine 负责对话循环
- UI/CLI 负责输入输出与交互

## 你可能会卡住的点（一步一步解释）

### 1）为什么 RuntimeBundle 里要放 `settings_overrides`？

因为设置来源很多（文件/环境/CLI），而交互过程中 `/model`、`/fast` 这类命令会刷新 UI 状态。
如果每次刷新都直接从文件读，就会把 CLI 参数覆盖掉。`settings_overrides` 就是为了解决“运行期有效但不落盘”的设置叠加层。

### 2）为什么 tool_metadata 里塞了 `session_id / mcp_manager / bridge_manager`？

这是 OpenHarness 的“跨工具共享上下文”的方式：
- tool 执行时会拿到 `ToolExecutionContext.metadata`
- 里面可以带 `mcp_manager` 等对象，避免全局单例到处飞

## 动手练习（最小代码单元）

运行：

```bash
python3 Study/exercises/ex03_backend_command.py
```

它演示 React TUI 如何通过 `build_backend_command()` 构造后端启动命令（不会真的启动 TUI）。

你需要完成脚本里的 TODO：
1. 增加一个参数 `--permission-mode plan`，观察 backend command 的变化
2. 把输出改成 JSON（字段：cwd/model/max_turns/base_url/permission_mode）

## 自测题（含标准答案）

### Q1：`build_runtime()` 最终要返回什么？为什么？
**A：**返回 `RuntimeBundle`，它封装了一次会话需要的核心对象（api_client/mcp/tools/hooks/engine/commands/app_state），让 UI/CLI 在“每次处理用户输入”时不必重新组装依赖。

### Q2：`run_repl()` 为什么分 `backend_only`？
**A：**React TUI 会在 Node/Ink 侧运行，它需要一个结构化 Python backend 进程做模型调用与工具执行；`backend_only` 允许只跑后端（给前端拉起或无 TTY 场景使用）。

### Q3（流程追踪题）：`build_runtime()` 中，以下组件的创建顺序是什么？
- A) QueryEngine
- B) ToolRegistry
- C) HookExecutor
- D) API Client
- E) McpClientManager

**A：** D → E → B → C → A。逻辑是：先有 API Client（连接模型），再有 MCP（外部工具），再创建工具注册表（包含内置+MCP工具），再创建 Hook 执行器，最后创建 QueryEngine（它需要前面所有组件）。

### Q4（判断题）：`settings_overrides` 和配置文件里的设置有什么区别？
**A：** `settings_overrides` 是运行期动态叠加的设置（如用户在交互中执行 `/model gpt-5.4`），不会写入磁盘。配置文件的设置是持久化的。两者在下次启动时，`settings_overrides` 会丢失，配置文件设置保留。

## 常见误区

1. **误区：以为 `build_runtime()` 只是简单的依赖注入**
   它实际上还包含网络连接（MCP server）、文件读取（skills/plugins）、系统提示词拼装等副作用操作，不是纯粹的对象组装。

2. **误区：以为 React TUI 和 Python backend 跑在同一个进程**
   React TUI（Node.js/Ink）和 Python backend 是两个进程，通过 JSON 协议通信。`build_backend_command()` 构造的就是 Python 子进程的启动命令。

3. **误区：混淆 `build_system_prompt()` 与用户输入**
   系统提示词是**框架自动构建的**，用户看不到也不应修改。它包含环境信息、可用工具列表、行为规则等，让模型知道"我在什么环境下工作、能做什么"。

