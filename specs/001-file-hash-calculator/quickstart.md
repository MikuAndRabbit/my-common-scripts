# Quickstart: 文件/目录 BLAKE3 哈希计算器

**Date**: 2026-06-12 | **Plan**: [plan.md](./plan.md)

## 前置条件

- Python 3.10+
- `uv` 已安装（`brew install uv` 或 `pip install uv`）
- 项目已 clone 到本地

## 环境准备

```bash
# 进入项目目录
cd /path/to/my-common-scripts

# uv 会自动根据 pyproject.toml 创建虚拟环境并安装依赖
# 首次运行时会自动完成，无需手动操作
```

## 基础验证场景

### 场景 1：计算单个文件的哈希

```bash
# 创建一个测试文件
echo "hello world" > /tmp/test.txt

# 计算哈希（默认 Markdown 输出）
./file-hash-calculator /tmp/test.txt
```

**期望输出**：Markdown 表格，包含 `/tmp/test.txt` 的绝对路径、名称 `test.txt` 和 BLAKE3 哈希（64 字符 hex）。

### 场景 2：验证确定性

```bash
# 连续运行两次，哈希值应完全相同
./file-hash-calculator /tmp/test.txt
./file-hash-calculator /tmp/test.txt
```

**期望结果**：两次输出的哈希值完全一致。

### 场景 3：JSON 格式输出

```bash
./file-hash-calculator /tmp/test.txt --format json
```

**期望输出**：有效 JSON 数组，包含 `path`、`name`、`hash`、`entry_type` 字段。

### 场景 4：CSV 格式输出

```bash
./file-hash-calculator /tmp/test.txt --format csv
```

**期望输出**：CSV 格式，首行为 `path,name,hash,entry_type`。

### 场景 5：YAML 格式输出

```bash
./file-hash-calculator /tmp/test.txt --format yaml
```

**期望输出**：有效 YAML，包含 path/name/hash/entry_type 字段。

### 场景 6：目录哈希计算

```bash
# 创建测试目录结构
mkdir -p /tmp/testdir/subdir
echo "aaa" > /tmp/testdir/file1.txt
echo "bbb" > /tmp/testdir/file2.txt
echo "ccc" > /tmp/testdir/subdir/file3.txt

# 计算目录哈希
./file-hash-calculator /tmp/testdir --format json
```

**期望输出**：JSON 数组包含 5 个条目：
- `/tmp/testdir/file1.txt`
- `/tmp/testdir/file2.txt`
- `/tmp/testdir/subdir/file3.txt`
- `/tmp/testdir/subdir`（目录）
- `/tmp/testdir`（目录）

目录条目出现在子条目**之后**（自底向上计算）。

### 场景 7：排除模式

```bash
# 排除 .txt 文件
./file-hash-calculator /tmp/testdir --exclude "*.txt" --format json
```

**期望输出**：仅包含目录条目，不包含 `.txt` 文件。

### 场景 8：输出到文件

```bash
./file-hash-calculator /tmp/testdir --output /tmp/result.json
cat /tmp/result.json
```

**期望结果**：`/tmp/result.json` 包含有效的 JSON 结果。

### 场景 9：自定义哈希长度

```bash
./file-hash-calculator /tmp/test.txt --hash-length 128 --format json
```

**期望输出**：哈希字符串长度为 32 字符（128-bit / 4）。

### 场景 10：并发计算验证

```bash
# 创建 100 个测试文件
mkdir -p /tmp/manyfiles
for i in $(seq 1 100); do echo "content $i" > "/tmp/manyfiles/file$i.txt"; done

# 单线程
time ./file-hash-calculator /tmp/manyfiles --workers 1 --format json > /tmp/r1.json

# 4 线程
time ./file-hash-calculator /tmp/manyfiles --workers 4 --format json > /tmp/r4.json

# 结果应完全一致
diff /tmp/r1.json /tmp/r4.json
```

**期望结果**：`diff` 无差异，4 线程版本的 wall-clock 时间明显短于单线程。

### 场景 11：断点续算

```bash
# 启动计算（在后台运行并迅速中断）
./file-hash-calculator /tmp/manyfiles --output /tmp/resume_test.json &
PID=$!
sleep 0.5
kill $PID 2>/dev/null

# 检查点文件应存在
ls -la /tmp/resume_test.json.checkpoint.jsonl

# 恢复计算
./file-hash-calculator /tmp/manyfiles --output /tmp/resume_test.json

# 结果应完整
python3 -c "import json; data=json.load(open('/tmp/resume_test.json')); print(f'Entries: {len(data)}')"
```

**期望结果**：最终输出包含所有 100 个文件的条目 + 目录条目。

### 场景 12：管道输入

```bash
echo "/tmp/test.txt" | ./file-hash-calculator --format json
```

**期望输出**：与直接传参 `/tmp/test.txt` 的结果相同。

## 清理

```bash
rm -rf /tmp/test.txt /tmp/testdir /tmp/manyfiles /tmp/result.json /tmp/r1.json /tmp/r4.json /tmp/resume_test.json*
```
