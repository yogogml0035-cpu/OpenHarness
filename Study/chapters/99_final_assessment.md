# 综合验收：你是否真正”学会了”OpenHarness？

这里给你一套”闭卷自测 + 动手小项目”。你可以按顺序做，最后对照标准答案。

## A. 口述题（建议你用 5 分钟复述）

### 1）请用 8 句话解释一次交互的完整链路（从输入到结束）
**标准答案要点：**
1. CLI/TUI 把用户输入交给 runtime（RuntimeBundle）。
2. runtime 里有 QueryEngine，保存 messages 历史。
3. QueryEngine.submit_message 把 user message append，并构造 QueryContext。
4. run_query 调 api_client.stream_message 流式产出 assistant delta。
5. 收到最终 assistant message 后，如果没有 tool_use，则 turn 结束。
6. 如果有 tool_use，框架先跑 pre_tool_use hooks，再做 PermissionChecker 评估。
7. 允许后执行 tool.execute，记录 carryover metadata，跑 post_tool_use hooks，把结果封装为 tool_result block 回填为 user message。
8. 再进入下一轮 turn，直到模型不再请求工具或到达 max_turns。

### 2）请解释”模型负责 what，harness 负责 how”在代码里对应哪些位置？
**标准答案要点：**
- what：assistant message 里产生的 ToolUseBlock（由模型决定要用什么工具、输入参数）
- how：`_execute_tool_call` 里的 hooks + permissions + tool.execute（由框架执行、并保证安全与可观测）

## B. 读码题（不用运行）

### 1）在 `run_query()` 里，哪里决定了”多工具并发执行”？
**标准答案：**`src/openharness/engine/query.py` 中 `if len(tool_calls) == 1: ... else: results = await asyncio.gather(...)` 的分支。

### 2）敏感路径硬拒绝在哪里实现？为什么它比 mode 更高优先级？
**标准答案：**
- 实现位置：`src/openharness/permissions/checker.py` 的 `SENSITIVE_PATH_PATTERNS` + evaluate() 开头匹配逻辑
- 原因：它是防 prompt injection 的 defence-in-depth，不能被用户配置/模式绕过

### 3）`_execute_tool_call` 的完整执行链（9 步）是什么？
**标准答案：**
1. PreToolUse hooks（可阻断）
2. tool lookup（ToolRegistry.get）
3. pydantic 输入校验（input_model.model_validate）
4. 路径解析（_resolve_permission_file_path）
5. 命令提取（_extract_permission_command）
6. permission evaluate（PermissionChecker.evaluate）
7. tool.execute(arguments, context)
8. _record_tool_carryover（记录元数据）
9. PostToolUse hooks

### 4）MCP 工具是怎么”伪装”成内置工具的？
**标准答案：** 通过 `McpToolAdapter`（适配器模式）。它把 MCP 工具包装成 `BaseTool` 接口，注册到同一个 `ToolRegistry`。`run_query` 不区分工具来源，统一走工具执行链。

## C. 模块关系综合题

### 1）画出以下模块的依赖关系（谁依赖谁）：
`cli.py` / `runtime.py` / `query.py` / `ToolRegistry` / `PermissionChecker` / `HookExecutor`

**标准答案：**
```
cli.py → runtime.py → {ToolRegistry, PermissionChecker, HookExecutor, QueryEngine}
query.py ← QueryEngine（query.py 的 run_query 被 QueryEngine 调用）
run_query 内部使用 → ToolRegistry + PermissionChecker + HookExecutor
```
关键点：runtime 负责”组装”，query 负责”使用”。

### 2）如果你要给 OpenHarness 新增一个”代码审查”工具，需要在哪些文件/模块中做改动？
**标准答案：**
1. 创建 `src/openharness/tools/code_review_tool.py`（定义 BaseTool 子类 + Pydantic input）
2. 在 `src/openharness/tools/__init__.py` 的 `create_default_tool_registry()` 中注册
3. （可选）添加 permission 相关配置（如果需要特殊权限规则）
4. （可选）添加对应的 hook matcher（如果需要审计）

## D. 动手小项目（10–20 分钟）

目标：用”最小闭环”复刻 OpenHarness 的核心循环（不连外部 API）。

你要做的事：
1. 基于 `Study/exercises/ex04_agent_loop_fake.py`，新增一个工具 `math_eval(expression)`：
   - 输入：字符串表达式（只允许数字、+ - * / 和括号）
   - 输出：计算结果
2. 修改 fake 模型，让它先调用 `math_eval(“2*(3+4)”)`，再输出最终回答。
3. 最后让脚本打印一段”你自己的事件日志”（按时间顺序列出 event 类型）。

验收标准（你做完应当看到）：
- 事件流里出现：AssistantTurnComplete → ToolExecutionStarted → ToolExecutionCompleted → AssistantTurnComplete
- 最终文本包含 `14`

提示（避免安全坑）：表达式求值请不要直接 `eval`，可以用 `ast.parse` 做白名单节点过滤。

## E. 自测打分（你可以给自己打分）

- 我能从 `cli.py` 追到 `run_query()` 并讲清楚每一步：0/1
- 我能默写 `_execute_tool_call` 的 9 步执行链：0/1
- 我能写一个 tool（Pydantic input + execute + read_only），并被 registry 使用：0/1
- 我能解释 permissions 的决策顺序与敏感路径 hard deny：0/1
- 我能解释 plugins/skills/hooks 是怎么被加载并影响行为：0/1
- 我能解释 MCP 与 tasks 的角色，以及 McpToolAdapter 的作用：0/1
- 我能说出 Settings 的四层优先级和 profile 投影机制：0/1

得分建议：
- 6–7：入门完成，可以开始做小功能/修 bug
- 4–5：核心概念掌握，建议回到薄弱章节再练一遍
- 2–3：回到第 4/6/7/8 章再跑一遍练习
- 0–1：先把第 1–4 章练习做完

