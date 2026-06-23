---
name: context-compressor
description: 面向终端 AI 工作流的上下文压缩与项目会话持久化技能，适用于 Codex CLI、Claude Code、cc-switch、WorkBuddy 等。用户只要提到压缩上下文、保存项目记忆、恢复会话、召回之前决定、记录里程碑、查看上下文状态，或使用 /compress、/recall、/summarize、/status、/milestone 这类命令时，都应使用该技能。遇到中文请求如“压缩上下文”“保存上下文”“总结本轮会话”“续接/恢复会话”“召回之前进展”“记录里程碑”“查看上下文状态”“让终端 AI 记住项目进度”时，也应触发。会话开始或结束时，使用该技能加载或刷新 `SKILL.md` 同级目录里的 `PROJECT.md`、`CONTEXT.md`、`INDEX.md` 和 `sessions/`。
---

# 上下文压缩器

## 概览

使用这个技能，可以创建并维护一个本地、按项目隔离的记忆库，让下一次 Codex 会话在不加载整个仓库或完整聊天记录的情况下，也能保持上下文连贯。它会把紧凑上下文存到 `<skill-folder>/context-store/projects/{project-hash}/` 下的 `PROJECT.md`、`CONTEXT.md`、`INDEX.md`、每日会话摘要和快照中。

默认存储位置就在 `SKILL.md` 所在的技能目录里，所以每个安装副本都有自己的本地记忆库。只有在用户明确要求共享或自定义存储时，才使用 `--store` 或 `WORKBUDDY_CONTEXT_STORE` 覆盖默认位置。

内置脚本只依赖 Python 标准库，行为是确定性的：

```bash
python scripts/context_compressor.py --project /path/to/project compress
```

## 核心流程

1. 从用户工作区或 `--project` 解析项目根目录。
2. 如果上下文库不存在，则初始化它。
3. 执行 `compress`，生成或刷新：
   - `PROJECT.md`：第 0 层元数据和持久状态。
   - `CONTEXT.md`：第 1 层紧凑工作上下文，受字节预算限制。
   - `INDEX.md`：第 2 层文件树、符号和 TODO/FIXME 标记。
   - `sessions/`：第 3 层摘要和里程碑。
   - `snapshots/`：JSON 形式的文件树和符号快照。
4. 在有意义的工作结束时，运行 `summarize`，写入已完成工作、决定、变更文件、后续步骤和提醒。
5. 当用户询问之前发生了什么时，先运行 `recall`，不要靠记忆猜。

这个技能本身不能安装真正的终端退出钩子。把用户显式提出的“compress”“summarize this session”“recall”“resume”“session end”或 `/compress` 之类请求视为生命周期边界，并调用脚本。

## 命令

使用技能目录中的脚本路径。如果当前工作目录就是技能目录，那么直接用 `scripts/context_compressor.py` 即可；否则传入绝对路径。

### 初始化

创建某个项目的存储骨架：

```bash
python scripts/context_compressor.py --project /path/to/project init --phase "第一阶段"
```

### 压缩

扫描项目并刷新紧凑上下文：

```bash
python scripts/context_compressor.py --project /path/to/project compress --budget 1000000 --phase "第一阶段"
```

### 总结

持久化一次会话交接，并刷新 `CONTEXT.md`：

```bash
python scripts/context_compressor.py --project /path/to/project summarize \
  --title "已实现上下文压缩技能" \
  --phase "第一阶段" \
  --completed "创建了存储骨架和压缩脚本" \
  --decision "使用技能同级的 context-store，并按项目哈希隔离" \
  --changed-file "context-compressor/scripts/context_compressor.py" \
  --next-step "如需自动化，再接入外部终端钩子" \
  --note "技能脚本只使用 Python 标准库"
```

`--completed`、`--decision`、`--changed-file`、`--next-step` 和 `--note` 都可以重复使用。`--append` 可用于在已有的同日摘要后继续追加。

### 召回

在本地记忆库中搜索：

```bash
python scripts/context_compressor.py --project /path/to/project recall "项目哈希"
```

### 状态

查看上下文大小和会话数量：

```bash
python scripts/context_compressor.py --project /path/to/project status --json
```

### 里程碑

记录一个不应被压缩掉的持久决定或检查点：

```bash
python scripts/context_compressor.py --project /path/to/project milestone --message "认证迁移已完成并验证。"
```

## 恢复流程

开始或恢复项目时：

1. 先运行 `status`，找到项目存储位置。
2. 先读 `PROJECT.md`。
3. 再读 `CONTEXT.md`，获取当前紧凑工作集。
4. 只有在需要文件树、符号查找或 TODO 上下文时，才读 `INDEX.md`。
5. 对更早的决定、阻塞或交接，使用 `recall <keyword>`。

## 压缩策略

优先保留项目事实，而不是泛泛而谈的评论。保留持久状态、变更文件、决定、阻塞项、命令和后续步骤。避免存储敏感信息。`CONTEXT.md` 的默认字节预算为 1,000,000。

当需要调预算、判断每一层该放什么，或解释取舍时，请阅读 `references/compression-policy.md`。

当你手工编写或审阅会话摘要时，请阅读 `references/session-summary-template.md`。
