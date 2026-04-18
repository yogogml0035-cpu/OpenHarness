# 第 9 章：Commands / Memory / Sessions / Compaction（交互“控制面”）

这一章要解决的问题：**“除了自然语言对话，OpenHarness 还有哪些‘控制面’？会话怎么保存？上下文怎么压缩？”**

## 你将学会什么

- slash commands：`/help` 这类命令如何解析、如何影响 runtime/engine
- session snapshot：如何保存/恢复消息与 tool_metadata
- memory：项目记忆文件（.md）如何维护索引
- microcompact：如何在不调用模型的情况下”便宜地”减少 token

## 前置知识

- 第 4 章的 run_query 循环（知道 auto-compact 在哪个位置被触发）
- 第 5 章的 ConversationMessage 结构（microcompact 操作的就是 messages 列表里的 ToolResultBlock）
- 了解 JSON 文件读写（session snapshot 用 JSON 存储）

## 关键文件（必读）

- commands：`src/openharness/commands/registry.py`
- sessions：`src/openharness/services/session_storage.py`
- memory：`src/openharness/memory/manager.py`、`src/openharness/memory/paths.py`
- compaction：`src/openharness/services/compact/__init__.py`（重点：`microcompact_messages`）

## Slash Commands：像一个“内置控制台”

`CommandRegistry.lookup(raw_input)`：
- 只有以 `/` 开头才算命令
- 解析 name + args
- 返回 handler（或 None）

复杂点在 handler：很多 handler 会刷新 model/permissions/theme/session 等状态。

## Session snapshot：可恢复的对话状态

`save_session_snapshot(...)` 保存：
- `messages`
- `usage`
- `tool_metadata`（只持久化白名单 key）

这能支持 `--continue/--resume` 等恢复流程。

## Memory：项目内知识的持久化

`add_memory_entry()` 会：
1. 在项目 memory 目录写一个 `.md`
2. 更新 `MEMORY.md` 索引（避免重复）

## Microcompact：先便宜地省 tokens

`microcompact_messages` 会把旧 tool_result 内容替换成固定占位符，不改结构但省 token。

## 动手练习（最小代码单元）

运行：

```bash
python3 Study/exercises/ex09_memory_sessions_compact.py
```

脚本会：
1. microcompact 一组 messages 并打印 tokens_saved
2. 在临时 data dir 下保存/读取 session snapshot
3. 在临时项目目录写入/列出 memory 文件

你需要完成脚本里的 TODO：
1. 把 keep_recent 从 1 改成 3，预测 tokens_saved 会变大还是变小，并解释
2. 手动往 tool_metadata 里加一个“未在白名单”的 key，观察 snapshot 里是否会持久化

## 自测题（含标准答案）

### Q1：为什么 tool_metadata 不是全量持久化？
**A：**tool_metadata 里可能放了运行时对象或不可 JSON 化数据；因此只持久化白名单 key 并做 sanitize，保证可恢复又可存储。

### Q2：microcompact 的优点与局限是什么？
**A：**
- 优点：不调用模型，速度快、成本低；对”超长工具输出”很有效
- 局限：不理解语义；关键事实可能被清空，需要更高级的 full compact（会调用模型）

### Q3（推演题）：假设 messages 里有 5 个 ToolResultBlock，`keep_recent=2`，microcompact 会清除几个？
**A：** 清除 3 个（保留最后 2 个）。清除的方式是把 `content` 替换为 `”[Old tool result content cleared]”`，不删除 block 本身。

### Q4（模块关系判断题）：tool_metadata 持久化白名单里包含以下哪些 key？
- A) `permission_mode` → **包含**
- B) `read_file_state` → **包含**
- C) `mcp_manager` → **不包含**（运行时对象，不可 JSON 化）
- D) `invoked_skills` → **包含**
- E) `api_client` → **不包含**

### Q5（业务逻辑推演题）：为什么 session snapshot 只持久化 `_PERSISTED_TOOL_METADATA_KEYS` 白名单里的 key，而不是全量保存？
**A：** 因为 `tool_metadata` 里可能包含：
1. **运行时对象**（如 `mcp_manager`、`tool_registry`），它们不能 JSON 序列化
2. **敏感信息**（如临时 API key），不应落盘
3. **大体积数据**（如完整文件内容缓存），会让 snapshot 文件过大
白名单机制确保只保存”恢复时真正需要”的轻量级、可序列化数据。

## 常见误区

1. **误区：以为 `/model gpt-5.4` 只是改了一个字符串**
   slash command handler 会触发一系列副作用：刷新 Settings、重新解析 provider、更新 AppState、通知前端。

2. **误区：以为 microcompact 会删除消息**
   microcompact 只替换 ToolResultBlock 的 content，不会删除任何消息或 block。消息结构保持完整，只是旧工具输出变成了占位符。

3. **误区：以为 `--resume` 能恢复所有状态**
   resume 恢复的是 messages + 白名单 tool_metadata。MCP 连接、hook 执行器等运行时对象需要重新创建（在 `build_runtime()` 中）。

