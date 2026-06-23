# 上下文压缩技能

`context-compressor` 是一个面向 Codex、Claude Code、cc-switch 等终端 AI 的技能，用来压缩、保存和召回项目上下文。它会在技能目录旁创建本地项目记忆库，保存 `PROJECT.md`、`CONTEXT.md`、`INDEX.md`、会话摘要、里程碑和快照。

## 安装到 Codex

克隆本仓库，然后把技能目录复制或链接到 Codex 的技能目录中。

### Windows PowerShell

```powershell
git clone https://github.com/<owner>/<repo>.git
Copy-Item -Recurse .\<repo>\context-compressor "$env:USERPROFILE\.codex\skills\context-compressor"
```

### macOS / Linux

```bash
git clone https://github.com/<owner>/<repo>.git
mkdir -p ~/.codex/skills
cp -R <repo>/context-compressor ~/.codex/skills/context-compressor
```

## 安装到 Claude Code

### Windows PowerShell

```powershell
git clone https://github.com/<owner>/<repo>.git
Copy-Item -Recurse .\<repo>\context-compressor "$env:USERPROFILE\.claude\skills\context-compressor"
```

### macOS / Linux

```bash
git clone https://github.com/<owner>/<repo>.git
mkdir -p ~/.claude/skills
cp -R <repo>/context-compressor ~/.claude/skills/context-compressor
```

安装后请重启终端 AI 会话。

## 一键安装

在仓库根目录运行：

```bash
bash skills.sh
```

这会把仓库里的每个技能安装到 Codex 和 Claude 的技能目录中。你也可以使用 `bash skills.sh codex`、`bash skills.sh claude` 或 `bash skills.sh ccswitch` 只安装到指定目标；`bash skills.sh all` 会安装到全部三个目标。

在 Windows 上，最简单的是使用 cmd 包装器：

```powershell
.\skills.cmd ccswitch
```

如果你想直接在 PowerShell 中执行脚本，可以这样运行：

```powershell
.\skills.ps1
```

PowerShell 版本支持相同的目标参数：`codex`、`claude`、`ccswitch`、`both` 和 `all`。

## cc-switch

要让技能能在 cc-switch 中被检索到，请把它安装到 cc-switch 的技能目录，并刷新本地注册表：

```bash
bash skills.sh ccswitch
```

这会把技能复制到 `~/.cc-switch/skills/context-compressor`，并注册到 cc-switch 的本地数据库。

## 使用方式

直接自然地说：

```text
压缩这个项目的上下文，方便我之后继续。
```

或者显式调用技能：

```text
使用 $context-compressor 总结这次会话并保存项目上下文。
```

技能描述支持中文提示：

```text
压缩一下当前项目上下文，方便下次恢复
```

## 直接运行脚本

内置脚本只依赖 Python 标准库，因此也可以直接运行：

```bash
python context-compressor/scripts/context_compressor.py --project /path/to/project compress
python context-compressor/scripts/context_compressor.py --project /path/to/project status --json
python context-compressor/scripts/context_compressor.py --project /path/to/project recall "决策关键词"
```

## 记忆位置

默认情况下，记忆会存放在技能旁边：

```text
context-compressor/context-store/projects/{project-hash}/
```

每个安装副本都有自己独立的本地记忆库。若要使用其他位置，可以传入 `--store /custom/context-store`，或者设置 `WORKBUDDY_CONTEXT_STORE`。

## 仓库内容

```text
context-compressor/
  SKILL.md
  agents/openai.yaml
  references/
  scripts/context_compressor.py
```

只有 `context-compressor/` 文件夹是技能本体。仓库根目录的 `README.md` 只是给 GitHub 用户看的说明。
