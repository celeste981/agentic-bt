# Skills 集成说明

本项目的 `agent` 内核支持 Agent Skills 开放规范（`SKILL.md` + YAML frontmatter）。

## 支持能力

1. 自动发现与加载 skills（多来源目录）
2. 将 skill 摘要注入 system prompt 的 `<available_skills>`
3. 显式命令 `/skill:name ...` 服务端展开
4. 模型自主调用 `skill_invoke` 工具加载 skill 正文

## 技能目录与文件格式

推荐目录结构：

```text
skills/
  my-skill/
    SKILL.md
  quick-skill.md
```

- skills 根目录下直接 `.md` 文件会被识别为 skill
- 子目录下仅识别 `SKILL.md`（也兼容 `skill.md`）

`SKILL.md` 示例：

```markdown
---
name: compare
description: Compare two symbols side by side with consistent metrics.
disable-model-invocation: false
---

# Compare Skill

...
```

## 默认搜索路径

加载优先级按顺序（先到先得，重名后者忽略）：

1. `SKILL_PATHS` 环境变量（用 `os.pathsep` 分隔多个路径）
2. 从 `cwd` 向上到 git root 的项目路径：
   - `.agents/skills/`
   - `.pi/skills/`
3. 用户路径：
   - `~/.agents/skills/`
   - `~/.pi/agent/skills/`
   - `~/.agent/skills/`
   - `~/.claude/skills/`
   - `~/.codex/skills/`
   - `~/.cursor/skills/`

## 两种调用方式

1. 显式调用（强制展开）：
   - `/skill:compare 比亚迪 vs 宁德时代`
2. 模型自主调用（推荐）：
   - 模型从 `<available_skills>` 选择 skill
   - 调用 `skill_invoke(name, args)` 获取正文与展开内容
   - 再按 skill 指令继续使用 `market_ohlcv/read/write/edit/compute/bash`

## 安全约束

- `disable-model-invocation: true`：
  - 不会出现在 `<available_skills>`（模型不可见）
  - `skill_invoke` 会拒绝调用
  - 但用户仍可通过 `/skill:name` 显式调用
- 第三方 skill 视为不可信输入，使用前请审查内容。
