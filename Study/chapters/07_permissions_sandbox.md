# 第 7 章：权限与沙箱（Permissions / Sandbox）

这一章要解决的问题：**“模型能不能随便读你电脑的文件、执行危险命令？OpenHarness 如何拦住它？”**

## 你将学会什么

- PermissionMode 三种模式：default / plan / full_auto
- `PermissionChecker.evaluate()` 的决策顺序（敏感路径硬拒绝 → 工具 allow/deny → 路径规则 → 命令 deny → 模式）
- （可选）sandbox 的边界检查思想（不要求你配置或运行）

## 前置知识

- 第 4 章的工具执行链（知道 `_execute_tool_call` 里权限检查在第几步）
- 第 6 章的 `is_read_only()` 概念
- 了解 `fnmatch`（glob 风格模式匹配，如 `*/.ssh/*`）

## 关键文件（必读）

- `src/openharness/permissions/modes.py`
- `src/openharness/config/settings.py`（`PermissionSettings` / `PathRuleConfig`）
- `src/openharness/permissions/checker.py`
  - `SENSITIVE_PATH_PATTERNS`
  - `PermissionChecker.evaluate(...)`
- （选读）`src/openharness/sandbox/path_validator.py`
- （选读）`src/openharness/utils/shell.py`（命令如何被 wrap 到 sandbox）

## PermissionChecker 的“决策顺序”很重要

读 `PermissionChecker.evaluate()` 时，建议你按“优先级”理解：

1) **敏感路径硬拒绝（不可被用户配置覆盖）**
- `SENSITIVE_PATH_PATTERNS`：例如 `*/.ssh/*`、`*/.aws/credentials`、`*/.openharness/credentials.json`

2) **工具级 allow/deny（显式优先）**
- `denied_tools`：直接拒绝
- `allowed_tools`：直接允许

3) **路径规则（glob 匹配）**
- `path_rules`：匹配到 deny 就拒绝（allow 不会“强行放行敏感路径”）

4) **命令 deny patterns（防止 rm -rf 这类）**
- `denied_commands`：对 `bash` 等命令型工具做额外拦截

5) **模式决策**
- FULL_AUTO：全放行（但仍会被敏感路径硬拒绝拦住）
- read-only：放行
- PLAN：阻断所有 mutating tools
- DEFAULT：mutating tools 需要用户确认

## 你可能会卡住的点（一步一步解释）

### 1）“敏感路径硬拒绝”为什么不能配置绕过？

**原因：防 prompt injection 的最后一道防线。**  
即使用户误装了恶意插件、或模型被诱导，框架仍应保护最高价值的凭据文件。

### 2）Plan mode 到底是什么？

它更像“结构化工作流”：
- 允许你先让模型做计划（读文件、分析）
- 但禁止真正改文件/跑危险命令

对新手很友好：先把方案想清楚，再执行更安全。

## 动手练习（最小代码单元）

运行：

```bash
python3 Study/exercises/ex07_permissions.py
```

脚本会演示：
- read-only vs mutating 的决策差异
- 敏感路径如何被硬拒绝
- path_rules / denied_commands 如何影响结果

你需要完成脚本里的 TODO：
1. 新增一条 path deny 规则（例如禁止 `*/Study/*`），然后验证是否生效
2. 把模式切到 `full_auto`，解释为什么敏感路径仍然会被拒绝

## 自测题（含标准答案）

### Q1：default 模式下，一个 mutating tool 可能出现哪三种结果？
**A：**
1) allowed=True（被 allowlist 放行）  
2) allowed=False 且 requires_confirmation=True（需要用户确认）  
3) allowed=False（被 denylist / 规则 / plan mode / 敏感路径等直接拦截）

### Q2：为什么 `glob/grep` 这类目录工具也要走路径规则？
**A：**它们可以间接读取敏感目录（例如把 `.ssh` 目录作为 root），因此需要在路径层面统一做策略匹配。

### Q3（推演题）：一个 `file_write` 工具要写入 `~/.ssh/authorized_keys`，在 `full_auto` 模式下会发生什么？请说出决策链的每一步。
**A：**
1. `_resolve_permission_file_path` 解析出绝对路径：`/home/user/.ssh/authorized_keys`
2. `PermissionChecker.evaluate()` 检查敏感路径：`*/.ssh/*` 匹配命中
3. 返回 `PermissionDecision(allowed=False, reason="Sensitive path")`
4. `_execute_tool_call` 返回 `is_error=True` 的 ToolResultBlock
5. **即使是 full_auto 模式，敏感路径仍然被硬拒绝**

### Q4（判断题）：以下哪些路径会被 SENSITIVE_PATH_PATTERNS 拦截？
- A) `/home/user/.ssh/id_rsa` → **会**（匹配 `*/.ssh/*`）
- B) `/home/user/.aws/credentials` → **会**（匹配 `*/.aws/credentials`）
- C) `/home/user/Documents/project.py` → **不会**
- D) `/home/user/.openharness/credentials.json` → **会**（匹配 `*/.openharness/credentials.json`）

### Q5（业务逻辑推演题）：default 模式下，用户配置了 `allowed_tools: ["bash"]`，模型尝试执行 `bash rm -rf /`。请描述决策过程。
**A：**
1. 工具名 `bash` 在 allowed_tools 中 → 工具级检查通过
2. 但命令 `rm -rf /` 会被 `denied_commands` 模式匹配拦截（如果配置了相关 deny pattern）
3. 如果没有配置 denied_commands，则因为 `bash` 是 mutating tool + 已在 allowlist → 可能被放行
4. **教训：allowed_tools 只跳过"需要确认"，不能跳过敏感路径和 denied_commands 检查**

## 常见误区

1. **误区：以为 full_auto 模式无任何限制**
   full_auto 只是跳过"用户确认"步骤。敏感路径硬拒绝和 denied_commands 仍然生效。

2. **误区：以为 path_rules 的 allow 规则可以覆盖敏感路径**
   不能。敏感路径检查在 path_rules 之前执行，且不可被用户配置覆盖。

3. **误区：把 Plan mode 当成"只读模式"**
   Plan mode 阻断的是所有 **mutating** tools（`is_read_only() == False`），但只读工具仍然可以执行。它更像是"只允许分析，不允许修改"。

