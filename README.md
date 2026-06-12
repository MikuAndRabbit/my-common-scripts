# 项目介绍

本项目是一个常用脚本的集合，旨在提高日常开发和系统管理效率。

### 已包含脚本

1. **nvm-global-search**: 极速遍历并搜索所有 nvm 环境（及系统环境）下的全局 npm 包。支持模糊搜索特定包名或列出所有版本的全局包，并显示包版本号。
2. **sync-file**: 比较两个文件的内容（基于哈希），不同则交互式同步。支持 BLAKE3 (优先) 和 SHA-256，跨平台兼容 macOS 和 Linux。
3. **extract_env_from_file**: 动态解析并提取 shell 脚本中 export 的环境变量，输出为 JSON 格式。通过隔离子 Shell 执行并对比环境变量差异实现精确提取。
4. **algorithm-records**: 解析 `Algorithm Records.xlsx` 刷题记录表的命令行工具，支持平台/题号精确查找、题名模糊搜索、整表 JSON 导出与统计概览；颜色填充（含 WPS theme color）会被自动归类为”流畅/卡顿/困难”。底层为 Python 实现（位于 `python/algorithm-records/`），由 `uv` 托管依赖，根目录的同名 Bash 包装脚本会自动 `uv run` 入口模块，详见 `python/algorithm-records/USAGE.md`。
5. **find-markdown-images**: 检测 Markdown 文件中的所有图片引用，按类型（本地/远程/内嵌）分类输出。支持行内图片、尖括号 URL、引用式图片、HTML `<img>` 标签等多种 Markdown 图片语法，可通过 `--json` 输出机器可读结果。支持 `--path-format` 控制本地路径的输出格式（`original` 原始写法 / `absolute` 绝对路径 / `relative` 相对路径），配合 `--path-relative-to` 可指定相对路径的基准目录（`cwd` 当前工作目录 / `file-dir` Markdown 文件所在目录 / 自定义路径）。底层为 Python 实现（位于 `python/find-markdown-images/`），由 `uv` 托管依赖。
6. **file-hash-calculator**: 计算文件和目录的 BLAKE3 哈希值。支持多输出格式（Markdown/JSON/CSV/YAML）、gitignore 风格排除表达式、进度条、并发计算和断点续算。底层为 Python 实现（位于 `python/file-hash-calculator/`），由 `uv` 托管依赖，根目录的同名 Bash 包装脚本会自动 `uv run` 入口模块。

---

# 项目代码文件结构

下面是本项目的代码文件组织结构（如果代码文件结构有变动应该及时改动下面的内容）：

```text
/
├── .gitignore                          # Git 忽略文件配置（含 Python/uv 产物）
├── AGENTS.md                           # Gemini CLI 配置/引导文件
├── CLAUDE.md                           # Claude CLI 配置/引导文件（软链接到 AGENTS.md）
├── README.md                           # 项目说明文档
├── algorithm-records                   # 刷题记录解析器的包装脚本（uv run 入口）
├── extract_env_from_file               # 从 shell 脚本中提取环境变量
├── file-hash-calculator                 # 文件/目录 BLAKE3 哈希计算器入口
├── find-markdown-images                # Markdown 图片检测的包装脚本（uv run 入口）
├── nvm-global-search                   # nvm 全局包搜索脚本
├── sync-file                           # 跨平台文件同步脚本
└── python/                             # 所有基于 Python 的子项目（由 uv 管理）
    ├── algorithm-records/              # `algorithm-records` 命令的实现
    │   ├── .python-version             # 锁定的 Python 版本（3.10）
    │   ├── USAGE.md                    # 详细使用文档
    │   ├── algorithm_records.py        # 解析器 + CLI 主模块
    │   └── pyproject.toml              # uv 依赖声明（openpyxl）
    └── find-markdown-images/           # `find-markdown-images` 命令的实现
        ├── .python-version             # 锁定的 Python 版本（3.10）
        ├── find_markdown_images.py     # 图片检测 + CLI 主模块
        └── pyproject.toml              # uv 依赖声明（无外部依赖）
    └── file-hash-calculator/           # `file-hash-calculator` 命令的实现
        ├── .python-version             # 锁定的 Python 版本（3.10）
        ├── pyproject.toml              # uv 依赖声明（blake3/tqdm/pyyaml/pathspec）
        ├── file_hash_calculator.py     # CLI 主模块
        └── lib/                        # 核心逻辑模块
            ├── __init__.py
            ├── hasher.py               # BLAKE3 哈希计算（文件/目录）
            ├── models.py               # 数据模型
            ├── formatter.py            # 输出格式化（Markdown/JSON/CSV/YAML）
            ├── traverser.py            # 目录遍历 + 排除逻辑
            ├── checkpoint.py           # 断点续算管理
            └── progress.py             # 进度条封装
```

> 约定：纯 Bash 脚本直接放在仓库根，可执行且**无文件后缀**；
> 需要 Python 依赖的命令统一放在 `python/<command>/` 子目录里，由 `uv` 管理虚拟环境，
> 并在仓库根提供同名 Bash 包装脚本作为命令行入口。

---
