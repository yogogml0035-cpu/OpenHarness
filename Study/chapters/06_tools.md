# 第 6 章：工具系统（Tools）—— BaseTool / ToolRegistry / Schema

这一章要解决的问题：**“OpenHarness 的工具到底长什么样？为什么工具 schema 对模型很重要？”**

## 你将学会什么

- 一个工具最小需要哪些要素：`name/description/input_model/execute()`
- `ToolRegistry` 如何组织工具、如何生成 API 所需 schema
- `is_read_only()` 为什么很关键（直接影响权限系统）

## 前置知识

- 第 4 章的工具执行链（知道 run_query 里工具是怎么被调用的）
- 了解 Pydantic BaseModel（input_model 就是一个 Pydantic model）
- 了解 JSON Schema（模型通过它来"理解"工具有哪些参数）

## 关键文件（必读）

- `src/openharness/tools/base.py`
  - `BaseTool` / `ToolResult` / `ToolExecutionContext` / `ToolRegistry`
- `src/openharness/tools/__init__.py`
  - `create_default_tool_registry()`：默认工具注册点
- 任选 2 个具体工具看实现模式：
  - `src/openharness/tools/file_read_tool.py`
  - `src/openharness/tools/bash_tool.py`
  - `src/openharness/tools/skill_tool.py`

## BaseTool 的“最小契约”

BaseTool 是一个很干净的抽象：
- `input_model: type[pydantic.BaseModel]`：结构化输入（模型更不容易乱填参数）
- `execute(arguments, context) -> ToolResult`：执行工具并返回文本结果
- `to_api_schema()`：把工具描述转换为 provider 需要的 JSON schema（模型用它来“理解”工具）
- `is_read_only()`：告诉权限系统这次调用是否属于只读（默认 False）

你应该能在脑中把工具执行想成：
> 模型给出 `{name, input}` → harness 校验 input → 执行 → 把 output 返回给模型

## ToolRegistry：工具集合 + schema 入口

`ToolRegistry` 是一个简单的 name → tool 映射：
- `register(tool)`
- `get(name)`
- `to_api_schema()`（把所有工具的 schema 列出来给模型）

这一点会在 `run_query()` 里用到：
- `tools=context.tool_registry.to_api_schema()`

## 动手练习（最小代码单元）

运行：

```bash
python3 Study/exercises/ex06_tools_schema.py
```

脚本会：
1. 定义一个 toy tool（Pydantic 输入 + read-only）
2. 注册到 ToolRegistry
3. 打印它的 `to_api_schema()`
4. 直接调用 `execute()` 得到 ToolResult

你需要完成脚本里的 TODO：
1. 再写一个工具 `repeat(text, times)`，并注册到 registry
2. 故意传入非法参数（比如 times="x"），观察 pydantic 校验报错长什么样

## 自测题（含标准答案）

### Q1：为什么 OpenHarness 强制用 pydantic input_model？
**A：**因为工具是模型调用的“API”。结构化输入能让模型更容易填对字段；对框架而言也能在执行前进行类型校验，减少“乱参数导致的危险行为”。

### Q2：`is_read_only()` 为什么会影响安全？
**A：**权限系统在默认模式下会自动放行只读工具，但会对“会修改文件/执行命令”的工具要求确认或直接阻断。读写判定错了会导致越权或误阻断。

### Q3：ToolResult 为什么除了 output 还要有 is_error？
**A：**模型需要知道工具是否失败，失败时会改变策略（重试、换方法、要求用户确认等）。

### Q4（最小代码验证题）：写出一个最小工具的伪代码（不超过 15 行），要求：名字叫 `word_count`，输入一段文本，输出单词数。
**参考答案：**
```python
class WordCountArgs(BaseModel):
    text: str

class WordCountTool(BaseTool):
    name = "word_count"
    description = "Count words in text."
    input_model = WordCountArgs

    def is_read_only(self, arguments):
        return True  # 只读操作

    async def execute(self, arguments, context):
        count = len(arguments.text.split())
        return ToolResult(output=str(count))
```

### Q5（模块关系判断题）：以下关于 ToolExecutionContext 的说法哪个是正确的？
- A) context.metadata 里包含 tool_registry，所以工具可以在执行时调用其他工具
- B) context.cwd 是固定的，不能被用户改变
- C) context.metadata 和 tool_metadata 是同一个对象

**A：** A 是正确的。在 `_execute_tool_call` 中，`context.metadata` 包含了 `tool_registry` 和 `ask_user_prompt` 等，这使得工具（如 Agent tool）可以在执行中调用其他工具。B 错误（cwd 可以通过 CLI 或命令改变），C 需要结合源码进一步确认。

## 常见误区

1. **误区：以为 `to_api_schema()` 是给人看的文档**
   它生成的 JSON Schema 是给**模型**看的——模型通过它来理解"这个工具接受什么参数"。如果 schema 写得不好，模型就会乱填参数。

2. **误区：忘记 `is_read_only()` 的参数**
   注意 `is_read_only()` 的参数是 `arguments`（已解析的 Pydantic model），不是原始 dict。这意味着同一个工具可以根据**不同的输入参数**返回不同的只读判定（例如 bash 工具根据命令内容判断）。

3. **误区：以为工具注册后就不能变了**
   `ToolRegistry` 在 MCP 连接变化时可以动态增减工具。运行时 MCP server 断开/重连，对应的 McpToolAdapter 会被移除/重新注册。

