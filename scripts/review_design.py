#!/usr/bin/env python3
"""Cherry Studio 设计护栏检查（2026-08-20 新增）
检查设计语言规范：颜色白名单、字号层级、结论条、CTA、深色页等。
用法:
    python3 review_design.py --dir templates/       # 目录全检
    python3 review_design.py --input slide01.xml    # 单文件
    python3 review_design.py --dir . --json         # JSON 输出
准出: error=0 必须；warning 人工裁决可放行
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── 设计令牌（单一来源 tokens.yaml；硬编码兜底避免依赖加载失败）──
TOKENS = {
    "allowed_colors": [
        # 品牌核心
        "rgba(255,90,95,1)", "rgba(255,90,95,0.06)", "rgba(255,90,95,0.10)", "rgba(255,90,95,0.12)",
        "rgba(255,160,164,1)", "rgba(255,210,213,1)", "rgba(255,220,222,1)", "rgba(255,240,241,1)",
        "rgba(23,23,23,1)", "rgba(31,35,41,1)", "rgba(72,72,78,1)", "rgba(105,105,112,1)",
        "rgba(88,88,95,1)", "rgba(55,55,58,1)",
        # 边框/背景
        "rgba(214,214,210,1)", "rgba(226,226,224,1)", "rgba(238,238,236,1)",
        "rgba(240,240,238,1)", "rgba(245,245,244,1)", "rgba(247,247,246,1)",
        "rgba(248,248,247,1)", "rgba(250,250,249,1)", "rgba(253,235,237,1)",
        # 白/透明
        "rgba(255,255,255,1)", "rgba(255,255,255,0.65)", "rgba(255,255,255,0.7)",
        "rgba(0,0,0,0)",
        # 科技青（伙伴编码）
        "rgba(55,216,255,1)", "rgba(55,150,200,1)",
        # AI 六色系（含透明度变体）
        "rgba(255,190,70,1)", "rgba(244,93,155,1)", "rgba(244,93,155,0.12)",
        "rgba(43,201,209,1)", "rgba(43,201,209,0.12)", "rgba(166,107,234,1)", "rgba(166,107,234,0.12)",
        "rgba(34,199,106,1)", "rgba(34,199,106,0.12)", "rgba(88,158,247,1)", "rgba(88,158,247,0.12)",
        "rgba(120,220,160,1)",
        # 深色（局部）
        "rgba(17,17,17,1)",
    ],
    "accent_colors": [
        "rgba(255,90,95,1)", "rgba(55,216,255,1)", "rgba(55,150,200,1)",
        "rgba(255,107,157,1)", "rgba(139,124,246,1)", "rgba(74,144,226,1)",
        "rgba(52,199,123,1)", "rgba(245,166,35,1)", "rgba(46,196,182,1)",
    ],
    "font_sizes": {
        "page_title": 30, "card_title": 18, "body": 13, "caption": 11, "footer": 10,
    },
    "conclusion": {"fill": "rgba(253,235,237,1)", "border": "rgba(255,90,95,1)",
                   "text_color": "rgba(255,90,95,1)", "max_per_page": 1},
    "cta_fill": "rgba(23,23,23,1)",
    "dark_bg": "rgba(17,17,17,1)",
}
# 尝试从 tokens.yaml 加载（存在则覆盖）
try:
    import yaml
    _tp = Path(__file__).parent.parent / "tokens.yaml"
    if _tp.exists():
        _d = yaml.safe_load(_tp.read_text(encoding="utf-8"))
        TOKENS["allowed_colors"] = _d["allowed_colors"]
except Exception:
    pass

# ── 单文件检查 ──
def review_slide(path: Path) -> dict:
    try:
        c = path.read_text(encoding="utf-8")
    except OSError as e:
        return {"path": str(path), "errors": [{"code": "read_failed", "message": str(e)}], "warnings": [], "issues": []}

    issues: list[dict] = []
    def issue(level, code, message, element=""):
        issues.append({"level": level, "code": code, "message": message, "element": element})

    # G1: 颜色白名单
    for m in re.finditer(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', c):
        val = f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{m.group(4)})"
        if val not in TOKENS["allowed_colors"]:
            issue("error", "color_not_in_palette", f"颜色不在令牌表: {val}")

    # G2: 强调色限量（每页高饱和强调色 ≤2 种）
    accents = set()
    for m in re.finditer(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*1\)', c):
        val = f"rgba({m.group(1)},{m.group(2)},{m.group(3)},1)"
        if val in TOKENS["accent_colors"]:
            accents.add(val)
    if len(accents) > 2:
        issue("warning", "accent_overuse", f"强调色种类过多: {len(accents)} 种（应 ≤2，含珊瑚红）")

    # G3: 字号层级（页标题≥28 / 卡标题16-18 / 正文12-14 / 标签10-11）
    # 只检查含文字的 <p> 元素；自闭合/空 content 装饰元素豁免
    sizes = []
    # 先剔除自闭合 <content .../> 装饰元素
    _no_selfclose = re.sub(r'<content[^>]*?/>', '', c)
    for m in re.finditer(r'<content[^>]*?fontSize="(\d+)"[^>]*?>(.*?)</content>', _no_selfclose, re.DOTALL):
        body = m.group(2)
        if "<p>" in body and re.sub(r"<[^>]+>", "", body).strip():
            sizes.append(int(m.group(1)))
    for s in set(sizes):
        if s < 10:
            issue("error", "font_below_min", f"字号 {s} 低于下限 10")
    if len(set(sizes)) > 6:
        issue("warning", "font_hierarchy_too_many", f"字号种类过多: {len(set(sizes))} 种（建议 ≤5）")

    # G4: 页面底部禁横贯长胶囊条（浅红/珊瑚粉，y>430 且宽>400 且高<=60）
    for m in re.finditer(
        r'<shape type="round-rect"[^>]*topLeftY="(\d+)"[^>]*width="(\d+)"[^>]*height="(\d+)"[^>]*><fill><fillColor color="rgba\((253,\s*235,\s*237|255,\s*90,\s*95)[^"]*"',
        c,
    ):
        y, w, h = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y > 430 and w > 400 and h <= 60:
            issue("error", "bottom_pill_bar", f"页面底部横贯长胶囊条 (y={y},{w}x{h}) — 禁止")

    # G5: 主 CTA（禁用黑色填充按钮）
    black_btns = len(re.findall(
        r'<shape type="round-rect"[^>]*><fill><fillColor color="rgba\(23,\s*23,\s*23,\s*1\)"',
        c,
    ))
    if black_btns > 1:
        issue("warning", "multi_cta", f"黑色 CTA 数量 >1: {black_btns} 个（黑底 CTA 已禁用，应改白底珊瑚红描边）")
    elif black_btns == 1:
        issue("warning", "black_cta", "发现黑色填充 CTA — 已禁用，应改白底+珊瑚红描边")

    # G8: 深色整页禁用（页面背景不得为深色）
    bg = re.search(r'<style><fill><fillColor color="rgba\((\d+),\s*(\d+),\s*(\d+),\s*1\)"', c)
    if bg:
        r, g, b = int(bg.group(1)), int(bg.group(2)), int(bg.group(3))
        if r < 60 and g < 60 and b < 60:
            issue("error", "dark_page_banned", f"整页深色背景禁用: rgba({r},{g},{b},1)")

    errors = [i for i in issues if i["level"] == "error"]
    warnings = [i for i in issues if i["level"] == "warning"]
    return {"path": str(path), "errors": errors, "warnings": warnings, "issues": issues}


def main() -> int:
    ap = argparse.ArgumentParser(description="Cherry Studio 设计护栏检查")
    ap.add_argument("--input", help="单个 slide XML")
    ap.add_argument("--dir", help="目录（检查全部 slide*.xml）")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    files: list[Path] = []
    if args.input:
        files = [Path(args.input)]
    elif args.dir:
        d = Path(args.dir)
        if not d.exists():
            print(f"错误: 目录不存在 {d}", file=sys.stderr)
            return 1
        files = sorted(d.glob("slide*.xml"))
        if not files:
            print("错误: 目录中没有 slide*.xml", file=sys.stderr)
            return 1
    else:
        print("错误: 需要 --input 或 --dir", file=sys.stderr)
        return 1

    results = []
    total_err = total_warn = 0
    for f in files:
        r = review_slide(f)
        results.append(r)
        total_err += len(r["errors"])
        total_warn += len(r["warnings"])
        status = "❌" if r["errors"] else ("⚠️" if r["warnings"] else "✅")
        print(f"{status} {f.name} ({len(r['issues'])} issues, {len(r['errors'])} err, {len(r['warnings'])} warn)")
        for i in r["issues"]:
            print(f"  [{i['level']}] {i['code']}: {i['message']}")

    if args.json:
        print(json.dumps({"results": results, "summary": {
            "files": len(files), "errors": total_err, "warnings": total_warn,
        }}, ensure_ascii=False, indent=2))

    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())
