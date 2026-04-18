# 第 8 章：Hooks / Plugins / Skills（扩展点）

这一章要解决的问题：**“OpenHarness 如何在不改核心代码的情况下，扩展行为与能力？”**

## 你将学会什么

- skills：按需加载的 Markdown 知识单元（SKILL.md）
- plugins：一套 Claude Code 兼容的扩展布局（commands/hooks/agents/mcp/skills）
- hooks：在生命周期关键点插入自定义行为（pre_tool_use / post_tool_use / session_start...）
- 三者的区别与协作关系

## 前置知识

- 第 4 章的工具执行链（知道 PreToolUse/PostToolUse hooks 在链中的位置）
- 第 6 章的 BaseTool 概念（skills 是通过 Skill tool 被加载的）
- 了解 YAML frontmatter（Markdown 文件开头 `---` 包裹的元数据区域）

## 关键文件（必读）

- skills
  - `src/openharness/skills/loader.py`
  - `src/openharness/skills/registry.py`
- plugins
  - `src/openharness/plugins/schemas.py`（PluginManifest）
  - `src/openharness/plugins/loader.py`（discover/load/parse）
- hooks
  - `src/openharness/hooks/events.py`
  - `src/openharness/hooks/loader.py`（HookRegistry + load）
  - `src/openharness/hooks/executor.py`（HookExecutor + matcher/inject）
  - `src/openharness/hooks/schemas.py`（hook 定义模型）

## Skills：最小知识扩展（SKILL.md）

你可以把 skill 当成：
> “一段结构化提示词 + 可选 frontmatter 元数据”

`load_skill_registry()` 会把以下来源的技能合并进来：
- bundled skills（内置）
- user skills（`~/.openharness/skills/<skill-dir>/SKILL.md`）
- extra_skill_dirs（CLI/运行时扩展）
- plugin skills（来自已启用插件）

## Plugins：把扩展打包成“目录”

插件核心是一个 `plugin.json`（或 `.claude-plugin/plugin.json`），由 `PluginManifest` 校验。

`load_plugin()` 解析并返回 `LoadedPlugin`，里面可能包含：
- skills（SKILL.md）
- commands（Markdown 命令）
- hooks（hooks.json）
- mcp servers（mcp.json/.mcp.json）
- agents（agent markdown frontmatter）

## Hooks：生命周期插槽

HookExecutor 的行为可以用一句话概括：
> “在某个事件发生时，挑出匹配的 hooks，按类型执行，并决定是否阻断”

### Hook 事件类型（6 种，在 `hooks/events.py` 中定义）

| 事件 | 触发时机 | 典型用途 |
|------|---------|---------|
| `session_start` | 会话启动时 | 初始化环境、加载外部配置 |
| `session_end` | 会话结束时 | 清理资源、发送统计 |
| `pre_tool_use` | 工具执行**前** | 审核/过滤/阻断危险操作 |
| `post_tool_use` | 工具执行**后** | 记录日志、触发后续动作 |
| `pre_compact` | 上下文压缩**前** | 保存关键信息 |
| `post_compact` | 上下文压缩**后** | 验证压缩结果 |

### Hook 执行类型（4 种，在 `hooks/schemas.py` 中定义）

| 类型 | 说明 | 典型场景 |
|------|------|---------|
| `command` | 执行一条 shell 命令 | 跑脚本、写日志 |
| `prompt` | 把事件上下文送给 LLM 做判断 | 智能审核（”这个 bash 命令安全吗？”） |
| `http` | 发送 HTTP 请求 | 通知 webhook、调用外部审计 API |
| `agent` | 启动一个 agent 子任务 | 让另一个 agent 做代码审查 |

匹配靠 `matcher`（fnmatch 风格），匹配对象通常是 tool_name 或 prompt。

### Hook 的”阻断”能力

`pre_tool_use` 类型的 hook 可以返回 `blocked=True`，此时 `_execute_tool_call` 会直接返回 error 结果，工具**不会被执行**。这是 hooks 最强大的安全能力。

## 动手练习（最小代码单元）

运行：

```bash
python3 Study/exercises/ex08_plugins_skills_hooks.py
```

脚本会在临时目录生成一个最小插件结构（plugin.json + 一个 command + 一个 skill），然后用 `load_plugin()` 读取并打印解析结果。

你需要完成脚本里的 TODO：
1. 给 command markdown 加 YAML frontmatter（name/description），观察 loader 如何提取 description
2. 给 skill 的 SKILL.md 加 frontmatter，观察 `_parse_skill_markdown` 的解析结果

## 自测题（含标准答案）

### Q1：skills 与 plugins 的区别是什么？
**A：**
- skill：一个知识单元（提示词/指导），通常由 Skill tool 按需加载
- plugin：一个扩展包，可能同时提供 commands/hooks/skills/mcp/agents 等多种扩展点

### Q2：hooks 能做什么、不能做什么？
**A：**
- 能：在关键事件前后运行命令/HTTP/prompt/agent 校验，并可阻断
- 不能：直接替代工具执行（它更像”守门员/审计/增强”，不是主执行链）

### Q3（业务逻辑推演题）：你想让所有 `bash` 工具调用都先经过一个安全审核脚本 `check_cmd.py`，应该怎么配置 hook？
**参考答案：**
```json
{
  “hooks”: {
    “pre_tool_use”: [
      {
        “type”: “command”,
        “matcher”: “bash”,
        “command”: “python3 check_cmd.py \”$TOOL_INPUT\””,
        “timeout_seconds”: 10
      }
    ]
  }
}
```
关键点：`matcher: “bash”` 确保只匹配 bash 工具；`type: “command”` 表示执行 shell 命令；如果脚本返回非零退出码，hook 会被视为 `blocked`。

### Q4（判断题）：以下关于 skills 的说法哪个是错误的？
- A) skill 是一段 Markdown，在模型需要时按需加载
- B) skill 可以来自内置、用户目录、插件三个来源
- C) skill 一旦加载就永远在模型的上下文中
- D) skill 的 frontmatter 可以包含 name 和 description

**A：** C 是错误的。skill 是**按需加载**的，通过 Skill tool 触发。加载后的 skill 内容会作为消息的一部分出现在上下文中，但不是”永远在”。

### Q5（流程追踪题）：当 `build_runtime()` 加载一个插件时，插件里的 hook 是怎么进入 HookExecutor 的？
**A：**
1. `load_plugin(plugin_dir)` 解析 `hooks.json`（或 `.hooks.json`），得到 hook 配置
2. 返回的 `LoadedPlugin` 包含 `hooks` 字段
3. `build_runtime()` 把所有 plugin hooks 合并到统一的 hook 配置中
4. 创建 `HookExecutor(merged_hooks)` → hook 就绑定到了执行器上

## 常见误区

1. **误区：以为 skills 和 plugins 是同一个东西**
   skill 是最小知识单元（一个 SKILL.md），plugin 是一个扩展包（可以包含 commands/hooks/skills/mcp/agents 多种扩展点）。skill 可以独立存在，也可以被 plugin 包含。

2. **误区：以为 hook 只能阻断**
   hook 有 4 种执行类型。`command` 和 `http` 通常用于记录/通知（非阻断），`prompt` 和 `agent` 可以做智能判断（可阻断也可不阻断）。

3. **误区：以为 post_tool_use hook 可以修改工具输出**
   `post_tool_use` hook 在工具执行**之后**运行，它看到的是最终结果，但不能修改 ToolResultBlock。它更适合做”审计/记录/触发后续动作”。

