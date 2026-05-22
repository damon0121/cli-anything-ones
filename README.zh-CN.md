# cli-anything-ones

只读的 CLI-Anything ONES 工单读取工具，面向编码代理和本地命令行使用。

## 项目简介

`cli-anything-ones` 用于解析 ONES 工单链接、读取工单详情、读取评论和字段信息，并在需要时下载附件。该工具只读取 ONES 数据，不会写评论、改状态、改字段或执行其他写操作。

## 功能

- 解析 ONES 工单 URL。
- 读取工单详情、评论、自定义字段和附件元数据。
- 在诊断问题时下载工单附件。
- 提供 OpenCode skill：`skills/cli-anything-ones`。
- 保持只读，不会写回 ONES。

## 仓库结构

```text
agent-harness/                  Python 包和 CLI 实现
agent-harness/ONES.md           CLI 行为和安全说明
agent-harness/cli_anything/ones Python 源码、测试和包内 README
skills/cli-anything-ones        OpenCode 使用该 CLI 的 skill
```

## 安装

从仓库根目录执行：

```bash
uv tool install -e ./agent-harness --python python3.11 --force
```

该命令会安装 `cli-anything-ones` 可执行命令。

如果当前目录已经是 `agent-harness`，可以改用：

```bash
uv tool install -e . --python python3.11 --force
```

安装后验证：

```bash
cli-anything-ones --version
cli-anything-ones doctor --json
```

## 配置

调用 ONES API 的命令需要 ONES access token。可以临时导出环境变量：

```bash
export ONES_ACCESS_TOKEN=...
```

也可以保存到本地 CLI 配置文件：

```bash
cli-anything-ones config set-token
```

保存后的 token 位于：

```text
~/.config/cli-anything-ones/config.json
```

配置文件会使用私有权限写入。若同时存在环境变量和本地配置，`ONES_ACCESS_TOKEN` 环境变量优先。

可选环境变量：

```bash
export ONES_BASE_URL=https://sz.ones.cn
export ONES_TEAM_ID=HbudLR1b
```

当工单 URL 中已经包含 team ID 时，`ONES_TEAM_ID` 可以不设置。

## 使用方法

解析工单 URL，不需要 token：

```bash
cli-anything-ones issue parse "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218" --json
```

读取工单详情：

```bash
cli-anything-ones issue get "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218"
```

输出 JSON，适合程序或代理读取：

```bash
cli-anything-ones issue get "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218" --json
```

下载附件：

```bash
cli-anything-ones attachment download "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218" --output-dir /tmp/ones --json
```

设置本地 token：

```bash
cli-anything-ones config set-token
```

检查本地配置，不会打印 token：

```bash
cli-anything-ones doctor --json
```

程序化使用时，建议优先使用 `--json`。

## 安全说明

- CLI 只读，不会写回 ONES。
- token 从 `ONES_ACCESS_TOKEN` 或本地 CLI 配置文件读取。
- `ONES_ACCESS_TOKEN` 环境变量优先于本地保存的 token。
- token 不会通过命令行参数传入，避免进入 shell history。
- `doctor` 不会打印 token。
- `config set-token` 默认使用隐藏输入，并以 `0600` 权限写入配置文件。
- 临时附件 URL 默认隐藏，只有在需要时才使用 `--include-attachment-urls`。
- 附件下载默认限制在 ONES 可信域名内，只有显式传入 `--allow-external-attachment-hosts` 才允许外部附件域名。

## 开发与测试

从包目录运行测试：

```bash
cd agent-harness
python -m pytest cli_anything/ones/tests
```

也可以使用项目文档中的 uv 方式运行：

```bash
uv run --python python3.11 --with pytest --with click python -m pytest cli_anything/ones/tests -v
```

## License

尚未声明 license。
