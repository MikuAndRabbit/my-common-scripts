# Tasks: 文件/目录 BLAKE3 哈希计算器

**Input**: 设计文档来自 `/specs/001-file-hash-calculator/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: 本功能规格说明中未显式要求测试任务，因此不包含测试阶段。

**Organization**: 任务按用户故事分组，支持各故事的独立实现和测试。

## Format: `[ID] [P?] [Story] 描述`

- **[P]**: 可并行执行（操作不同文件，无依赖关系）
- **[Story]**: 任务所属的用户故事（如 US1, US2, US3）
- 描述中包含精确的文件路径

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 项目初始化和基础结构搭建

- [X] T001 根据实施计划创建项目目录结构：`python/file-hash-calculator/` 和 `python/file-hash-calculator/lib/`
- [X] T002 创建 `python/file-hash-calculator/pyproject.toml`，声明依赖：`blake3`、`tqdm`、`pyyaml`、`pathspec`，指定 Python 版本 >= 3.10
- [X] T003 [P] 创建 `python/file-hash-calculator/.python-version`，锁定 Python 版本为 3.10
- [X] T004 [P] 创建根目录 Bash 包装脚本 `file-hash-calculator`（无后缀），使用 `uv run` 调用 `python/file-hash-calculator/file_hash_calculator.py`

---

## Phase 2: Foundational（阻塞性前置任务）

**Purpose**: 所有用户故事都依赖的核心基础设施，必须优先完成

**⚠️ CRITICAL**: 此阶段完成前，任何用户故事都不能开始

- [X] T005 [P] 在 `python/file-hash-calculator/lib/models.py` 中定义数据模型：`HashEntry`（path/name/hash/entry_type/mtime/size）、`CheckpointEntry`（path/hash/entry_type/name/mtime/size）
- [X] T006 [P] 在 `python/file-hash-calculator/lib/traverser.py` 中实现基础目录遍历逻辑：递归列出所有文件和子目录，返回按深度排序的路径列表（文件在前、目录在后，支持自底向上计算）
- [X] T007 创建 `python/file-hash-calculator/lib/__init__.py`，初始化为空模块

**Checkpoint**: 基础设施就绪 — 用户故事实现可以开始

---

## Phase 3: User Story 1 - 基础文件和目录哈希计算 (Priority: P1) 🎯 MVP

**Goal**: 用户能够计算一个或多个文件/目录的 BLAKE3 哈希值，结果默认以 Markdown 表格输出到终端

**Independent Test**: 对单个文件运行命令，验证输出包含正确的绝对路径、文件名和 BLAKE3 哈希（64 字符 hex）；对目录运行命令，验证所有后代文件和子目录均出现在输出中且哈希值正确

### Implementation for User Story 1

- [X] T008 [P] [US1] 在 `python/file-hash-calculator/lib/hasher.py` 中实现核心哈希计算：文件哈希（64KB 分块流式读取 + BLAKE3 增量 update）、目录哈希（排序子哈希后以 `#` 拼接再计算 BLAKE3）、空目录哈希（`BLAKE3("")`）
- [X] T009 [P] [US1] 在 `python/file-hash-calculator/lib/formatter.py` 中实现 Markdown 表格格式化输出（表头：Path/Name/Hash），支持写入任意 file-like 对象
- [X] T010 [US1] 在 `python/file-hash-calculator/file_hash_calculator.py` 中实现 CLI 入口（使用 argparse）：接受位置参数 PATH（一个或多个）、调用 traverser 收集文件列表、调用 hasher 计算哈希、调用 formatter 输出 Markdown 到 stdout
- [X] T011 [US1] 处理边界情况：符号链接跳过并输出 warning 到 stderr、不可读文件输出 error 到 stderr 并继续、输入路径去重（解析为绝对路径后去重，祖先目录覆盖子路径）

**Checkpoint**: 此时 User Story 1 应完全可用，可独立测试基本哈希计算功能

---

## Phase 4: User Story 2 - 多输出格式 (Priority: P1)

**Goal**: 用户可选择 Markdown（默认）、JSON、CSV 或 YAML 输出格式

**Independent Test**: 对同一输入分别使用四种格式标志运行命令，验证每种输出均为有效的 Markdown/JSON/CSV/YAML 格式且哈希值一致

### Implementation for User Story 2

- [X] T012 [US2] 在 `python/file-hash-calculator/lib/formatter.py` 中扩展格式化器，新增 JSON、CSV、YAML 三种输出格式支持（JSON 数组、CSV 含表头、YAML 列表），所有格式包含 path/name/hash/entry_type 字段
- [X] T013 [US2] 在 `python/file-hash-calculator/file_hash_calculator.py` 中添加 `--format` / `-f` 选项（可选值：markdown/json/csv/yaml，默认 markdown），将格式参数传递给 formatter

**Checkpoint**: 此时 User Story 1 和 2 均可独立工作，四种输出格式全部可用

---

## Phase 5: User Story 3 - 输出到文件及安全检测 (Priority: P2)

**Goal**: 用户可将结果输出到文件；若目标文件已存在且非空，工具会警告并要求确认后才覆盖；长时间计算中定期刷新结果到文件

**Independent Test**: 使用 `--output results.md` 运行命令验证文件被创建；再次运行验证工具警告并要求确认；在计算过程中中断进程验证部分结果已写入文件

### Implementation for User Story 3

- [X] T014 [US3] 在 `python/file-hash-calculator/lib/checkpoint.py` 中实现检查点写入基础功能：以 JSON Lines 格式追加写入 `<output>.checkpoint.jsonl`，每行一个 HashEntry 的 JSON 序列化，支持 `flush()` 确保持久化
- [X] T015 [US3] 在 `python/file-hash-calculator/file_hash_calculator.py` 中添加 `--output` / `-o` 选项：检测目标文件是否存在且非空时交互式提示确认覆盖（显示警告信息，等待 Y/N 输入）；计算过程中每处理完一个条目即写入检查点文件并刷新
- [X] T016 [US3] 实现格式推断逻辑：当指定 `--output` 但未指定 `--format` 时，根据文件扩展名推断格式（`.json` → JSON、`.csv` → CSV、`.yaml`/`.yml` → YAML、其他 → Markdown）
- [X] T017 [US3] 实现计算完成后的最终输出转换：读取 `.checkpoint.jsonl` 文件，按用户指定格式写入最终输出文件，完成后删除检查点文件

**Checkpoint**: 此时 User Story 1-3 均可独立工作，支持输出到文件

---

## Phase 6: User Story 4 - 文件与目录排除 (Priority: P2)

**Goal**: 用户可通过 glob 风格排除表达式跳过不需要哈希的文件或目录

**Independent Test**: 对包含 `.git/`、`node_modules/` 和 `*.log` 文件的目录运行命令并指定排除模式，验证被排除的项不出现在输出中

### Implementation for User Story 4

- [X] T018 [US4] 在 `python/file-hash-calculator/lib/traverser.py` 中扩展遍历器：集成 `pathspec` 库，支持 gitignore 风格排除表达式（`*`/`**`/`?`/`[abc]`），排除的目录及其所有子内容均被跳过，且不影响父目录的哈希计算
- [X] T019 [US4] 在 `python/file-hash-calculator/file_hash_calculator.py` 中添加 `--exclude` / `-e` 选项（可多次指定），将排除模式传递给 traverser

**Checkpoint**: 此时 User Story 1-4 均可独立工作，支持排除模式

---

## Phase 7: User Story 5 - 进度指示 (Priority: P3)

**Goal**: 长时间哈希计算过程中，用户可看到进度条，显示已处理文件数/总数及预估剩余时间

**Independent Test**: 对包含 1000+ 文件的目录运行命令，验证进度条出现并随文件处理更新

### Implementation for User Story 5

- [X] T020 [US5] 在 `python/file-hash-calculator/lib/progress.py` 中封装 `tqdm` 进度条：输出到 `sys.stderr`，显示当前处理文件名和完成百分比，支持总数为 0 时的边界处理
- [X] T021 [US5] 在 `python/file-hash-calculator/file_hash_calculator.py` 中集成进度条：文件遍历完成后获取总数并初始化进度条，每完成一个文件的哈希计算后更新进度

**Checkpoint**: 此时 User Story 1-5 均可独立工作，进度条在 stderr 正常显示

---

## Phase 8: User Story 6 - 并发计算 (Priority: P3)

**Goal**: 用户可指定并发线程数加速哈希计算

**Independent Test**: 对包含 100+ 文件的目录分别以 `--workers 1` 和 `--workers 4` 运行，验证并行版本更快且结果一致

### Implementation for User Story 6

- [X] T022 [US6] 在 `python/file-hash-calculator/lib/hasher.py` 中实现并发哈希计算：使用 `concurrent.futures.ThreadPoolExecutor`，将文件列表分发给线程池并行计算文件哈希；目录哈希在文件哈希全部完成后单线程计算（确保确定性排序）
- [X] T023 [US6] 在 `python/file-hash-calculator/file_hash_calculator.py` 中添加 `--workers` / `-w` 选项（默认值 `os.cpu_count()`），将并发数传递给 hasher

**Checkpoint**: 此时 User Story 1-6 均可独立工作，支持并发加速

---

## Phase 9: User Story 7 - 断点续算 (Priority: P3)

**Goal**: 计算中断后（Ctrl+C/系统崩溃），用户可重新运行相同命令从断点恢复，仅处理未完成的文件

**Independent Test**: 以 `--output results.json` 启动计算，中途中断，重新运行相同命令，验证仅未处理文件被计算且最终输出完整正确

### Implementation for User Story 7

- [X] T024 [US7] 在 `python/file-hash-calculator/lib/checkpoint.py` 中扩展断点续算功能：实现 `load_checkpoint()` 读取已有 `.checkpoint.jsonl` 并构建 `{path: CheckpointEntry}` 映射；实现 `is_stale()` 方法通过比较文件当前 mtime/size 与检查点记录判断是否需要重新计算
- [X] T025 [US7] 在 `python/file-hash-calculator/file_hash_calculator.py` 中实现续算逻辑：启动时检测检查点文件是否存在，若存在则加载已完成条目；遍历待处理列表时跳过 mtime/size 均匹配的已完成条目；新增条目追加写入检查点文件
- [X] T026 [US7] 实现 SIGINT（Ctrl+C）信号处理：捕获 `KeyboardInterrupt`，确保检查点文件已刷新后以退出码 130 退出，输出文件保留部分结果

**Checkpoint**: 此时 User Story 1-7 均可独立工作，支持断点续算

---

## Phase 10: User Story 8 - 可配置哈希输出长度 (Priority: P3)

**Goal**: 用户可指定 BLAKE3 哈希的输出长度（bit），默认为 256-bit

**Independent Test**: 分别以 `--hash-length 128` 和 `--hash-length 256` 运行命令，验证输出哈希字符串长度分别为 32 和 64 字符

### Implementation for User Story 8

- [X] T027 [US8] 在 `python/file-hash-calculator/file_hash_calculator.py` 中添加 `--hash-length` / `-l` 选项（默认 256，必须 > 0），将长度参数传递给 hasher 的 `blake3.hexdigest(length=N//8)` 调用；在 `python/file-hash-calculator/lib/hasher.py` 中支持可变哈希长度参数

**Checkpoint**: 此时所有用户故事 (US1-US8) 均可独立工作

---

## Phase 11: Polish & 跨切面关注点

**Purpose**: 影响多个用户故事的改进和收尾工作

- [X] T028 实现 stdin 管道输入支持：在 `python/file-hash-calculator/file_hash_calculator.py` 中检测 stdin 非 TTY 时读取管道输入（每行一个路径），与命令行参数合并后去重；若既无命令行参数且 stdin 为 TTY，显示帮助信息并以退出码 2 退出
- [X] T029 [P] 完善 CLI 帮助信息和退出码：在 argparse 中为所有选项添加中文帮助文本；确保退出码符合契约（0=成功、1=一般错误、2=参数错误、130=中断）
- [X] T030 [P] 更新 `README.md`：在项目文件中新增 `file-hash-calculator` 工具的描述、使用示例和文件结构说明
- [X] T031 按照 `specs/001-file-hash-calculator/quickstart.md` 中的场景逐项验证功能正确性

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 — 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 — **阻塞所有用户故事**
- **User Stories (Phase 3-10)**: 全部依赖 Foundational 阶段完成
  - 用户故事按优先级顺序执行（P1 → P2 → P3）
  - 同优先级内按编号顺序（US1 → US2）
- **Polish (Phase 11)**: 依赖所有用户故事完成

### User Story Dependencies

- **User Story 1 (P1)**: Foundational 完成后即可开始 — 无其他故事依赖
- **User Story 2 (P1)**: Foundational 完成后即可开始 — 依赖 US1 的 formatter 基础架构
- **User Story 3 (P2)**: 依赖 US1（核心计算）和 US2（多格式输出）— checkpoint 机制需要格式化器
- **User Story 4 (P2)**: Foundational 完成后即可开始 — 仅扩展 traverser
- **User Story 5 (P3)**: 依赖 US1（核心计算流程）
- **User Story 6 (P3)**: 依赖 US1（hasher 模块）
- **User Story 7 (P3)**: 依赖 US3（checkpoint 机制）
- **User Story 8 (P3)**: 依赖 US1（hasher 模块）

### Within Each User Story

- 核心模块先于 CLI 集成
- 库模块（lib/）先于入口脚本
- 独立模块标记 [P] 可并行实现

### Parallel Opportunities

- Phase 1 中 T003 和 T004 可并行
- Phase 2 中 T005 和 T006 可并行
- Phase 3 (US1) 中 T008 和 T009 可并行
- Phase 4 (US4) 可与 US3 并行（操作不同文件）
- 所有标记 [P] 的任务可并行执行

---

## Parallel Example: User Story 1

```bash
# 并行启动 US1 的核心模块开发：
Task: "在 python/file-hash-calculator/lib/hasher.py 中实现核心哈希计算"
Task: "在 python/file-hash-calculator/lib/formatter.py 中实现 Markdown 格式化"

# 上述两个任务完成后，再进行 CLI 集成：
Task: "在 python/file-hash-calculator/file_hash_calculator.py 中实现 CLI 入口"
```

---

## Implementation Strategy

### MVP First（仅 User Story 1）

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational（关键 — 阻塞所有故事）
3. 完成 Phase 3: User Story 1（基本哈希计算 + Markdown 输出）
4. **停止并验证**: 独立测试 User Story 1
5. 可演示/可用

### Incremental Delivery

1. Setup + Foundational → 基础设施就绪
2. + User Story 1 → 独立测试 → **MVP!**（基本哈希计算可用）
3. + User Story 2 → 独立测试 → 多格式输出可用
4. + User Story 3 → 独立测试 → 输出到文件可用
5. + User Story 4 → 独立测试 → 排除模式可用
6. + User Story 5 → 独立测试 → 进度条可用
7. + User Story 6 → 独立测试 → 并发加速可用
8. + User Story 7 → 独立测试 → 断点续算可用
9. + User Story 8 → 独立测试 → 可变哈希长度可用
10. + Polish → 完整发布

### Parallel Team Strategy

多人协作场景：

1. 团队共同完成 Setup + Foundational
2. Foundational 完成后：
   - 开发者 A: User Story 1 + User Story 2（核心计算 + 输出格式，紧密相关）
   - 开发者 B: User Story 4（排除模式，仅改 traverser，独立性强）
3. US1+US2 完成后：
   - 开发者 A: User Story 3（输出到文件）
   - 开发者 B: User Story 5 + User Story 6（进度条 + 并发）
4. US3 完成后：
   - 开发者 A: User Story 7（断点续算）
   - 开发者 B: User Story 8（哈希长度）

---

## Notes

- [P] 任务 = 操作不同文件，无依赖关系
- [Story] 标签将任务映射到特定用户故事，便于追踪
- 每个用户故事应可独立完成和测试
- 每个任务或逻辑组完成后提交
- 在任意 checkpoint 处可停下来独立验证该故事
- 避免：模糊任务、同文件冲突、破坏独立性的跨故事依赖
- 所有 Bash 脚本文件无后缀（遵循项目约定）
- Git Commit 使用英文 + Conventional Commits 规范
