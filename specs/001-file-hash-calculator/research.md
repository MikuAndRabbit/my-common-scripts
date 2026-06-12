# Research: 文件/目录 BLAKE3 哈希计算器

**Date**: 2026-06-12 | **Plan**: [plan.md](./plan.md)

## Research Topics

### 1. BLAKE3 Python 库选型

- **Decision**: 使用 `blake3` PyPI 包（官方 Rust 实现的 Python 绑定）
- **Rationale**:
  - 官方维护的 Python 绑定，直接调用 Rust 实现，性能最优
  - 支持 `hash_length` 参数控制输出长度（默认 32 字节/256-bit）
  - 支持增量 `update()` 模式，适合大文件分块流式读取
  - API 简洁：`blake3.blake3(data).hexdigest(length=N)`
- **Alternatives considered**:
  - `pyblake3`：与 `blake3` 相同，`blake3` 是官方推荐的新包名
  - 直接调用系统 `b3sum` 命令：引入外部依赖，跨平台兼容性差，无 Python 级控制

### 2. 进度条库选型

- **Decision**: 使用 `tqdm`
- **Rationale**:
  - Python 生态中最广泛使用的进度条库
  - 支持 `file=sys.stderr` 输出到 stderr（不影响 stdout/文件输出）
  - 支持自定义描述文本和格式
  - 轻量级，API 简单
- **Alternatives considered**:
  - `rich.progress`：功能更丰富但依赖重，引入 `rich` 全家桶
  - `progress`：功能过于简单
  - 自实现：不必要的重复造轮子

### 3. Glob 排除模式实现

- **Decision**: 使用 `pathspec` 库（gitignore 风格路径匹配）
- **Rationale**:
  - Spec 要求 glob-style patterns，与 `.gitignore` 语法一致
  - `pathspec` 直接解析 gitignore 规则文件格式
  - 支持 `**` 递归通配、`*` 单级通配、`?` 单字符通配
  - 支持正向/反向匹配（include/exclude）
- **Alternatives considered**:
  - `fnmatch` 标准库：不支持 `**` 递归匹配，功能不足
  - `glob` 标准库：仅支持正向匹配，不适合排除场景
  - 自实现通配符匹配：容易有边界情况 bug

### 4. YAML 输出

- **Decision**: 使用 `pyyaml`
- **Rationale**:
  - Python YAML 序列化/反序列化的标准库
  - `yaml.safe_dump()` 安全输出，适合数据序列化
  - 与 JSON/CSV 输出在同一层级实现
- **Alternatives considered**:
  - `ruamel.yaml`：功能更强但更重，简单序列化场景不需要
  - 自实现 YAML 输出：格式简单但容易出错

### 5. 断点续算机制设计

- **Decision**: 使用 JSON Lines 格式的检查点文件（`<output>.checkpoint.jsonl`），每行一个 HashEntry 的 JSON 序列化
- **Rationale**:
  - JSON Lines 天然支持追加写入，每条记录独立
  - 中断后文件不损坏（最多丢失最后一行不完整记录）
  - 恢复时读取检查点文件即可获得所有已完成条目
  - 通过比较文件 mtime + size 判断是否需要重新计算
  - 最终输出按用户指定格式转换
- **Alternatives considered**:
  - SQLite 数据库：功能强大但引入额外依赖，过度设计
  - 单 JSON 文件：追加写入复杂，中断时文件容易损坏
  - 复用输出文件本身：输出格式多样（Markdown/CSV 等），解析困难

### 6. 并发计算策略

- **Decision**: 使用 `concurrent.futures.ThreadPoolExecutor`
- **Rationale**:
  - BLAKE3 计算是 I/O 密集型（读文件）而非 CPU 密集型
  - 线程池适合 I/O 密集型任务，GIL 影响小
  - 标准库自带，无额外依赖
  - 支持 `max_workers` 配置
- **Alternatives considered**:
  - `multiprocessing.Pool`：适合 CPU 密集型，进程间通信开销大
  - `asyncio` + `aiofiles`：异步 I/O，但 `blake3` 是同步 API，需要 `run_in_executor`
  - 自实现线程管理：不必要的复杂性

### 7. 目录哈希计算算法

- **Decision**: 递归计算：先计算所有子文件的哈希，再计算子目录的哈希（自底向上），目录哈希 = `BLAKE3("child1_hash#child2_hash#...")`，子哈希按字典序排序
- **Rationale**:
  - Spec 明确规定：sorted, `#`-joined child hashes
  - 自底向上确保目录哈希反映完整子树状态
  - 排序保证确定性（跨平台文件系统遍历顺序可能不同）
- **Alternatives considered**:
  - Merkle tree 结构：过于复杂，不符合 spec 要求
  - 简单拼接文件名+哈希：文件名排序在不同 locale 下可能不一致

### 8. 空目录哈希

- **Decision**: 空目录的哈希 = `BLAKE3("")`（空字符串的 BLAKE3）
- **Rationale**:
  - 无子节点时，待哈希字符串为空
  - 与 spec edge case 描述一致："well-defined constant or the BLAKE3 of an empty string"
  - 简单且确定

### 9. 大文件流式读取

- **Decision**: 以 64KB 块大小分块读取文件，使用 `blake3` 的增量 `update()` API
- **Rationale**:
  - 64KB 是常见的 I/O 缓冲区大小，平衡内存占用和系统调用次数
  - `blake3` 原生支持增量哈希，无需手动拼接
  - 确保 GB 级文件不会耗尽内存
- **Alternatives considered**:
  - `mmap`：依赖 OS 内存映射，大文件可能失败
  - 全量读取：不符合约束要求

### 10. 输出格式推断

- **Decision**: 当指定 `--output` 但未指定 `--format` 时，根据文件扩展名推断格式
- **Rationale**:
  - `.json` → JSON, `.csv` → CSV, `.yaml`/`.yml` → YAML, 其他 → Markdown
  - 符合 spec FR-009 要求
  - 简单直观

### 11. 路径去重策略

- **Decision**: 将输入路径解析为绝对路径后去重，对于目录，若其祖先目录也在输入中则跳过
- **Rationale**:
  - 绝对路径去重简单可靠
  - 祖先目录覆盖子路径的逻辑符合用户直觉
  - 避免重复计算

### 12. Stdin 输入支持

- **Decision**: 通过 `sys.stdin` 读取，每行一个路径，与命令行参数合并
- **Rationale**:
  - 符合 Unix 管道惯例
  - 支持 `find ... | file-hash-calculator` 场景
  - 仅在 stdin 非 TTY 时读取（检测管道输入）
