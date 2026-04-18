# 第 4 章：Agent Loop 核心（run_query / QueryEngine）

这一章要解决的问题：**“工具调用闭环到底怎么实现？为什么它是整个项目的‘心脏’？”**

## 你将学会什么

- QueryEngine 的职责边界：保存消息历史 + 调用 run_query
- run_query 的循环结构：流式模型输出 → 识别 tool_use → 执行工具 → tool_result 回填 → 继续
- 工具执行链：Hook(Pre) → Permission → Tool.execute → CarryoverRecord → Hook(Post)

## 前置知识

- 第 1-3 章的全部内容（知道从 CLI 到 RuntimeBundle 的路径）
- 理解 Python `async for` 和 `AsyncIterator`（run_query 是一个异步生成器）
- 知道 `asyncio.gather()` 可以并发执行多个协程

## 关键文件（必读）

- `src/openharness/engine/query_engine.py`
- `src/openharness/engine/query.py`
- `src/openharness/engine/stream_events.py`
- `src/openharness/engine/messages.py`

## 先建立“两个世界”的概念

OpenHarness 把系统分成两个世界：

1) **模型世界**（Model decides）
- 产出：文本增量（delta）与工具调用（tool_use）

2) **执行世界**（Harness executes）
- 产出：工具结果（tool_result）
- 保障：权限、敏感路径保护、hooks、并发执行、可观测事件流

这就是“模型负责 what、harness 负责 how”落到代码的形态。

## QueryEngine：它只是“历史 + 入口”

打开 `src/openharness/engine/query_engine.py`，抓住这两点就够：

- `submit_message(prompt)`：把 user message append 到历史，然后 build QueryContext，调用 `run_query(context, messages)`
- `continue_pending()`：当上次停在“工具结果已产生，但模型还没来得及回话”时继续跑

## run_query：核心循环（建议你背下来）

打开 `src/openharness/engine/query.py`，重点看 `async def run_query(...)`：

每个 turn 大致是：

1.（可选）auto-compact（避免上下文太长）
2. 调 `api_client.stream_message(...)`，流式产出事件
3. 收到 `ApiMessageCompleteEvent` 得到最终 assistant message
4. 如果 assistant message 没有 tool_uses → 结束
5. 否则：
   - 产生 `ToolExecutionStarted`
   - 执行 `_execute_tool_call(...)`（里面含 hooks+permissions）
   - 产生 `ToolExecutionCompleted`
   - 把 tool_results 作为一个 user message append 回 messages
   - 进入下一轮 turn

关键点：
- 单个 tool call：顺序执行（即时流式回 UI）
- 多个 tool call：并发执行（`asyncio.gather`），再统一回放完成事件

### run_query 中的 auto-compact 机制

在每轮 turn 开始前，`run_query` 会检查当前消息历史的 token 数量是否超过阈值：
1. 先尝试 **microcompact**（清除旧 tool_result 内容，便宜、不调模型）
2. 如果 microcompact 后仍超阈值，执行 **full compact**（调用模型做语义摘要）

这个机制在 `auto_compact_if_needed()` 函数中实现，对应源码位置：`services/compact/__init__.py`。

> 这意味着 run_query 不仅仅是"调模型 + 跑工具"，它还负责**上下文窗口管理**——这是很多 Agent 框架容易忽略的工程细节。

## _execute_tool_call：工具执行链（可观测 + 安全）

你要记住这条链（对照源码 `engine/query.py` 的 `_execute_tool_call` 函数）：

1. **PreToolUse hooks**（可阻断）：`hook_executor.execute(HookEvent.PRE_TOOL_USE, ...)`
   - 如果 `pre_hooks.blocked == True`，直接返回 error 类型的 ToolResultBlock
2. **tool lookup**（ToolRegistry）：`tool_registry.get(tool_name)` → 未知工具返回 error
3. **pydantic 输入校验**（`tool.input_model.model_validate(tool_input)`）→ 非法参数返回 error
4. **路径解析**（`_resolve_permission_file_path`）：从参数中提取 `file_path/path/root` 并标准化为绝对路径
5. **命令提取**（`_extract_permission_command`）：从参数中提取 `command` 字段
6. **permission evaluate**（`PermissionChecker.evaluate(...)`）：含敏感路径硬拒绝、工具 allow/deny、路径规则、命令 deny、模式判断
   - 如果 `requires_confirmation`，会调用 `permission_prompt` 询问用户
7. **tool.execute(arguments, context)**：真实执行工具
8. **`_record_tool_carryover`**：记录元数据（读过哪些文件、用过哪些技能、工作日志…）到 `tool_metadata`
9. **PostToolUse hooks**：`hook_executor.execute(HookEvent.POST_TOOL_USE, ...)`

> **为什么要详细记住这条链？** 因为它是安全性与可扩展性的核心——任何一个环节出问题，要么导致安全漏洞（跳过权限），要么导致功能失效（hook 不执行）。

## 动手练习（最小代码单元）

运行：

```bash
python3 Study/exercises/ex04_agent_loop_fake.py
```

这个脚本做了一件很重要的事：**用一个 FakeApiClient 模拟模型的 tool_use 行为**，让你在不连外部 API 的情况下亲眼看到：
- run_query 发出的 StreamEvent 顺序
- 工具被执行、工具结果被回填、循环终止

你需要完成脚本里的两个 TODO：
1. 让 fake 模型一次请求 2 个工具调用，观察 run_query 的并发分支
2. 把 toy tool 改成“读写型”（`is_read_only=False`），看看权限系统会如何阻止（并解释原因）

## 自测题（含标准答案）

### Q1：为什么 tool results 要以“user message”的形式 append 回去？
**A：**因为在 Anthropic/Claude 风格的 message schema 里，工具结果作为 `tool_result` content block 由 user 角色承载，这样模型下一轮能看到“我刚刚请求的工具的输出”。

### Q2：run_query 为什么要区分单工具与多工具？
**A：**
- 单工具：边执行边流式发事件，让 UI 更及时（用户不会等一坨）
- 多工具：并发执行减少总耗时，同时仍能按工具维度产出 started/completed 事件

### Q3：_execute_tool_call 里最核心的”安全点”是哪个？
**A：**`PermissionChecker.evaluate(...)` + 内建敏感路径 deny（`SENSITIVE_PATH_PATTERNS`），它保证即使模型想访问敏感凭据文件也会被硬阻断。

### Q4（流程追踪题）：假设模型在一次回复中请求了 3 个工具调用，请描述 run_query 会怎么处理。
**A：**
1. 收到 `ApiMessageCompleteEvent`，发现 `tool_uses` 列表长度为 3
2. 因为是多工具，使用 `asyncio.gather()` 并发执行 3 个 `_execute_tool_call`
3. 每个 tool call 各自走完 PreHook → Permission → Execute → Carryover → PostHook 链
4. 3 个 `ToolResultBlock` 收集完毕后，统一 append 为一条 user message
5. 进入下一轮 turn

### Q5（代码理解题）：`_record_tool_carryover` 做了什么？为什么需要它？
**A：** 它把工具执行的关键信息（读过的文件路径、调用过的 skill、工作日志）记录到 `tool_metadata` 中。这些信息用于：
- 会话恢复时重建上下文
- session snapshot 持久化（见第 9 章）
- 给后续工具调用提供”之前做了什么”的上下文

## 常见误区

1. **误区：以为 run_query 只循环一次**
   `run_query` 会循环多轮 turn，直到模型不再请求工具（`stop_reason == “end_turn”`）或到达 `max_turns`。

2. **误区：以为工具结果立刻被模型看到**
   工具结果要经过 `append` 到 messages 列表后，在**下一轮** `stream_message()` 调用时才被模型看到。这是”消息回填”的核心机制。

3. **误区：以为 PreToolUse hook 阻断等于”不执行就没事”**
   hook 阻断会返回一个 `is_error=True` 的 ToolResultBlock，模型**会看到这个错误**并可能调整策略。

4. **误区：忽略 auto-compact 的存在**
   如果对话很长，旧的 tool_result 内容会被 microcompact 清空。如果你在调试时发现”之前的工具输出怎么变成了 [Old tool result content cleared]”——这就是 auto-compact 在工作。

