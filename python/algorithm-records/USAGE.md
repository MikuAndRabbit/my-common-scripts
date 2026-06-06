# `algorithm_records.py` 使用指南

`algorithm_records.py` 是一个解析 `Algorithm Records.xlsx` 刷题记录表的 Python
模块, 既可作为库 `import`, 也可以直接当作命令行工具使用.

---

## 1. 数据模型

### 1.1 Excel 文件的结构

整本 workbook 一共 6 个 sheet:

| Sheet         | 含义                                            |
| ------------- | ----------------------------------------------- |
| `Acwing`      | Acwing 平台的刷题记录 (3600 道题, 14 列)         |
| `LeetCode`    | LeetCode 主站的刷题记录 (6000 道题, 22 列)       |
| `LC-Special`  | LeetCode 特别赛/LCP/剑指 等 (211 道, 22 列)      |
| `面试题`      | 程序员面试金典 (108 道, 22 列)                   |
| `牛客`        | 牛客网真题 (58 道, 22 列)                        |
| `颜色备注`    | 颜色 → 难度评价 的图例                          |

数据 sheet 的列布局是相同的:

```
| 题目序号 | 题目名称 |  1  |  2  |  3  | ... | N  |
```

- 第 3 列起每一列代表 "第 N 次刷此题", 表头是整数 `N`;
- 单元格的值是该次刷题的日期 (`datetime`);
- 单元格的**背景颜色**编码了体感难度.

`颜色备注` sheet 里定义了 3 种颜色:

| ARGB         | 含义   |
| ------------ | ------ |
| `FFADD88D` 🟢 | 流畅   |
| `FFF4B382` 🟠 | 卡顿   |
| `FFEF949F` 🔴 | 困难   |

> ⚠️ 实际数据里还可能有少量单元格用了 Excel 的 *theme 颜色* (如 WPS 调色板).
> 解析器会通过 workbook 自带的 ``xl/theme/theme1.xml`` 把
> ``(theme_index, tint)`` 解算成最终 RGB, 再与图例做最近邻匹配 (容差 ≤ 30
> 欧氏距离), 因此 RGB 直填和 theme 调色板两种填色方式都能被正确识别, 不丢颜色.

> 💡 验证过的 ground truth: LeetCode #775 (橙, 解析=卡顿), #1375 (橙, 卡顿),
> #955 (红, 困难), #2155 (绿, 流畅). 全部匹配.

### 1.2 解析后的 Python 数据结构

```
AlgorithmRecords
├── path             : Path
├── color_legend     : dict[str, str]               # 从 workbook 里读出来的
└── problems_by_source : dict[str, list[Problem]]   # 按 sheet 名分组
                          │
                          └── Problem
                              ├── source        : str       # sheet 名
                              ├── problem_id    : int | str # Acwing/LC 是 int; 其它是 str
                              ├── name          : str | None
                              └── attempts      : list[Attempt]
                                                  │
                                                  └── Attempt
                                                      ├── index       : int   # 第几次 (1-based)
                                                      ├── date        : date
                                                      ├── difficulty  : str   # 流畅/卡顿/困难/未标注
                                                      └── color       : str | None
```

---

## 2. 安装 / 依赖

唯一运行时依赖是 [`openpyxl`](https://openpyxl.readthedocs.io), 已在本子项目的
`pyproject.toml` 里声明; 依赖由 [`uv`](https://docs.astral.sh/uv/) 管理.

最常见的用法是通过仓库根目录下的 `./algorithm-records` 包装脚本调用 CLI,
它会自动 `uv run` 本子项目, 首次运行时自动创建虚拟环境并安装依赖, 无需手动
执行 `uv sync`. 想要显式同步一次 (例如离线场景下预热环境):

```bash
uv sync --project python/algorithm-records
```

Python 版本要求: **3.10+** (用到了 `dict[str, ...]` / `int | str` 等新语法,
本子项目 `.python-version` 已锁到 3.10).

---

## 3. 当作库使用

```python
from algorithm_records import parse

records = parse("Algorithm Records.xlsx")

# --- 1. 概览统计 ----------------------------------------------------------
for source, stats in records.summary().items():
    print(source, stats)
# LeetCode {'total_problems': 6000, 'attempted_problems': 2838,
#           'total_attempts': 3478, '难度_流畅': 2093, ...}

# --- 2. 按平台 + 题号精确查找 --------------------------------------------
p = records.find("LeetCode", 1)
print(p.name, p.attempt_count, p.last_attempt.date)
# 两数之和 2 2024-06-18

# 注意非 LeetCode/Acwing 的 problem_id 是字符串
p = records.find("LC-Special", "LCP 01")

# --- 3. 按题名模糊搜索 ---------------------------------------------------
for p in records.search_by_name("两数", source="LeetCode"):
    print(p.problem_id, p.name, p.attempt_count)

# --- 4. 遍历刷题事件 (做日历热力图、按周统计……) --------------------------
from collections import Counter
weekly = Counter()
for problem, attempt in records.all_attempts():
    weekly[attempt.date.isocalendar()[:2]] += 1   # (year, week)

# --- 5. 按日聚合 ---------------------------------------------------------
daily = records.daily_counts()                          # 全平台
daily_lc = records.daily_counts(source="LeetCode")      # 单平台

# --- 6. 导出 JSON --------------------------------------------------------
Path("records.json").write_text(records.to_json(), encoding="utf-8")
```

### 3.1 常用过滤

```python
# 只看至少做过 1 次的题
attempted = list(records.attempted_problems())

# 找出反复刷的题 (重点复习对象)
heavy = [p for p in records.attempted_problems() if p.attempt_count >= 4]

# 找出每次都"困难"的题
hard_every_time = [
    p for p in records.attempted_problems()
    if all(a.difficulty == "困难" for a in p.attempts)
]

# 找出最近一次还是"困难"的题 (说明还没掌握)
still_hard = [
    p for p in records.attempted_problems()
    if p.last_attempt.difficulty == "困难"
]
```

---

## 4. 命令行用法

仓库根目录提供了 `algorithm-records` 包装脚本, 内部会 `uv run` 本子项目里的
`algorithm_records.py`, 同时把当前工作目录原样传给 Python, 因此 `--file` 传相对
路径时按你的 *调用位置* 解析. 推荐用法:

```bash
./algorithm-records <subcommand> [options]
```

如果你想绕过包装脚本, 也可以直接在子项目目录下:

```bash
uv run --project python/algorithm-records python python/algorithm-records/algorithm_records.py <subcommand> [options]
```

全局参数:

| 参数       | 说明                                           | 默认                       |
| ---------- | ---------------------------------------------- | -------------------------- |
| `--file/-f` | xlsx 文件路径                                 | `Algorithm Records.xlsx`   |

### 4.1 `summary` — 概览

```bash
$ ./algorithm-records summary
文件: Algorithm Records.xlsx
颜色图例: {'FFADD88D': '流畅', 'FFF4B382': '卡顿', 'FFEF949F': '困难'}

平台          总题数  已做题  总次数  流畅  卡顿  困难  未标注
------------------------------------------
Acwing        3600      29      29     9     9    11       0
LeetCode      6000    2838    3478  2112   608   758       0
LC-Special     211     211     213   138    39    36       0
面试题            108     107     113    66    17    30       0
牛客              58      58      60    16    22    22       0
```

### 4.2 `find` — 精确查找

```bash
$ ./algorithm-records find LeetCode 1
{
  "source": "LeetCode",
  "problem_id": 1,
  "name": "两数之和",
  "attempt_count": 2,
  "attempts": [
    {"index": 1, "date": "2023-12-31", "difficulty": "流畅", "color": "FFADD88D"},
    {"index": 2, "date": "2024-06-18", "difficulty": "流畅", "color": "FFADD88D"}
  ]
}

$ ./algorithm-records find LC-Special "LCP 01"
```

> CLI 会先尝试 `int(id)`, 再 fallback 到原字符串, 所以 `find Acwing 2` 和
> `find LC-Special "LCP 01"` 都能直接工作.

### 4.3 `search` — 模糊搜索

```bash
$ ./algorithm-records search 两数 --source LeetCode
[LeetCode] 1     两数之和                 次数=2  最近 2024-06-18 (流畅)
[LeetCode] 2     两数相加                 次数=3  最近 2025-09-06 (流畅)
[LeetCode] 167   两数之和 II - 输入有序数组   次数=1  最近 2024-06-17 (流畅)
...
```

不带 `--source` 则跨全平台搜索. 关键字大小写不敏感.

### 4.4 `export` — 导出 JSON

```bash
# 写到文件
$ ./algorithm-records export --out records.json
已写入 records.json (2091097 bytes)

# 打到 stdout, 配合 jq 用
$ ./algorithm-records export | jq '.summary'
```

JSON 顶层结构:

```json
{
  "path": "...",
  "color_legend": {"FFADD88D": "流畅", ...},
  "summary": { "LeetCode": {...}, ... },
  "problems_by_source": {
    "LeetCode": [
      {
        "source": "LeetCode",
        "problem_id": 1,
        "name": "两数之和",
        "attempt_count": 2,
        "attempts": [{"index": 1, "date": "2023-12-31", "difficulty": "流畅", "color": "FFADD88D"}, ...]
      },
      ...
    ],
    ...
  }
}
```

---

## 5. 一些设计取舍 & 边界情况

| 情况                                              | 解析行为                                                     |
| ------------------------------------------------- | ------------------------------------------------------------ |
| Acwing 表头第 13/14 列是空                        | 跳过 (任何非整数表头都被忽略)                                 |
| 行的题号和题名都为空                              | 跳过                                                         |
| 行有题号但题名为空 (Acwing 占位题)                | 保留为 `Problem`, `name=None`, `attempts=[]`                  |
| 单元格日期是字符串 `"2024-01-02"`                 | 自动解析为 `date`; 支持 `-`, `/`, `.` 三种分隔符              |
| 单元格背景色用了 theme 颜色 (如 WPS 调色板)        | 通过 workbook 的 `theme1.xml` 解算 RGB, 与图例最近邻匹配 (阈值 ≤ 30) |
| 单元格背景色解算后与图例所有色差距均 > 阈值       | 归到 `未标注`; 原始 `color` 字段保留解算后 RGB 或 `"theme:<idx>/<tint>"` |
| `颜色备注` sheet 丢失                              | 回落到 `DEFAULT_DIFFICULTY_BY_COLOR` (代码里硬编码的 3 个色)  |
| 一行某些列没有日期                                | 该次刷题不产生 `Attempt` (不会插占位)                          |
| 同一行的 `Attempt.index` 顺序                     | 按表头列号升序排序 (1, 2, 3, ...)                             |
| 找不到题目时 `records.find(...)`                  | 返回 `None` (不抛)                                            |

### 修改图例 / 增加新颜色

如果以后在 `颜色备注` sheet 加新的颜色行 (例如 "未做完"), 不需要改代码 —
`parse()` 每次都会重新读图例. 只要新的颜色出现在数据单元格里, 就会被自动归类
到对应标签.

---

## 6. 文件清单

```
my-common-scripts/
├── algorithm-records              # 包装脚本 (uv run 入口, 仓库根)
└── python/
    └── algorithm-records/
        ├── algorithm_records.py   # 解析器 + CLI 主模块
        ├── pyproject.toml         # uv 管理的依赖声明
        ├── .python-version        # 锁定的 Python 版本
        └── USAGE.md               # 本文档
```

待解析的 `Algorithm Records.xlsx` 不在仓库里, 通过 `--file` 指向你本地的副本即可.
