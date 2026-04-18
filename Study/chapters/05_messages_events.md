# 第 5 章：消息模型与事件流（Messages / StreamEvents）

这一章要解决的问题：**“OpenHarness 用什么数据结构把‘对话/工具/流式输出’统一起来？”**

## 你将学会什么

- `ConversationMessage` 的 content blocks：Text / Image / ToolUse / ToolResult
- 模型 API 事件（ApiTextDeltaEvent/ApiMessageCompleteEvent）如何映射到 OpenHarness 的 StreamEvent
- 为什么 UI 会拿到一串”事件”而不是一个大字符串

## 前置知识

- 第 4 章的 run_query 循环（知道工具调用闭环的流程）
- 了解”流式输出”的概念（模型不是一次吐完，而是一个字一个字/一块一块发出来的）
- 知道 JSON 序列化的概念（`to_api_param()` 就是把 Python 对象变成可发给 API 的字典）

## 关键文件（必读）

- `src/openharness/engine/messages.py`
- `src/openharness/engine/stream_events.py`
- `src/openharness/api/client.py`（只看事件 dataclass 即可）

## ConversationMessage：一个统一的“消息容器”

`ConversationMessage` 有两个关键字段：
- `role`: `"user"` / `"assistant"`
- `content`: `list[ContentBlock]`

ContentBlock 里最重要的四种：
- `TextBlock`：普通文本
- `ImageBlock`：多模态图片（base64）
- `ToolUseBlock`：模型请求调用工具（name + input + id）
- `ToolResultBlock`：工具执行结果（tool_use_id + content + is_error）

你要记住一个小但重要的点：
- `ConversationMessage.tool_uses` 是从 `content` 里筛 `ToolUseBlock`
- 所以 assistant message 里有 `ToolUseBlock` 就代表“模型要用工具”

## StreamEvent：UI/CLI 看的“事件流”

run_query 不是直接 return 文本，而是 yield 一连串 StreamEvent：
- `AssistantTextDelta`：流式文本增量
- `AssistantTurnComplete`：这一轮 assistant message 完成（带 usage）
- `ToolExecutionStarted` / `ToolExecutionCompleted`
- `StatusEvent` / `ErrorEvent`
- `CompactProgressEvent`（压缩会话时的进度）

为什么这么设计？
- UI 可以更细粒度地展示：边打字边显示、工具开始/完成、状态提示
- 同一套事件既适用于 React TUI，也适用于 headless/print 模式

## 动手练习（最小代码单元）

运行：

```bash
python3 Study/exercises/ex05_messages_events.py
```

它会构造一组 `ConversationMessage`（包含 tool_use/tool_result），并演示：
- `tool_uses` 属性怎么拿到工具调用
- `to_api_param()` 变成 provider wire format 的样子

你需要完成脚本里的 TODO：
1. 给 assistant message 增加第二个 ToolUseBlock，并把它的 tool_result 回填
2. 把其中一个 tool_result 标成 `is_error=True`，并解释 run_query 为什么还要把它回填给模型

## 自测题（含标准答案）

### Q1：`ToolUseBlock.id` 的作用是什么？
**A：**它把“模型发起的某一次工具调用”与“后续返回的 ToolResultBlock”关联起来：tool_result 里会填 `tool_use_id`。

### Q2：为什么需要 `AssistantTextDelta` 和 `AssistantTurnComplete` 两种事件？
**A：**
- delta 用于流式渲染（边出边显示）
- complete 用于“这一轮结束”的边界（拿到最终 message/usage，做状态更新）

### Q3：tool_result 为什么要包含 is_error？
**A：**模型需要知道工具是否成功，失败时才能调整策略（例如换方案、要求用户确认、减少破坏性操作）。

### Q4（模块关系判断题）：以下哪个说法是正确的？
- A) `ToolUseBlock` 出现在 user message 中
- B) `ToolResultBlock` 出现在 assistant message 中
- C) 一个 assistant message 可以同时包含 TextBlock 和 ToolUseBlock
- D) `to_api_param()` 返回的是 ConversationMessage 对象

**A：** C 是正确的。A 错误（ToolUseBlock 出现在 **assistant** message 中），B 错误（ToolResultBlock 出现在 **user** message 中），D 错误（`to_api_param()` 返回的是 **字典**，不是对象）。

### Q5（推演题）：如果 assistant message 里有 2 个 ToolUseBlock，对应的 user message 里应该有几个 ToolResultBlock？每个 ToolResultBlock 的 `tool_use_id` 是怎么确定的？
**A：** 应该有 2 个 ToolResultBlock。每个 ToolResultBlock 的 `tool_use_id` 必须与对应 ToolUseBlock 的 `id` 一一匹配。这就像"请求-响应"配对，模型通过 id 来识别"这个结果是哪个工具调用返回的"。

## 常见误区

1. **误区：以为 StreamEvent 是给模型看的**
   StreamEvent 是给 **UI/CLI** 消费的，模型看的是 `messages` 列表里的 ConversationMessage。

2. **误区：以为 `to_api_param()` 的输出就是存储格式**
   `to_api_param()` 是转换成 API 调用的 wire format（发给模型 API 的格式），不是本地存储/session snapshot 的格式。

3. **误区：搞混"消息角色"与"内容块类型"的对应关系**
   记住口诀：**模型说工具（assistant + ToolUseBlock），框架回结果（user + ToolResultBlock）**。

