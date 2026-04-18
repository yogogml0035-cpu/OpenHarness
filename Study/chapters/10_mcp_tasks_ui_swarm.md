# 第 10 章：MCP / Tasks / UI 协议 / Multi-Agent（高级接口层）

这一章要解决的问题：**”OpenHarness 如何接入外部工具(MCP)、管理后台任务、把事件发给前端，以及多 Agent 协作的接口是什么？”**

这章更偏”接口层”，你可以先理解轮廓，不必一次吃透实现细节。

## 你将学会什么

- MCP：把外部工具/资源以统一接口暴露给模型
- Tasks：后台执行 shell/agent 子进程，并可读写输出
- UI 协议：React TUI 前后端如何用结构化消息通信（Pydantic models）
- Multi-agent：coordinator/swarm 的核心概念（工具名、通知结构）
- Channels：多渠道接入的架构设计

## 前置知识

- 第 3 章的 `build_runtime()` 流程（MCP 和 Tasks 在其中被初始化）
- 第 6 章的 ToolRegistry（MCP 工具通过 McpToolAdapter 注册到 registry）
- 了解 JSON-RPC 或类似协议概念（MCP 基于结构化消息通信）

## 关键文件（必读）

- MCP：`src/openharness/mcp/client.py`、`src/openharness/mcp/types.py`、`src/openharness/mcp/config.py`
- Tasks：`src/openharness/tasks/manager.py`、`src/openharness/tasks/types.py`
- UI protocol：`src/openharness/ui/protocol.py`
- Multi-agent/coordinator：`src/openharness/coordinator/coordinator_mode.py`
- Channels：`src/openharness/channels/adapter.py`、`src/openharness/channels/impl/base.py`
- Swarm：`src/openharness/swarm/registry.py`、`src/openharness/swarm/types.py`

## MCP：外部工具的统一接入层

`McpClientManager`：
- 连接多个 MCP server（stdio/http 两种传输方式）
- 拉取 tools/resources
- 提供 `call_tool()/read_resource()` 给工具适配器使用

### MCP 工具是怎么变成"和内置工具一样"的？

这是一个关键的架构设计：

```
MCP server → McpClientManager.list_tools() → 
  create_default_tool_registry() → McpToolAdapter(mcp_tool) → 
    ToolRegistry.register() → 模型像调用普通工具一样调用
```

`McpToolAdapter` 是一个适配器（Adapter 模式），它把 MCP 工具包装成 `BaseTool` 接口，使得 `run_query` 里的工具执行链对 MCP 工具完全透明。

## Tasks：后台任务管理

`BackgroundTaskManager`：
- 创建任务（shell/agent 两种类型）
- 监控进程状态（running/completed/failed）
- 输出落盘（写入文件），支持 tail/read
- agent 任务支持 stdin 写入（必要时自动重启）

### 为什么需要后台任务？

某些操作耗时很长（如编译、测试运行、大规模代码分析），不适合阻塞 Agent Loop。后台任务允许模型"发起任务 → 继续对话 → 稍后检查结果"。

## UI 协议：前后端结构化通信

React TUI 用 JSON 通信，后端用 `FrontendRequest/BackendEvent` 做结构校验与演进。

### 为什么用 Pydantic model 而不是裸 JSON？

- **类型安全**：前后端 schema 不匹配时在 Python 侧就能发现
- **版本演进**：新增字段可以给默认值，不破坏旧版前端
- **文档自动生成**：Pydantic model 自带 JSON Schema 输出

## Channels：多渠道接入架构

OpenHarness 支持通过多种渠道（Slack/Discord/Telegram/飞书/钉钉/QQ/微信等）接入。架构设计：

- `channels/adapter.py`：统一的渠道适配接口
- `channels/impl/base.py`：基类，定义了 `send/receive/webhook` 等方法
- `channels/bus/`：事件总线，解耦渠道消息与核心处理
- 每个渠道实现（如 `slack.py`、`telegram.py`）只需实现基类方法

> **注意**：channels 模块主要面向"把 OpenHarness 部署为服务/Bot"的场景，不影响本地 CLI/TUI 使用。初学阶段了解它的存在即可。

## Multi-Agent / Swarm

coordinator 和 swarm 模块提供了多 Agent 协作的能力：

- `coordinator/coordinator_mode.py`：TaskNotification 结构（XML 格式的任务通知）
- `swarm/`：多 Agent 生命周期管理、权限同步、工作树隔离
  - `registry.py`：Agent 注册与发现
  - `spawn_utils.py`：子 Agent 启动工具
  - `permission_sync.py`：跨 Agent 权限同步
  - `worktree.py`：Git 工作树隔离（每个 Agent 在独立分支工作）

## 动手练习（最小代码单元）

运行：

```bash
python3 Study/exercises/ex10_mcp_tasks_ui_swarm.py
```

脚本会演示：
1. 在“空配置”下初始化 MCP manager（不连接外部 server）
2. 构造/校验一条 UI `FrontendRequest`，以及一条 `BackendEvent`
3. 在临时 data dir 下跑一个后台 shell task，并读取输出
4. 解析/格式化 `task-notification` XML（来自 coordinator_mode）

你需要完成脚本里的 TODO：
1. 把 task 的命令从 `echo` 改成 `python3 -c 'print(...)'`，并解释为什么输出仍能被读到
2. 自己构造一个 `task-notification`，用 parse 再 format，验证“结构化协议”是一致的

## 自测题（含标准答案）

### Q1：MCP tools 是怎么进入 ToolRegistry 的？
**A：**runtime 在 `create_default_tool_registry(mcp_manager)` 时，会遍历 `mcp_manager.list_tools()`，为每个 MCP tool 注册 `McpToolAdapter`，从而让模型像调用普通工具一样调用外部 MCP 工具。

### Q2：为什么后台 task 输出要落到文件，而不是只存在内存里？
**A：**文件输出可以跨 UI 刷新/跨进程读取，便于 tail、调试和恢复；同时也避免长输出占用内存。

### Q3（架构判断题）：MCP 工具和内置工具在 `run_query` 的工具执行链中有什么区别？
**A：** 没有区别。MCP 工具通过 `McpToolAdapter` 被包装成 `BaseTool` 接口后，注册到同一个 `ToolRegistry` 中。`run_query` 调用时不区分来源，全部走同一条 PreHook → Permission → Execute → PostHook 链。这就是 Adapter 模式的价值。

### Q4（推演题）：如果一个 MCP server 在会话中途断开连接，会发生什么？
**A：**
1. `McpClientManager` 检测到连接断开
2. 对应的 MCP 工具从 `ToolRegistry` 中移除（或标记为不可用）
3. 如果模型尝试调用已断开的 MCP 工具，`tool_registry.get(name)` 返回 None → 返回 "Unknown tool" 错误
4. 模型收到错误后会调整策略（使用其他工具或告知用户）

### Q5（模块关系题）：Channels 模块与 UI 协议模块的区别是什么？
**A：**
- **UI 协议**（`ui/protocol.py`）：面向本地 React TUI 前端，同一台机器上的进程间通信
- **Channels**（`channels/`）：面向远程渠道（Slack/Telegram 等），通过网络 API/Webhook 通信
- 两者都是"消息输入输出"的适配层，但面向的用户场景和通信方式完全不同

## 常见误区

1. **误区：以为 MCP 是 OpenHarness 独创的协议**
   MCP（Model Context Protocol）是一个开放协议标准，不是 OpenHarness 发明的。OpenHarness 实现了 MCP 客户端，用于接入任何兼容的 MCP server。

2. **误区：以为后台 task 和 Agent Loop 是同一个东西**
   Agent Loop（run_query）是前台的对话循环；后台 task 是独立的子进程，可以是 shell 命令或另一个 agent 实例。两者互不阻塞。

3. **误区：以为 swarm 就是"多个 agent 同时运行"**
   swarm 更像是"有组织的协作"：包含注册/发现、权限同步、工作树隔离（每个 agent 在自己的 git 分支工作）。不是简单的并发，而是有编排的分工。

