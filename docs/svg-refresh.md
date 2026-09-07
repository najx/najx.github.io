# SVG, navigation and SEO refresh

Review branch: `codex/svg-design-seo`. No merge or production deployment is part of this change.

## What changed

- Replaced all 29 repository bitmap assets (PNG, JPEG, WebP and ICO) with 24 original, editable SVGs. Six favicon variants are consolidated into one scalable mark. Existing certification badges and inline article diagrams are preserved.
- The replaced asset set goes from 12,487,629 bytes to 66,336 bytes (about 99.5% smaller). This compares asset files, not page-load times. Originals remain recoverable from Git history.
- New illustrations cover outages, quantum computing, security, engineering roles, twelve-factor applications, IPv4/IPv6, and multi-agent systems. They are explanatory drawings, not recreated photographs or purported screenshots. Captions/credits were updated accordingly.
- Refined the existing identity with a spacious article archive, readable typography, responsive navigation, light/dark palettes, excerpts, topic links and a collapsible article contents list.
- Search is accent-insensitive and works locally; all article links remain available without JavaScript. Added keyboard focus states, a skip link, scrollable tables/figures/code blocks and a news-ticker pause control.
- Consolidated document layouts and metadata: one H1 and canonical per page, descriptions, page language, article dates, JSON-LD, robots.txt, sitemap/feed links and SVG image dimensions/alternative text. Removed duplicate analytics initialization. Existing article URLs and the custom domain are preserved.
- Pull requests build and validate, but only a push to `main` can upload/deploy GitHub Pages. Review branches cannot deploy through this workflow.

## Asset mapping

Each former non-favicon bitmap keeps its directory and basename, with `.svg` replacing its extension. The six files under `assets/favicons/` are replaced by `favicon.svg`, referenced by the document head and web manifest. The obsolete Windows tile configuration was removed.

## Validation

With Ruby 3.2 and the locked Bundler dependencies installed:

```sh
bundle install
JEKYLL_ENV=production bundle exec jekyll build
python3 scripts/validate_site.py
node --check assets/js/main.js
node --check assets/js/search.js
node --check assets/js/ticker.js
```

The dependency-free validator checks the generated HTML, local links and anchors, metadata, JSON-LD, SVG XML/no embedded bitmaps, search completeness, feeds, manifest and custom domain. It also runs in CI. Gemfile and Gemfile.lock are unchanged.

Browser checks on 8 September 2026: six representative routes (home, search, topics, about, router privacy and the French request-journey article), at 390px and 1280px, in both themes: 24 views with no axe WCAG 2 A/AA or 2.1 AA violations and no page-level horizontal overflow. Search matches/no-match/accent handling, mobile Menu/Escape/navigation, theme persistence and contents links were exercised. All 24 SVGs were rendered and their text bounds checked; selected compositions were visually inspected. These automated checks are not a full accessibility certification or a ranking/performance guarantee.

## Review tradeoffs

- SVG-only assets follow the requested scope. Social networks do not consistently support SVG preview images, so the default sharing metadata uses text cards rather than advertising unsupported SVG thumbnails. Apple home-screen icons and legacy ICO-only browsers have no raster fallback. A compatible raster social/touch fallback would require relaxing the SVG-only requirement.
- Article prose and technical claims were not fact-checked or rewritten. Heading levels, image references and captions were adjusted; some Markdown line endings were normalized. Use Git's ignore-whitespace view when reviewing these files.
- SEO here means a sound technical foundation, not a promise of rankings. Content quality, indexing and real-user performance need assessment after an approved deployment.

References: [Google image formats and image SEO](https://developers.google.com/search/docs/appearance/google-images), [Article structured data](https://developers.google.com/search/docs/appearance/structured-data/article).
