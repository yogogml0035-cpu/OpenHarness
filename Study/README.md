# Study/ — OpenHarness 学习资料（不含部署/安装）

面向对象：刚接触本项目、希望**读懂架构设计 / 代码功能 / 业务逻辑**的同学。

本目录的目标：
- 建立一张“项目心智地图”：模块分层、关键对象、主流程
- 能沿着入口把一次完整交互跑通（从 CLI → Runtime → Agent Loop → Tools → Permissions/Hooks）
- 能看懂扩展机制（commands / skills / plugins / MCP / tasks / multi-agent）
- 每章都有“动手验证”的最小代码单元 + 自测题（含标准答案）

不包含内容：
- 项目部署、安装、依赖管理、鉴权配置的具体操作步骤（你可以先跳过）

## 使用方式（建议按顺序）

1. 读学习路线：`Study/plan.md`
2. 按章节阅读：`Study/chapters/01_repo_map.md` → `...` → `Study/chapters/10_mcp_tasks_ui_swarm.md`
3. 每章最后运行对应练习：`Study/exercises/` 下的 `ex*.py`
4. 做完每章自测（题目 + 标准答案都在章节末尾）
5. 最后做综合验收：`Study/chapters/99_final_assessment.md`

## 练习脚本怎么跑

约定：从仓库根目录运行（也就是本项目目录），例如：

```bash
python3 Study/exercises/ex01_repo_map.py
```

说明：
- 练习脚本会自动把 `src/` 加到 `sys.path`，不要求你先把包安装到全局环境。
- 所有练习**默认不需要 API Key**，不会发起真实模型调用；如果某个练习涉及外部能力，会在脚本/章节里明确标注为“只读学习”。

## 目录结构

```
Study/
  plan.md                 # 学习路线 + 建议节奏
  chapters/               # 每章资料（Markdown）
  exercises/              # 每章最小可运行代码（Python）
```

