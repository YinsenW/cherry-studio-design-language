# Cherry Studio Design Language & PPT Template Library

Cherry Studio 品牌设计语言 v1.0 + **53 页飞书幻灯片（Lark Slides）模板库**，以可复用 SKILL.md 形式提供，供 AI agent 快速产出风格统一的品牌视觉材料。

## 包含什么

```
.
├── SKILL.md                 # 完整设计规范 + 模板库使用工作流 + CLI 命令 + 排障手册
├── templates/
│   ├── INDEX.md             # 53 页场景索引（每页：适用场景/结构/替换清单）
│   └── slide01.xml ~ slide53.xml  # 960×540 飞书 Slides XML 模板
└── assets/
    ├── cherry-logo.png      # 官方 Logo（1024×1024 透明 PNG）
    └── product-placeholder.png  # 产品截图占位图
```

## 模板覆盖

| 类别 | 页数 | 页码 |
|------|------|------|
| 封面 / 转场 / 封底 | 7 | P1-P6, P51 |
| 深色变体（章节页 / 封底） | 2 | P52, P53 |
| 目录 / 导航 | 3 | P7-P9 |
| 文本 / 论证 | 8 | P10-P17 |
| 数据 / 图表 | 8 | P18-P25 |
| 流程 / 架构 | 7 | P26-P32 |
| 产品 / 方案 | 6 | P33-P38 |
| 规划 / 组织 | 6 | P39-P44 |
| 生态 / 社区 | 6 | P45-P50 |

## 快速开始（agent 视角）

1. 读 `templates/INDEX.md` 按内容类型选模板
2. 复制 `slideXX.xml` + `assets/*.png` 到工作目录
3. 按 INDEX 的『替换』清单定点替换示例内容
4. 用官方 lint 校验：`python3 lark-slides/scripts/xml_lint.py --input slide.xml`
5. 通过 `lark-cli slides +create / +add-slide` 发布到飞书

## 设计要点

- 纯白画布 `#FFFFFF` + 粗黑标题 `#171717` + 白卡细边框 `#D6D6D2`
- 珊瑚红 `#FF5A5F` 为唯一品牌强调色（Logo #FF5757）
- 黑按钮 = 唯一 CTA；克制彩线（粉/青/紫/蓝/绿/黄）
- 17 条反模式（禁蓝紫渐变 / 禁珊瑚红铺满 / 禁重阴影玻璃态...）
- 模板实际色板与字号见 SKILL.md（与规范兼容但更精确，以模板为准）

## 依赖

- [larksuite/cli](https://github.com/larksuite/cli)（飞书幻灯片 XML 操作）
- 官方 `xml_lint.py` 校验脚本（lark-slides skill 内）

## License

MIT © 2026 Cherry Studio
