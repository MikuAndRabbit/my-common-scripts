# CLI Interface Contract: file-hash-calculator

**Date**: 2026-06-12 | **Plan**: [../plan.md](../plan.md)

## Command Signature

```bash
file-hash-calculator [OPTIONS] [PATH...]
```

## Arguments

| Argument | Required | Multiple | Description |
|----------|----------|----------|-------------|
| `PATH` | No | Yes | 一个或多个文件/目录路径。如不提供且 stdin 非 TTY，则从 stdin 读取（每行一个路径） |

## Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--format` | `-f` | `markdown\|json\|csv\|yaml` | `markdown` | 输出格式 |
| `--output` | `-o` | `PATH` | None (stdout) | 输出文件路径。若文件已存在且非空，交互式确认后覆盖 |
| `--exclude` | `-e` | `PATTERN` | None | glob 风格排除表达式，可多次指定 |
| `--workers` | `-w` | `INT` | `os.cpu_count()` | 并发工作线程数 |
| `--hash-length` | `-l` | `INT` | `256` | BLAKE3 输出长度（bit），必须 > 0 |
| `--help` | `-h` | - | - | 显示帮助信息 |

## Output Format Contracts

### Markdown (default)

```markdown
| Path | Name | Hash |
|------|------|------|
| /absolute/path/to/file.txt | file.txt | abc123... |
| /absolute/path/to/dir/ | dir | def456... |
```

### JSON

```json
[
  {
    "path": "/absolute/path/to/file.txt",
    "name": "file.txt",
    "hash": "abc123...",
    "entry_type": "file"
  },
  {
    "path": "/absolute/path/to/dir",
    "name": "dir",
    "hash": "def456...",
    "entry_type": "directory"
  }
]
```

### CSV

```csv
path,name,hash,entry_type
/absolute/path/to/file.txt,file.txt,abc123...,file
/absolute/path/to/dir,dir,def456...,directory
```

### YAML

```yaml
- path: /absolute/path/to/file.txt
  name: file.txt
  hash: abc123...
  entry_type: file
- path: /absolute/path/to/dir
  name: dir
  hash: def456...
  entry_type: directory
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | 成功完成 |
| 1 | 一般错误（文件不存在、权限不足等） |
| 2 | 参数错误（无效选项值等） |
| 130 | 被 SIGINT 中断（Ctrl+C） |

## Stderr Output

- 进度条：仅在 stderr 输出（`tqdm(file=sys.stderr)`）
- 警告信息：跳过的符号链接、无法读取的文件
- 错误信息：参数错误、致命错误

## Resume Behavior

当 `--output` 指定且检查点文件（`<output>.checkpoint.jsonl`）存在时：
1. 自动加载已有结果
2. 仅处理未完成的条目
3. 检测到文件变更（mtime/size 不匹配）时重新计算
4. 完成后删除检查点文件，生成最终输出

## Format Inference

当 `--output` 指定但 `--format` 未指定时：

| Extension | Inferred Format |
|-----------|----------------|
| `.json` | json |
| `.csv` | csv |
| `.yaml`, `.yml` | yaml |
| 其他 | markdown |

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| 空目录 | 哈希 = `BLAKE3("")`，输出一条 directory 条目 |
| 符号链接 | 跳过，输出 warning 到 stderr |
| 不可读文件 | 输出 error 到 stderr，跳过该文件，继续处理 |
| 重复路径 | 解析为绝对路径后去重 |
| 无路径输入（stdin 为 TTY） | 显示帮助信息，退出码 2 |
| 中断（Ctrl+C） | 检查点文件保留，输出文件包含部分结果 |
| 特殊字符路径 | 完全支持 Unicode 路径 |
