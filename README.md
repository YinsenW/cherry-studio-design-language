# Feishu PPT Skill — Lark Slides Template Library for AI Agents

AI-agent skill for building **Lark (Feishu) slides via the `lark-cli`**: a 51-page template library, brand design tokens, XML generation workflow, and automated layout review.

Built as a reusable SKILL.md so agents can produce polished, on-brand presentations quickly — pick a template, swap content, lint, publish.

## What's inside

```
.
├── SKILL.md                 # Design spec + template workflow + CLI commands + troubleshooting
├── templates/
│   ├── INDEX.md             # 51-page scene index (per page: use case / structure / replace list)
│   └── slide01.xml ~ slide51.xml  # 960×540 Lark Slides XML templates
├── assets/
│   ├── cherry-logo.png      # Example logo asset (1024×1024 transparent PNG)
│   └── product-placeholder.png  # Product screenshot placeholder
└── scripts/
    └── review_layout.py     # Automated layout check (overlap / overflow / out-of-bounds)
```

## Template coverage

| Category | Pages | Range |
|----------|-------|-------|
| Cover / transition / closing | 7 | P1-P6, P51 |
| TOC / navigation | 3 | P7-P9 |
| Text / argumentation | 8 | P10-P17 |
| Data / charts | 8 | P18-P25 |
| Flow / architecture | 7 | P26-P32 |
| Product / solution | 6 | P33-P38 |
| Planning / org | 6 | P39-P44 |
| Ecosystem / community | 6 | P45-P50 |

## Quick start (agent view)

1. Read `templates/INDEX.md`, pick a template by content type
2. Copy `slideXX.xml` + `assets/*.png` into a work dir
3. Replace sample content per the INDEX "replace" checklist (templates are a starting point — adjust layout/density to fit content, keep the brand tokens)
4. Lint: `python3 scripts/review_layout.py --input slide.xml`
5. Publish via `lark-cli slides +create / +add-slide`

## Design tokens

- White canvas `#FFFFFF` + bold black headings `#171717` + white cards with thin border `#D6D6D2`
- Coral red `#FF5A5F` as the single brand accent (logo #FF5757)
- Black button = the only CTA; restrained accent lines (pink/cyan/purple/blue/green/yellow)
- 17 anti-patterns (no blue-purple gradients / no coral-red fills / no heavy shadows-glassmorphism...)
- Exact palette & font sizes: see SKILL.md (template values are authoritative)

## Dependencies

- [larksuite/cli](https://github.com/larksuite/cli) (Lark Slides XML operations)
- Official `xml_lint.py` (inside the lark-slides skill) for XML validation

## License

- **Code, templates, and scripts**: MIT © 2026
- **Brand assets** (e.g. `assets/cherry-logo.png`): brand/logo assets are **not** covered by the MIT license — they are the property of their respective owners and included only as examples. Replace them with your own assets for production use.
