# Data Model: 文件/目录 BLAKE3 哈希计算器

**Date**: 2026-06-12 | **Plan**: [plan.md](./plan.md)

## Entities

### HashEntry

表示单个文件或目录的哈希计算结果。

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `path` | `str` | 绝对路径 | 非空，文件系统有效路径 |
| `name` | `str` | 文件/目录名（不含路径） | 非空 |
| `hash` | `str` | BLAKE3 哈希值（hex 字符串） | 非空，hex 字符，长度 = `hash_length / 4` |
| `entry_type` | `Literal["file", "directory"]` | 条目类型 | 必须为 `"file"` 或 `"directory"` |
| `mtime` | `float` | 文件修改时间（Unix timestamp） | 用于断点续算变更检测 |
| `size` | `int` | 文件大小（字节），目录为 0 | >= 0 |

**Validation Rules**:
- 文件 HashEntry：`hash = BLAKE3(file_content, length=hash_length)`
- 目录 HashEntry：`hash = BLAKE3("#".join(sorted(child_hashes)), length=hash_length)`
- `mtime` 和 `size` 用于断点续算时的变更检测

**State Transitions**: N/A（无状态实体）

### ExclusionPattern

表示一个排除规则。

| Field | Type | Description |
|-------|------|-------------|
| `pattern` | `str` | glob 风格排除表达式（gitignore 语法） |
| `compiled` | `pathspec.PathSpec` | 编译后的匹配对象 |

**Validation Rules**:
- Pattern 必须为有效的 gitignore 规则字符串
- 支持 `*`, `**`, `?`, `[abc]` 等 gitignore 标准语法

### CheckpointEntry

表示断点续算中一条已完成的记录。

| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | 绝对路径（主键） |
| `hash` | `str` | BLAKE3 哈希值 |
| `entry_type` | `str` | `"file"` 或 `"directory"` |
| `name` | `str` | 文件/目录名 |
| `mtime` | `float` | 记录时的文件修改时间 |
| `size` | `int` | 记录时的文件大小 |

**Resume Logic**:
1. 读取检查点文件，构建 `{path: CheckpointEntry}` 映射
2. 对每个待计算路径，检查是否存在 checkpoint entry
3. 若存在且 `mtime` 和 `size` 匹配当前文件 → 跳过，复用哈希
4. 若存在但 `mtime`/`size` 不匹配 → 重新计算
5. 若不存在 → 正常计算

## Relationships

```text
InputPaths (1..N) ──► HashEntry (1..N per input path)
                           │
                           ├── file:   直接计算 BLAKE3(content)
                           └── directory: 递归计算子节点哈希后合并
                                  │
                                  └── children: list[HashEntry]

ExclusionPattern (0..N) ──► Directory Traversal (过滤)
CheckpointEntry (0..N)  ──► Resume Logic (跳过已完成)
```
