#!/usr/bin/env python3
"""Cherry Studio 模板排版 Review 脚本
检查单个/多个 slide XML 的排版问题：越界、溢出、重叠、错位、格式异常。
用法:
    python3 review_layout.py --input slide01.xml            # 单文件
    python3 review_layout.py --dir templates/               # 目录全检
    python3 review_layout.py --input slide01.xml --json     # JSON 输出
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── 画布 ──
CANVAS_W, CANVAS_H = 960, 540

# ── 文本宽度估算（无渲染时的近似）──
def est_text_width(text: str, font_size: float) -> float:
    """估算文本像素宽度：CJK≈字号，拉丁≈0.55×，数字≈0.6×，空格≈0.3×。"""
    w = 0.0
    for ch in text:
        if ch == " ":
            w += font_size * 0.3
        elif ch.isdigit():
            w += font_size * 0.6
        elif ord(ch) > 0x2E80:  # CJK 及全角
            w += font_size
        else:
            w += font_size * 0.55
    return w


def parse_float(s: str | None, default: float = 0.0) -> float:
    if s is None:
        return default
    try:
        return float(s)
    except ValueError:
        return default


# ── 单文件检查 ──
def review_slide(path: Path) -> dict:
    """检查一个 slide XML，返回问题列表。"""
    c = path.read_text(encoding="utf-8")
    issues: list[dict] = []

    def issue(level: str, code: str, message: str, element: str = "") -> None:
        issues.append({"level": level, "code": code, "message": message, "element": element})

    # 1. 颜色格式异常（历史 bug：(3, 'rgba...' 或 'rgba...' 包裹）
    if "(3, '" in c:
        issue("error", "bad_color_format", "存在 (3, 'rgba... 异常颜色格式（历史污染）")
    bad_colors = re.findall(r'color="\'[^"]+"', c)
    if bad_colors:
        issue("error", "bad_color_format", f"存在 {len(bad_colors)} 处引号包裹颜色")

    # 2. border width 必须整数
    for m in re.finditer(r'<border[^>]*width="([\d.]+)"', c):
        v = m.group(1)
        if "." in v:
            issue("error", "border_width_decimal", f"border width={v} 非整数（schema 要求 nonNegativeInteger）")

    # 3. fontSize 最小 6
    for m in re.finditer(r'fontSize="([\d.]+)"', c):
        v = parse_float(m.group(1))
        if v < 6:
            issue("error", "font_size_too_small", f"fontSize={v} 小于最小值 6")

    # 4. 越界 / 负坐标（所有带 topLeftX/topLeftY 的元素）
    for m in re.finditer(
        r'<[^>]*?topLeftX="([-\d.]+)"[^>]*?topLeftY="([-\d.]+)"[^>]*?width="([\d.]+)"[^>]*?height="([\d.]+)"',
        c,
    ):
        x, y, w, h = (parse_float(m.group(i)) for i in range(1, 5))
        if x < -0.5 or y < -0.5:
            issue("error", "negative_coord", f"负坐标 ({x},{y})")
        if x + w > CANVAS_W + 0.5 or y + h > CANVAS_H + 0.5:
            issue("error", "out_of_bounds", f"越界 ({x},{y}) {w}x{h} 超出 {CANVAS_W}x{CANVAS_H}")

    # 5. 文本溢出（单行不换行 wrap=false 场景）
    for m in re.finditer(
        r'<shape type="text"[^>]*topLeftX="([\d.]+)"[^>]*topLeftY="([\d.]+)"[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"[^>]*>(.*?)</shape>',
        c,
        re.DOTALL,
    ):
        x, y, w, h = (parse_float(m.group(i)) for i in range(1, 5))
        content = m.group(5)
        wrap_m = re.search(r'wrap="(\w+)"', content)
        wrap = wrap_m.group(1) if wrap_m else "true"
        fs_m = re.search(r'fontSize="([\d.]+)"', content)
        fs = parse_float(fs_m.group(1), 14)
        line_spacing_m = re.search(r'lineSpacing="([\d.]+)"', content)
        ls = parse_float(line_spacing_m.group(1), 1.2) if line_spacing_m else 1.2

        for p in re.finditer(r"<p>(.*?)</p>", content, re.DOTALL):
            text = p.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            if not text.strip():
                continue
            # 装饰引号（" 或 ' 单独成行）不检查溢出——故意超出框的视觉元素
            if re.fullmatch(r"[“”\"'‘’]{1,2}", text.strip()):
                continue
            ew = est_text_width(text, fs)
            if wrap == "false":
                # 不换行：必须单行放得下
                if ew > w * 1.02:
                    issue(
                        "error", "text_overflow_no_wrap",
                        f"文本溢出（不换行）: “{text[:20]}...” 估算{ew:.0f}px > 框{w:.0f}px",
                        f"({x},{y}) {w}x{h}",
                    )
            else:
                # 换行：行数 × 行高 vs 框高
                lines = max(1, int(ew / max(w, 1)) + 1)
                need_h = lines * fs * ls
                # 大数字强调块（fs≥24 且内容短）允许 30% 余量——关键数据放大是设计
                tolerance = 1.30 if (fs >= 24 and len(text) <= 4) else 1.05
                if need_h > h * tolerance:
                    issue(
                        "error", "text_overflow_wrap",
                        f"文本溢出（换行）: “{text[:20]}...” 需{lines}行×{fs*ls:.0f}px={need_h:.0f}px > 框高{h:.0f}px",
                        f"({x},{y}) {w}x{h}",
                    )

    # 6. 重叠：文本元素之间（bbox 相交且非嵌套）
    texts = []
    for m in re.finditer(
        r'<shape type="text"[^>]*topLeftX="([\d.]+)"[^>]*topLeftY="([\d.]+)"[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"[^>]*>(.*?)</shape>',
        c,
        re.DOTALL,
    ):
        x, y, w, h = (parse_float(m.group(i)) for i in range(1, 5))
        content = m.group(5)
        first_p = re.search(r"<p>(.*?)</p>", content, re.DOTALL)
        label = first_p.group(1)[:12] if first_p else "?"
        # 跳过装饰引号（视觉元素允许重叠）
        if re.fullmatch(r"[“”\"'‘’]{1,2}", label.strip()):
            continue
        texts.append((x, y, w, h, label))

    for i in range(len(texts)):
        x1, y1, w1, h1, l1 = texts[i]
        for j in range(i + 1, len(texts)):
            x2, y2, w2, h2, l2 = texts[j]
            # 相交面积计算
            ix = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            iy = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            overlap = ix * iy
            # 忽略极小重叠（1px 内）和完全嵌套（一个在另一个里面是层级而非重叠）
            small = min(w1 * h1, w2 * h2)
            if overlap > 50 and overlap < small * 0.95:
                # 用 label 字符数 × 行高（≈字号）估算实际文字宽度；文字宽度远小于框宽时是框虚宽，不算真重叠
                est_w1 = len(l1) * min(h1, 44) * 0.9
                est_w2 = len(l2) * min(h2, 44) * 0.9
                real_x_overlap = max(0, min(x1 + est_w1, x2 + est_w2) - max(x1, x2))
                if real_x_overlap <= 4:
                    continue
                issue(
                    "warning", "text_overlap",
                    f"文本重叠: “{l1}”({x1:.0f},{y1:.0f},{w1:.0f}x{h1:.0f}) × “{l2}”({x2:.0f},{y2:.0f},{w2:.0f}x{h2:.0f}) 重叠{overlap:.0f}px²",
                )

    # 7. 一致性：页眉 Logo 位置（28x28 @ 44,24）——若有 img
    imgs = re.findall(r'<img[^>]*topLeftX="([\d.]+)" topLeftY="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', c)
    for x, y, w, h in imgs:
        if parse_float(x) != 44 or parse_float(y) != 24:
            # 封面大 Logo 例外：64x64 @ 448,150 附近是封底/封面
            if not (parse_float(w) >= 60 and parse_float(x) > 300):
                issue("info", "logo_position", f"Logo 位置非常规 ({x},{y}) {w}x{h}")

    # 8. 字面换行符（<p> 内 \n 会被渲染省略）
    for m in re.finditer(r"<p>([^<]*\n[^<]*)</p>", c):
        issue("warning", "literal_newline", f"<p> 内含字面换行符（渲染时可能被省略）: “{m.group(1)[:30]}...”")

    # 9. 空段落 / 重复属性（按 tag 精确检查）
    if re.search(r"<p>\s*</p>", c):
        issue("warning", "empty_paragraph", "存在空 <p></p>")
    dup_attrs = set()
    for m in re.finditer(r"<(\w+)([^>]*)>", c):
        tag, attrs_str = m.group(1), m.group(2)
        # 忽略自闭合属性名里的值（粗提取属性名）
        attr_names = re.findall(r'(\w+)="', attrs_str)
        seen = set()
        for a in attr_names:
            if a in seen:
                dup_attrs.add(f"{tag}.{a}")
            seen.add(a)
    if dup_attrs:
        issue("warning", "duplicate_attribute", f"存在重复属性: {sorted(dup_attrs)}")

    return {"file": str(path), "issues": issues}


def main() -> int:
    ap = argparse.ArgumentParser(description="Cherry Studio 模板排版 Review")
    ap.add_argument("--input", help="单个 XML 文件")
    ap.add_argument("--dir", help="目录（检查全部 slide*.xml）")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    files: list[Path] = []
    if args.input:
        files = [Path(args.input)]
    elif args.dir:
        d = Path(args.dir)
        files = sorted(d.glob("slide*.xml"))
    if not files:
        print("错误: 需要 --input 或 --dir", file=sys.stderr)
        return 1

    results = []
    total_errors = 0
    total_warnings = 0
    for f in files:
        r = review_slide(f)
        results.append(r)
        errs = [i for i in r["issues"] if i["level"] == "error"]
        warns = [i for i in r["issues"] if i["level"] == "warning"]
        total_errors += len(errs)
        total_warnings += len(warns)
        if not args.json:
            status = "✅" if not errs else f"❌ {len(errs)} error"
            print(f"{status} {f.name} ({len(r['issues'])} issues, {len(errs)} err, {len(warns)} warn)")
            for i in r["issues"]:
                print(f"  [{i['level']}] {i['code']}: {i['message']}")

    if args.json:
        print(json.dumps({
            "summary": {"files": len(files), "errors": total_errors, "warnings": total_warnings},
            "results": results,
        }, ensure_ascii=False, indent=2))

    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
