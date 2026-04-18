# 第 1 章：项目全景图与阅读路线（Repo Map）

你在这一章要解决的核心问题只有一个：**“我应该从哪里开始读 OpenHarness？”**

## 你将学会什么

- 能说清楚这个项目的“十几个子系统”分别放在哪个目录
- 知道一次交互会经过哪些关键文件（从入口到核心循环）
- 学会用“入口文件 + 测试用例”快速理解业务逻辑

## OpenHarness 是什么（用一句话）

OpenHarness 是一个 **Agent Harness（智能体运行框架）**：模型决定“做什么”(what)，框架负责“怎么做”(how) —— 主要包括：
- 让模型以**流式**方式输出内容
- 当模型请求调用工具（tool_use）时，框架执行工具、做权限校验、跑 hooks、把结果再喂回模型
- 可扩展：commands / skills / plugins / MCP / tasks / multi-agent

## 前置知识

- 能读 Python 代码（函数、类、async/await 大致知道是什么）
- 知道”大语言模型”可以通过 API 输出文本
- 不需要了解 Agent 框架的任何细节——这一章的目标就是帮你建立第一印象

## 目录结构（先把地图背下来）

必看目录：
- `src/openharness/`：OpenHarness 核心 Python 包（**最重要，后面所有章节都围绕它**）
- `ohmo/`：另一个入口（personal-agent app），可先放后面
- `frontend/terminal/`：React TUI（终端前端）
- `tests/`：理解业务逻辑最快的”第二入口”

你可以把 `src/openharness/` 按子系统记成 **四层**：

### 第一层：入口层（怎么进来）
- `cli.py`：`oh` / `openharness` 命令行入口（Typer）
- `ui/app.py`：`run_repl/run_print_mode/run_task_worker` 三种运行方式

### 第二层：核心循环层（怎么跑起来）
- `ui/runtime.py`：组装 RuntimeBundle（settings → plugins → mcp → tools → hooks → engine → commands）
- `engine/query_engine.py`：QueryEngine（消息历史 + 调用 run_query）
- `engine/query.py`：`run_query()` 核心工具调用闭环
- `engine/messages.py`：消息/内容块数据结构
- `engine/stream_events.py`：UI 消费的事件流定义

### 第三层：核心能力层（框架做了什么）
- `tools/`：工具系统（文件、shell、web、mcp、tasks、multi-agent…）
- `permissions/`：权限系统（模式、路径规则、敏感路径防护）
- `hooks/`：生命周期 hooks（pre_tool_use / post_tool_use / session_start…）
- `config/`：配置系统（Settings/Profile/paths）
- `prompts/`：系统提示词组装（`system_prompt.py` 把环境/工具/规则拼成模型看到的”指令”）
- `api/`：Provider/API Client（Anthropic/OpenAI/Codex/Copilot）
- `auth/`：认证管理（OAuth/API Key/外部登录）

### 第四层：扩展层（怎么变强）
- `commands/`：slash commands（`/help`、`/model`、`/permissions` 等）
- `plugins/` + `skills/`：插件/技能加载（Markdown 扩展）
- `mcp/`：MCP（Model Context Protocol）客户端
- `tasks/`：后台任务（shell/agent 子进程）
- `swarm/` + `coordinator/`：多 Agent 协作/团队机制
- `channels/`：多渠道接入（Slack/Discord/Telegram/飞书/钉钉/QQ/微信等）
- `bridge/`：跨进程 Agent 会话桥接

### 辅助层（可以后面再看）
- `services/`：会话存储（`session_storage.py`）、上下文压缩（`compact/`）、token 估算、cron 调度
- `state/`：运行时全局状态管理（`AppState`）
- `memory/`：项目记忆文件持久化
- `keybindings/`：键绑定（vim 模式等）
- `vim/`：vim 编辑模式支持
- `voice/`：语音输入模式
- `themes/` + `output_styles/`：主题与输出样式
- `personalization/`：用户个性化偏好提取
- `sandbox/`：Docker 沙箱执行环境
- `platforms.py`：跨平台兼容性工具

## 最重要的“主流程”长什么样

从用户视角看：

1. 你输入一句话（CLI 或 TUI）
2. 模型输出一段话（可能中间夹着工具调用）
3. 框架执行工具（权限/钩子/执行）
4. 工具结果回到模型 → 模型继续 → 直到不再需要工具

从代码视角看（只记 4 个文件就能跑通主线）：
- `src/openharness/cli.py`
- `src/openharness/ui/runtime.py`
- `src/openharness/engine/query_engine.py`
- `src/openharness/engine/query.py`

## 读代码路线（一步一步）

按下面顺序读，你会更容易“把点连成线”：

1) 看入口参数都有哪些：`src/openharness/cli.py`
- 找 `@app.callback` 的 `main()`：它决定进入 `run_repl` / `run_print_mode` / `run_task_worker`

2) 看 runtime 怎么组装：`src/openharness/ui/runtime.py`
- 找 `async def build_runtime(...)`
- 重点抓：`tool_registry`、`PermissionChecker`、`HookExecutor`、`QueryEngine` 是怎么来的

3) 看核心循环：`src/openharness/engine/query.py`
- 找 `async def run_query(...)`
- 抓住 3 个阶段：`stream_message` → `execute_tool_call` → `messages.append(tool_results)`

4) 去 tests 找“行为证据”：`tests/`
- 建议先看：`tests/test_engine/test_query_engine.py`、`tests/test_tools/test_core_tools.py`

## 动手练习（最小代码单元）

运行：

```bash
python3 Study/exercises/ex01_repo_map.py
```

你会看到脚本打印出的模块统计。然后你做两件事：
1. 按脚本里的 TODO，把 `tests/` 的测试文件数量也统计出来
2. 把输出改成按“子系统优先级”排序（先 engine/tools/permissions/hooks/commands）

完成标准：你能在 1 分钟内回答“工具系统在哪、权限系统在哪、核心循环在哪”。

## 自测题（含标准答案）

### Q1：读 OpenHarness 最短路径是哪四个文件？
**A：**
- `src/openharness/cli.py`
- `src/openharness/ui/runtime.py`
- `src/openharness/engine/query_engine.py`
- `src/openharness/engine/query.py`

### Q2：为什么建议你用 tests 来理解业务逻辑？
**A：** tests 通常把“输入 → 行为 → 输出”的预期写死了，比只读实现更快确认：某个模块应该怎么用、边界条件是什么、哪些行为是稳定契约。

### Q3：工具调用闭环里，模型与 harness 分别负责什么？
**A：**
- 模型：决定下一步要不要调用工具、调用哪个工具、输入参数是什么（what）
- harness：权限校验、hook 执行、真实执行工具、把结果组织成 tool_result 再给模型（how）

### Q4：项目有哪些"辅助模块"是可以后面再看的？请至少列出 4 个。
**A：** `keybindings/`（键绑定）、`vim/`（vim 模式）、`voice/`（语音输入）、`themes/`（主题）、`output_styles/`（输出样式）、`personalization/`（个性化偏好）、`sandbox/`（Docker 沙箱）——这些不影响理解核心流程。

### Q5（流程追踪题）：当你在终端输入 `oh "你好"` 时，请按顺序列出会经过的 4 个关键源文件。
**A：**
1. `cli.py` → 解析命令行参数，决定进入 print 模式
2. `ui/runtime.py` → `build_runtime()` 组装所有依赖
3. `engine/query_engine.py` → `submit_message()` 追加用户消息
4. `engine/query.py` → `run_query()` 流式调用模型、处理工具调用

## 常见误区

1. **误区：以为 `ohmo/` 是核心代码**
   实际上 `ohmo/` 是一个独立的上层应用，核心逻辑全在 `src/openharness/` 里。

2. **误区：跳过 `tests/` 直接看实现**
   测试用例是理解"模块应该怎么用"的最快方式，比注释更可靠。

3. **误区：以为所有模块同等重要，想从头到尾全看**
   `engine/` + `tools/` + `permissions/` 是核心三件套，先吃透它们，其它模块按需查看。

