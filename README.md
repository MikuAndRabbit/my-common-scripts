# 项目介绍

本项目是一个常用脚本的集合，旨在提高日常开发和系统管理效率。

### 已包含脚本

1. **nvm-global-search**: 极速遍历并搜索所有 nvm 环境（及系统环境）下的全局 npm 包。支持模糊搜索特定包名或列出所有版本的全局包，并显示包版本号。
2. **sync-file**: 比较两个文件的内容（基于哈希），不同则交互式同步。支持 BLAKE3 (优先) 和 SHA-256，跨平台兼容 macOS 和 Linux。
3. **extract_env_from_file**: 动态解析并提取 shell 脚本中 export 的环境变量，输出为 JSON 格式。通过隔离子 Shell 执行并对比环境变量差异实现精确提取。

---

# 项目代码文件结构

下面是本项目的代码文件组织结构（如果代码文件结构有变动应该及时改动下面的内容）：

```text
/
├── .gitignore            # Git 忽略文件配置
├── AGENTS.md             # Gemini CLI 配置/引导文件
├── CLAUDE.md             # Claude CLI 配置/引导文件（软链接到 AGENTS.md）
├── README.md             # 项目说明文档
├── extract_env_from_file # 从 shell 脚本中提取环境变量
├── nvm-global-search     # nvm 全局包搜索脚本
└── sync-file             # 跨平台文件同步脚本
```

---
