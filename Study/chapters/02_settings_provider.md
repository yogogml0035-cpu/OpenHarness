# 第 2 章：配置系统（Settings）与 Provider/Auth 业务逻辑

这一章要解决的问题：**“OpenHarness 如何决定用哪个 provider、哪个模型、用什么方式拿到凭据？”**

## 你将学会什么

- Settings 的四层优先级：CLI > 环境变量 > 配置文件 > 默认值
- Profile（ProviderProfile）如何把”workflow 视角”的配置投影回旧的 flat 字段
- Provider 检测（detect_provider）与 API Client 选择的逻辑位置

## 前置知识

- 第 1 章的目录全景图（知道 `config/` 和 `api/` 的位置）
- 了解 Pydantic BaseModel 的基本用法（字段、默认值、序列化）
- 知道”配置优先级”的概念（类似 CSS 优先级：越具体的来源越高）

## 关键文件（必读）

- `src/openharness/config/settings.py`
  - `class Settings`
  - `merge_cli_overrides()` / `materialize_active_profile()` / `sync_active_profile_from_flat_fields()`
  - `resolve_auth()`（知道它干什么即可，练习不会真的用到外部登录）
- `src/openharness/config/paths.py`：配置/数据目录的默认位置与 env 覆盖
- `src/openharness/api/provider.py`：`detect_provider()` / `auth_status()`
- `src/openharness/ui/runtime.py`：`_resolve_api_client_from_settings()`（runtime 里选 client 的地方）

## Settings 的“业务含义”（不是字段堆砌）

你可以把 Settings 理解成三块：

1) **模型调用层**
- `model` / `max_tokens` / `base_url` / `api_format` / `provider` / `timeout`

2) **安全与行为层**
- `permission`（权限模式、允许/拒绝工具、路径规则）
- `hooks`（生命周期钩子）
- `sandbox`（可选的命令沙箱）

3) **扩展层**
- `enabled_plugins` / `mcp_servers` / `memory` / `theme` / `output_style`

最关键的是 `profiles + active_profile`：
- 新设计倾向于“工作流/ProviderProfile 视角”
- 但为了兼容，仍保留一些 flat 字段（`model/provider/api_format/...`）
- `materialize_active_profile()` 会把 active_profile 的内容“投影”回 flat 字段，确保 runtime 用的是一致的一套值

## Provider/Auth 的选择逻辑（读代码路线）

按这条线读会很顺：

1) `load_settings()`（`src/openharness/config/settings.py`）
   - 如果 `~/.openharness/settings.json` 存在 → 读文件 → 合并默认值
   - 再应用环境变量覆盖（`_apply_env_overrides`）

2) `Settings.merge_cli_overrides(...)`
   - CLI 覆盖会触发 profile 同步与投影：确保 `active_profile + flat 字段`一致

3) `detect_provider(settings)`（`src/openharness/api/provider.py`）
   - 基于 `provider/api_format/model/base_url` 推断 provider 信息（主要用于 UI 展示与能力判断）

4) `_resolve_api_client_from_settings(settings)`（`src/openharness/ui/runtime.py`）
   - 真正决定要创建哪种 API client（Anthropic/OpenAI/Codex/Copilot…）

## 你可能会卡住的点（一步一步解释）

### 1）“profile”和“model”到底谁说了算？

简单规则：
- `active_profile` 先决定 provider/api_format/default_model/base_url/auth_source
- `model` 可能来自：
  - profile 的 `last_model`（用户上次选的）
  - 或 profile 的 `default_model`
  - 或 CLI/env 覆盖

看代码就记住：`materialize_active_profile()` 是把 profile 变成 runtime 可用的“最终设置”。

### 2）为什么要同时保留 flat 字段？

因为 CLI（以及历史调用者）可能只改 `--model` 或 `--api-format`。为了让它们继续工作，需要：
- `sync_active_profile_from_flat_fields()`：把 flat 改动折回 profile
- 再 `materialize_active_profile()`：得到最终一致的 settings

### 3）环境变量覆盖的读取顺序

在 `_apply_env_overrides()` 中，模型名的读取顺序是：
```
ANTHROPIC_MODEL → OPENHARNESS_MODEL
```
也就是说，如果两个变量都设置了，`ANTHROPIC_MODEL` 会优先。这是为了兼容 Anthropic 官方 SDK 的习惯。

## 动手练习（最小代码单元）

运行：

```bash
python3 Study/exercises/ex02_settings_provider.py
```

你会看到脚本打印：
- 默认 Settings 的 active_profile/provider/api_format/model
- 应用不同 overrides 后的变化
- `detect_provider()` 的输出

你需要完成脚本里的两个 TODO：
1. 把 `OPENHARNESS_MODEL` 环境变量覆盖也演示出来（脚本内临时设置即可）
2. 把输出改成“差异视图”：只打印被覆盖的字段

## 自测题（含标准答案）

### Q1：Settings 的优先级顺序是什么？
**A：** CLI 参数 > 环境变量 > `~/.openharness/settings.json` > 默认值。

### Q2：`materialize_active_profile()` 的作用是什么？
**A：**把 `active_profile` 的配置投影回 flat 字段（provider/api_format/base_url/model 等），生成 runtime 使用的“最终 settings”。

### Q3：`detect_provider()` 与 `_resolve_api_client_from_settings()` 的区别？
**A：**
- `detect_provider()`：推断 provider 信息（名字、auth kind、能力）偏”展示/诊断”
- `_resolve_api_client_from_settings()`：真的创建 API client，属于”运行时关键路径”

### Q4（推演题）：如果用户同时设置了 `ANTHROPIC_MODEL=claude-sonnet-4-6` 和 `--model gpt-5.4`，最终用的是哪个模型？为什么？
**A：** 最终用 `gpt-5.4`。因为优先级是 CLI > 环境变量。`merge_cli_overrides(model=”gpt-5.4”)` 会覆盖环境变量设置的值。

### Q5（模块关系判断题）：以下说法哪个是错误的？
- A) `Settings` 里的 `profiles` 字段是一个字典，key 是 profile 名
- B) `materialize_active_profile()` 会修改原 Settings 对象
- C) `_apply_env_overrides()` 是一个模块级函数，不是 Settings 的方法

**A：** B 是错误的。`materialize_active_profile()` 返回一个**新的 Settings 对象**，不会修改原对象（Pydantic model 的 immutability 原则）。

## 常见误区

1. **误区：以为 Settings 是从一个地方读取的**
   实际有四层来源叠加，且 profile 还会把值”投影”回 flat 字段。理解 `materialize_active_profile()` 的作用是关键。

2. **误区：以为 `detect_provider()` 直接影响模型调用**
   `detect_provider()` 只是推断和展示，真正创建 API client 的是 runtime 里的 `_resolve_api_client_from_settings()`。

3. **误区：以为环境变量 `OPENHARNESS_MODEL` 总是最高优先级**
   实际上 CLI 参数 > 环境变量。且环境变量内部 `ANTHROPIC_MODEL` 优先于 `OPENHARNESS_MODEL`。

