# Implementation Plan: 文件/目录 BLAKE3 哈希计算器

**Branch**: `001-file-hash-calculator` | **Date**: 2026-06-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-file-hash-calculator/spec.md`

## Summary

新增一个命令行工具 `file-hash-calculator`，用于计算文件和目录的 BLAKE3 哈希值。支持多输出格式（Markdown/JSON/CSV/YAML）、glob 风格排除表达式、进度条、并发计算和断点续算。采用 Python 实现，遵循项目现有的 `python/<command>/` + 根目录 Bash 包装脚本的结构约定，由 `uv` 管理独立依赖环境。

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: `blake3` (BLAKE3 哈希计算), `tqdm` (进度条), `pyyaml` (YAML 输出), `pathspec` (gitignore 风格路径排除)

**Storage**: 文件系统（输出文件 + 断点续算检查点文件）

**Testing**: pytest

**Target Platform**: macOS, Linux, Windows（跨平台 CLI）

**Project Type**: CLI 工具

**Performance Goals**: 4 线程并发计算 1,000 个文件时，相比单线程至少有 2 倍加速

**Constraints**: 大文件以 64KB 分块流式读取，避免全量加载到内存；输出文件定期刷新以支持断点续算

**Scale/Scope**: 支持 10,000+ 文件的目录树哈希计算

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

项目 constitution 文件为空，无明确约束条款。以下检查基于项目既有约定（CLAUDE.md / README.md 中记录）：

| Gate | Status | Notes |
|------|--------|-------|
| Bash 脚本无文件后缀 | ✅ PASS | 根目录包装脚本命名为 `file-hash-calculator`，无后缀 |
| Python 代码位于 `python/<command>/` | ✅ PASS | 实现代码位于 `python/file-hash-calculator/` |
| 使用 `uv` 管理 Python 依赖 | ✅ PASS | 每个命令独立 `uv` 环境，`pyproject.toml` 声明依赖 |
| 代码文件结构变动需更新 README.md | ✅ PENDING | 实现完成后更新 |
| Git Commit 使用英文 + Conventional Commits | ✅ PENDING | 提交时遵循 |

## Project Structure

### Documentation (this feature)

```text
specs/001-file-hash-calculator/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── cli-interface.md # CLI 接口契约
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
/
├── file-hash-calculator             # 根目录 Bash 包装脚本（uv run 入口）
└── python/
    └── file-hash-calculator/        # Python 实现
        ├── .python-version          # 锁定的 Python 版本（3.10）
        ├── pyproject.toml           # uv 依赖声明
        ├── file_hash_calculator.py  # CLI 主模块
        └── lib/                     # 核心逻辑模块
            ├── __init__.py
            ├── hasher.py            # BLAKE3 哈希计算（文件/目录）
            ├── models.py            # 数据模型（HashEntry 等）
            ├── formatter.py         # 输出格式化（Markdown/JSON/CSV/YAML）
            ├── traverser.py         # 目录遍历 + 排除逻辑
            ├── checkpoint.py        # 断点续算管理
            └── progress.py          # 进度条封装
```

**Structure Decision**: 遵循项目现有约定——Python 实现放在 `python/file-hash-calculator/`，由 `uv` 管理；根目录提供同名 Bash 包装脚本。核心逻辑拆分为独立模块（hasher / formatter / traverser / checkpoint / progress），`file_hash_calculator.py` 作为 CLI 入口组装各模块。

## Complexity Tracking

> 无 Constitution 违规需要说明。
