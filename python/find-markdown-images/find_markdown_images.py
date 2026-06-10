"""检测 Markdown 文件中的图片引用并按类型（本地/远程/内嵌）分类输出.

支持以下 Markdown 图片语法::

    1. 行内图片:   ![alt](url) / ![alt](url "title")
    2. 尖括号 URL: ![alt](<url with spaces>)
    3. 引用式图片: ![alt][ref] + [ref]: url 定义（含 ![alt][] 折叠形式）
    4. HTML img:   <img src="url"> / <img src='url'> / <img src=url>
                   （src 可出现在标签任意位置，标签可跨行）

URL 分类::

    - data:             → embedded（内嵌）
    - https/http/ftp/…  → remote（远程）
    - 其余              → local（本地：相对路径、绝对路径、Windows 路径等）

本模块既可作为库使用, 也可直接 ``python find_markdown_images.py`` 当 CLI 跑.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

#: ANSI 颜色码.
RESET = "\033[0m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"

#: URL 类型 → 中文标签.
_URL_TYPE_LABEL: dict[str, str] = {
    "local": "本地",
    "remote": "远程",
    "embedded": "内嵌",
}

#: URL 类型 → ANSI 颜色.
_URL_TYPE_COLOR: dict[str, str] = {
    "local": GREEN,
    "remote": BLUE,
    "embedded": YELLOW,
}

# ---------------------------------------------------------------------------
# 正则模式
# ---------------------------------------------------------------------------

# 行内图片: ![alt](url) / ![alt](<url>) / ![alt](url "title")
# 将尖括号和普通 URL 合为一条正则, 避免重复匹配.
_RE_INLINE_IMAGE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]"       # ![alt]
    r"\("                          # (
    r"(?:"
    r"<(?P<url_ab>[^>]+)>"        #   <url in angle brackets>
    r"|"
    r"(?P<url_plain>[^\s)]+)"     #   plain url (no spaces, no ))
    r")"
    r"(?:\s+(?P<title>\"[^\"]*\"|'[^']*'))?"  # optional "title" or 'title'
    r"\)",                         # )
)

# 引用定义: [ref]: url （必须位于行首）.
_RE_REF_DEF = re.compile(
    r"^\[(?P<ref>[^\]]+)\]:\s+"
    r"(?:"
    r"<(?P<url_ab>[^>]+)>"
    r"|"
    r"(?P<url_plain>[^\s>]+)"
    r")"
    r"(?:\s+\"[^\"]*\"|\s+'[^']*')?$",
    re.MULTILINE,
)

# 引用式图片: ![alt][ref] （含 ![alt][] 折叠形式）.
_RE_REF_IMAGE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\[(?P<ref>[^\]]*)\]"
)

# HTML <img> 标签: <img ... src="url" ...> （可跨行, 大小写不敏感）.
_RE_HTML_IMG = re.compile(
    r"<img\s[^>]*?src\s*=\s*"
    r"(?:"
    r"\"(?P<url_dq>[^\"]*)\""
    r"|"
    r"'(?P<url_sq>[^']*)'"
    r"|"
    r"(?P<url_bare>[^\s>]+)"
    r")",
    re.DOTALL | re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImageRef:
    """文件中找到的一处图片引用."""

    url: str                # 原始 URL / 路径
    alt: str | None         # alt 文本 (HTML <img> 无 alt 时为 None)
    image_type: str         # "inline" | "reference" | "html"
    url_type: str           # "local" | "remote" | "embedded"
    line_number: int        # 出现的行号 (1-based)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParseResult:
    """单个 Markdown 文件的解析结果."""

    file_path: Path
    images: list[ImageRef]

    @property
    def has_local(self) -> bool:
        """是否存在本地路径图片."""
        return any(img.url_type == "local" for img in self.images)

    @property
    def has_remote(self) -> bool:
        """是否存在远程路径图片."""
        return any(img.url_type == "remote" for img in self.images)

    @property
    def has_embedded(self) -> bool:
        """是否存在内嵌图片 (data URI)."""
        return any(img.url_type == "embedded" for img in self.images)

    @property
    def local_count(self) -> int:
        return sum(1 for img in self.images if img.url_type == "local")

    @property
    def remote_count(self) -> int:
        return sum(1 for img in self.images if img.url_type == "remote")

    @property
    def embedded_count(self) -> int:
        return sum(1 for img in self.images if img.url_type == "embedded")

    def to_dict(self) -> dict:
        return {
            "file_path": str(self.file_path),
            "has_local": self.has_local,
            "has_remote": self.has_remote,
            "has_embedded": self.has_embedded,
            "local_count": self.local_count,
            "remote_count": self.remote_count,
            "embedded_count": self.embedded_count,
            "images": [img.to_dict() for img in self.images],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# ---------------------------------------------------------------------------
# URL 分类
# ---------------------------------------------------------------------------

# 远程协议前缀.
_REMOTE_PREFIXES = ("https://", "http://", "ftp://", "ftps://", "//")


def _classify_url(url: str) -> str:
    """将 URL 分类为 ``"embedded"`` | ``"remote"`` | ``"local"``."""
    if url.startswith("data:"):
        return "embedded"
    if url.startswith(_REMOTE_PREFIXES):
        return "remote"
    # Windows 绝对路径: C:\ 或 \\server\share
    if re.match(r"^[A-Za-z]:[\\/]", url) or url.startswith("\\\\"):
        return "local"
    # POSIX 绝对路径
    if url.startswith("/"):
        return "local"
    # 其余均为相对本地路径
    return "local"


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _pos_to_line(lines: list[str], pos: int) -> int:
    """将字符位置转换为 1-based 行号."""
    cumulative = 0
    for i, line in enumerate(lines):
        cumulative += len(line) + 1  # +1 for the newline character
        if cumulative > pos:
            return i + 1
    return len(lines)


def _extract_url_from_match(match: re.Match, *url_groups: str) -> str:
    """从正则匹配中提取 URL (多个候选 group 取首个非空值)."""
    for group_name in url_groups:
        value = match.group(group_name)
        if value is not None:
            return value
    return ""


# ---------------------------------------------------------------------------
# 解析函数
# ---------------------------------------------------------------------------


def _collect_reference_definitions(content: str) -> dict[str, str]:
    """收集 Markdown 文件中的所有引用定义, 返回 ``{标签(小写): URL}`` 映射."""
    definitions: dict[str, str] = {}
    for match in _RE_REF_DEF.finditer(content):
        ref = match.group("ref").strip().lower()
        url = _extract_url_from_match(match, "url_ab", "url_plain")
        if ref and url:
            definitions[ref] = url
    return definitions


def _find_inline_images(
    content: str,
    lines: list[str],
    images: list[ImageRef],
    seen_spans: list[tuple[int, int]],
) -> None:
    """查找行内图片 (含尖括号 URL 形式)."""
    for match in _RE_INLINE_IMAGE.finditer(content):
        span = (match.start(), match.end())
        # 检查是否与已匹配的 span 重叠
        if any(s[0] < span[1] and s[1] > span[0] for s in seen_spans):
            continue
        seen_spans.append(span)

        alt = match.group("alt")
        url = _extract_url_from_match(match, "url_ab", "url_plain")
        line_number = _pos_to_line(lines, match.start())
        images.append(ImageRef(
            url=url,
            alt=alt,
            image_type="inline",
            url_type=_classify_url(url),
            line_number=line_number,
        ))


def _find_reference_images(
    content: str,
    lines: list[str],
    images: list[ImageRef],
    seen_spans: list[tuple[int, int]],
    ref_defs: dict[str, str],
) -> None:
    """查找引用式图片."""
    for match in _RE_REF_IMAGE.finditer(content):
        span = (match.start(), match.end())
        # 检查是否与已匹配的 span 重叠
        if any(s[0] < span[1] and s[1] > span[0] for s in seen_spans):
            continue
        seen_spans.append(span)

        alt = match.group("alt")
        ref_key = match.group("ref").strip().lower()
        # 折叠形式 ![alt][]: ref 为空时使用 alt 作为引用键
        if not ref_key:
            ref_key = alt.strip().lower()

        url = ref_defs.get(ref_key)
        if url is None:
            # 引用定义不存在, 跳过并给出警告
            print(
                f"⚠ 未找到引用定义 '{match.group('ref') or alt}' (行 "
                f"{_pos_to_line(lines, match.start())})",
                file=sys.stderr,
            )
            continue

        line_number = _pos_to_line(lines, match.start())
        images.append(ImageRef(
            url=url,
            alt=alt,
            image_type="reference",
            url_type=_classify_url(url),
            line_number=line_number,
        ))


def _find_html_images(
    content: str,
    lines: list[str],
    images: list[ImageRef],
) -> None:
    """查找 HTML <img> 标签中的图片."""
    for match in _RE_HTML_IMG.finditer(content):
        url = _extract_url_from_match(match, "url_dq", "url_sq", "url_bare")
        if not url:
            continue
        line_number = _pos_to_line(lines, match.start())

        # 尝试提取 alt 属性
        alt_match = re.search(
            r'alt\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\S+))',
            match.group(0),
            re.IGNORECASE,
        )
        alt: str | None = None
        if alt_match:
            alt = alt_match.group(1) or alt_match.group(2) or alt_match.group(3)

        images.append(ImageRef(
            url=url,
            alt=alt,
            image_type="html",
            url_type=_classify_url(url),
            line_number=line_number,
        ))


def parse(path: str | Path) -> ParseResult:
    """解析 Markdown 文件, 提取所有图片引用.

    Parameters
    ----------
    path :
        Markdown 文件路径.

    Returns
    -------
    ParseResult
        解析结果, 包含所有图片引用及其分类信息.

    Raises
    ------
    FileNotFoundError
        文件不存在.
    ValueError
        路径不是普通文件.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"找不到文件: {path}")
    if not path.is_file():
        raise ValueError(f"不是普通文件: {path}")

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    images: list[ImageRef] = []
    seen_spans: list[tuple[int, int]] = []

    # Step 1: 收集引用定义
    ref_defs = _collect_reference_definitions(content)

    # Step 2: 查找行内图片
    _find_inline_images(content, lines, images, seen_spans)

    # Step 3: 查找引用式图片
    _find_reference_images(content, lines, images, seen_spans, ref_defs)

    # Step 4: 查找 HTML <img> 标签
    _find_html_images(content, lines, images)

    return ParseResult(file_path=path, images=images)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_output(result: ParseResult) -> str:
    """格式化人类可读的输出文本."""
    lines: list[str] = []

    # 文件名
    lines.append(f"📄 文件: {result.file_path}")
    lines.append("")

    # 图片检测摘要
    lines.append("🔍 图片检测:")
    for url_type, label in _URL_TYPE_LABEL.items():
        has = getattr(result, f"has_{url_type}")
        count = getattr(result, f"{url_type}_count")
        color = _URL_TYPE_COLOR[url_type]
        status = f"{color}✅ 存在{RESET}" if has else f"❌ 不存在"
        count_info = f" ({count} 张)" if has else ""
        lines.append(f"  {label}图片: {status}{count_info}")
    lines.append("")

    # 图片列表
    if result.images:
        lines.append("📋 图片列表:")
        # 计算列宽
        max_url_len = max(len(img.url) for img in result.images)
        url_col_width = max(max_url_len, 10)

        # 表头
        header = (
            f"  {DIM}{'#':>3}  "
            f"{'类型':　<4}  "
            f"{'URL':<{url_col_width}}  "
            f"{'行号':>4}{RESET}"
        )
        lines.append(header)

        for i, img in enumerate(result.images, 1):
            color = _URL_TYPE_COLOR[img.url_type]
            label = _URL_TYPE_LABEL[img.url_type]
            line = (
                f"  {i:>3}  "
                f"{color}{label}{RESET}    "
                f"{img.url:<{url_col_width}}  "
                f"{img.line_number:>4}"
            )
            lines.append(line)

        lines.append("")

    # 统计
    total = len(result.images)
    parts: list[str] = []
    if result.local_count:
        parts.append(f"{GREEN}本地: {result.local_count}{RESET}")
    if result.remote_count:
        parts.append(f"{BLUE}远程: {result.remote_count}{RESET}")
    if result.embedded_count:
        parts.append(f"{YELLOW}内嵌: {result.embedded_count}{RESET}")
    summary = ", ".join(parts) if parts else "无"
    lines.append(f"📊 统计: 共 {total} 张图片 ({summary})")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    """CLI 入口."""
    parser = argparse.ArgumentParser(
        description="检测 Markdown 文件中的所有图片引用，按类型（本地/远程/内嵌）分类输出",
    )
    parser.add_argument(
        "file",
        type=str,
        help="Markdown 文件路径",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="以 JSON 格式输出 (适合脚本调用)",
    )

    args = parser.parse_args(argv)

    try:
        result = parse(args.file)
    except FileNotFoundError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json_output:
        print(result.to_json())
    else:
        print(_format_output(result))


if __name__ == "__main__":
    main()
