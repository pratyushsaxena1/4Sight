# 4Sight UI rework — design

## Goal
Make the app look professional and intentional instead of basic, without looking
templated or AI-generated. Add short copy describing what the app is. No em dashes
in any product copy.

## Direction: refined dark terminal
Evolve the existing dark theme into a fintech / trading-terminal look.

### Palette & type
- Background near-black `#0b0c0e`; elevated surface `#15171b`; subtle borders `#24272e`
  (replaces the stark white gridlines, the main "basic" tell).
- Text primary `#e8eaed`, muted `#8b9099`. Accent blue `#5b9dff` for focus, links,
  primary button. Green `#2ec96b` (Acquired) and red `#f0555f` (Disposed) reserved for
  A/D semantics only.
- Inter for UI text. JetBrains Mono (same Google Fonts pattern already in the file) for
  numeric data with tabular figures — the "terminal" cue.

### Layout
- Left-aligned `max-width: ~1080px` column instead of centering everything.
- Header: 4Sight wordmark + one-line descriptor + short line on what a Form 4 is.
- Search is the primary input+button group. Visualization / Analysis become a smaller
  secondary action row, not three equal giant buttons.

### Table
- No white gridlines. Distinct header, thin row separators, hover highlight, subtler zebra.
- Numeric columns right-aligned, mono. A/D shown as a colored badge (Acquired / Disposed).
- N/A caveat becomes a small muted footnote.

### Other pages
- Shared header/wordmark + back nav across all three pages.
- Analysis: style the `<pre>` into a readable report card.
- Visualization: dark-themed matplotlib chart.
- Responsiveness: replace fixed `%` widths with flex + max-width; stack on mobile.

## Files touched
- `static/css/indexStyle.css` — bulk of the work.
- `templates/index.html`, `visualization.html`, `analysis.html` — markup for header,
  badges, classes.
- `static/py/graphs.py` `generate_stock_plot` — dark chart theme.
No route/logic changes.
