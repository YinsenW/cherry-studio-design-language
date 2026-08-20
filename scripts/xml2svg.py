#!/usr/bin/env python3
"""XML → SVG 转换器：把飞书 slides 模板 XML 渲染成矢量 SVG（清晰无限缩放）"""
import re, base64, os, glob, sys
from xml.etree import ElementTree as ET

W, H = 960, 540

def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;'))

def rgba_to_hex(rgba):
    """rgba(255,90,95,1) → #FF5A5F"""
    m = re.match(r'rgba\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\)', rgba or '')
    if not m:
        return '#000000'
    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    a = float(m.group(4))
    hexc = f'#{r:02X}{g:02X}{b:02X}'
    if a < 0.99:
        return hexc + f'{int(a*255):02X}'
    return hexc

def parse_float(s, default=0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default

def text_svg(elem, base_dir):
    """text shape → <text> with tspans"""
    x = parse_float(elem.get('topLeftX'))
    y = parse_float(elem.get('topLeftY'))
    w = parse_float(elem.get('width'), 100)
    h = parse_float(elem.get('height'), 20)
    content = elem.find('content')
    if content is None:
        return ''
    fs = parse_float(content.get('fontSize'), 14)
    family = content.get('fontFamily', '思源黑体')
    color = rgba_to_hex(content.get('color', 'rgba(23,23,23,1)'))
    bold = content.get('bold') == 'true'
    align = content.get('textAlign', 'left')
    valign = content.get('verticalAlign', 'top')
    line_spacing = content.get('lineSpacing', 'multiple:1.35')
    ls = 1.35
    m = re.match(r'multiple:([\d.]+)', line_spacing)
    if m:
        ls = float(m.group(1))
    wrap = content.get('wrap', 'true') == 'true'
    autofit = content.get('autoFit', 'normal-auto-fit')

    # 多行：每个 <p> 一行
    lines = [p.text or '' for p in content.findall('p')]
    if not lines:
        lines = [content.text or '']
    # 空行也保留
    line_h = fs * ls

    # 垂直对齐
    total_h = line_h * len(lines)
    if valign == 'middle':
        y0 = y + (h - total_h) / 2 + fs * 0.85
    elif valign == 'bottom':
        y0 = y + h - total_h + fs * 0.85
    else:
        y0 = y + fs * 0.85

    font_weight = 'bold' if bold else 'normal'
    font_family = "'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif"

    anchor = {'left': 'start', 'center': 'middle', 'right': 'end'}.get(align, 'start')
    txt_x = {'left': x, 'center': x + w/2, 'right': x + w}.get(align, x)

    parts = []
    for i, line in enumerate(lines):
        ly = y0 + i * line_h
        parts.append(f'<text x="{txt_x:.1f}" y="{ly:.1f}" font-family="{font_family}" font-size="{fs:.0f}" '
                     f'fill="{color}" font-weight="{font_weight}" text-anchor="{anchor}">'
                     f'{esc(line)}</text>')
    return '\n'.join(parts)

def shape_svg(elem, base_dir):
    """shape → svg 形状"""
    stype = elem.get('type')
    x = parse_float(elem.get('topLeftX'))
    y = parse_float(elem.get('topLeftY'))
    w = parse_float(elem.get('width'), 0)
    h = parse_float(elem.get('height'), 0)
    fill = '#FFFFFF'
    border = None
    border_w = 1
    # fill / border
    f = elem.find('fill/fillColor')
    if f is not None:
        fill = rgba_to_hex(f.get('color', 'rgba(255,255,255,1)'))
    b = elem.find('border')
    if b is not None:
        border = rgba_to_hex(b.get('color', '#000000'))
        border_w = parse_float(b.get('width'), 1)

    stroke = f' stroke="{border}" stroke-width="{border_w}"' if border else ''

    if stype == 'round-rect':
        rx = parse_float(elem.get('radius'))
        if rx <= 0:
            rx = min(16, h/2) if h > 0 else 16
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx:.1f}" fill="{fill}"{stroke}/>'
    if stype == 'rect':
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{stroke}/>'
    if stype == 'ellipse':
        cx, cy = x + w/2, y + h/2
        rx, ry = w/2, h/2
        return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}"{stroke}/>'
    if stype == 'diamond':
        cx, cy = x + w/2, y + h/2
        pts = f"{cx},{y} {x+w},{cy} {cx},{y+h} {x},{cy}"
        return f'<polygon points="{pts}" fill="{fill}"{stroke}/>'
    return ''

def img_svg(elem, base_dir):
    src = elem.get('src', '')
    # 解析 @./xxx.png
    path = src.replace('@./', '')
    full = os.path.join(base_dir, path)
    x = parse_float(elem.get('topLeftX'))
    y = parse_float(elem.get('topLeftY'))
    w = parse_float(elem.get('width'), 20)
    h = parse_float(elem.get('height'), 20)
    if not os.path.exists(full):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#eee"/>'
    with open(full, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(full)[1].lstrip('.').lower() or 'png'
    mime = {'jpg': 'jpeg', 'jpeg': 'jpeg'}.get(ext, ext)
    return f'<image href="data:image/{mime};base64,{b64}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/>'

def table_svg(elem, base_dir):
    x0 = parse_float(elem.get('topLeftX'))
    y0 = parse_float(elem.get('topLeftY'))
    # col widths
    colgroup = elem.find('colgroup')
    col_w = []
    if colgroup is not None:
        for col in colgroup.findall('col'):
            col_w.append(parse_float(col.get('width'), 100))
    parts = []
    cy = y0
    for tr in elem.findall('tr'):
        row_h = parse_float(tr.get('height'), 40)
        cx = x0
        tds = tr.findall('td')
        for i, td in enumerate(tds):
            cw = col_w[i] if i < len(col_w) else 100
            fill = '#FFFFFF'
            f = td.find('fill/fillColor')
            if f is not None:
                fill = rgba_to_hex(f.get('color', 'rgba(255,255,255,1)'))
            parts.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw:.1f}" height="{row_h:.1f}" fill="{fill}" stroke="#ddd" stroke-width="0.5"/>')
            content = td.find('content')
            if content is not None:
                fs = parse_float(content.get('fontSize'), 12)
                color = rgba_to_hex(content.get('color', 'rgba(23,23,23,1)'))
                bold = content.get('bold') == 'true'
                align = content.get('textAlign', 'left')
                family = "'Noto Sans SC', 'PingFang SC', sans-serif"
                txt = ''.join(p.text or '' for p in content.findall('p'))
                anchor = {'left': 'start', 'center': 'middle', 'right': 'end'}.get(align, 'start')
                tx = {'left': cx + 6, 'center': cx + cw/2, 'right': cx + cw - 6}.get(align, cx + 6)
                parts.append(f'<text x="{tx:.1f}" y="{cy + row_h/2 + fs*0.35:.1f}" font-family="{family}" '
                             f'font-size="{fs:.0f}" fill="{color}" font-weight="{"bold" if bold else "normal"}" '
                             f'text-anchor="{anchor}">{esc(txt)}</text>')
            cx += cw
        cy += row_h
    return '\n'.join(parts)

def xml_to_svg(xml_path, out_path=None):
    base_dir = os.path.dirname(os.path.abspath(xml_path))
    c = open(xml_path).read()
    # 去掉 xmlns（避免 ET 命名空间处理）
    c = c.replace('xmlns="https://www.larkoffice.com/sml/2.0"', '')
    root = ET.fromstring(c)
    data = root.find('data')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">']
    parts.append('<rect width="960" height="540" fill="#FFFFFF"/>')
    if data is not None:
        for child in data:
            tag = child.tag
            if tag == 'shape':
                stype = child.get('type')
                if stype == 'text':
                    parts.append(text_svg(child, base_dir))
                else:
                    parts.append(shape_svg(child, base_dir))
            elif tag == 'img':
                parts.append(img_svg(child, base_dir))
            elif tag == 'table':
                parts.append(table_svg(child, base_dir))
    parts.append('</svg>')
    svg = '\n'.join(parts)
    if out_path:
        open(out_path, 'w').write(svg)
    return svg

if __name__ == '__main__':
    tpl = '/Users/cherryai001/.hermes/skills/creative/cherry-studio-design-language/templates/'
    out_dir = '/tmp/tpl-svg/'
    os.makedirs(out_dir, exist_ok=True)
    for f in sorted(glob.glob(tpl + 'slide*.xml')):
        name = os.path.basename(f).replace('.xml', '.svg')
        xml_to_svg(f, out_dir + name)
    print(f"✅ 转换完成: {len(glob.glob(out_dir + '*.svg'))} 个 SVG")
