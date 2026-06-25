# Responsive Frontend Contract

City GO user interface must work without horizontal page scrolling or browser zoom at every viewport from 320 px upward.

## Global rules

- `viewport-fit=cover` is enabled in `frontend/index.html`.
- Safari text autosizing is fixed with `-webkit-text-size-adjust: 100%`.
- `html`, `body`, `#root`, application screens and page containers cannot exceed viewport width.
- Flex and grid children use `min-width: 0` so long titles, addresses and URLs wrap instead of expanding the page.
- Images, canvases and maps have `max-width: 100%`.
- Inputs use at least 16 px text on mobile to prevent iOS Safari focus zoom.
- Left, right, top and bottom safe-area insets are respected.
- Touch targets remain at least 44 px.

## Navigation

The mobile primary navigation is a horizontally scrollable flex row. It must not be forced into five shrinking columns. On wider phones all items fit; on narrow screens the row scrolls with momentum.

## Place detail

At 520 px and below:

- photo and panel are one column;
- hero media follows a stable aspect ratio;
- title and facts wrap within the panel;
- footer actions are one column and include bottom safe-area padding;
- landscape mode moves the footer into normal document flow.

## Required viewport matrix

| Width / device class | Portrait | Landscape |
|---|---:|---:|
| 320 px compact phone | required | required |
| 360 px Android / compact iPhone | required | required |
| 390 px current iPhone | required | required |
| 428 px iPhone 12 Pro Max class | required | required |
| 768 px tablet | required | required |
| 1024 px tablet/laptop | required | required |
| 1440 px desktop | required | optional |

## Safari checks

For each user-facing page verify:

1. page width equals visual viewport width;
2. no horizontal document scroll;
3. focusing search/select fields does not zoom the page;
4. navigation remains usable with five items;
5. long place names, addresses and URLs wrap;
6. sticky actions are not hidden behind the home indicator;
7. 125% and 150% system text do not overlap controls;
8. maps resize after orientation change;
9. Telegram WebView uses the same constraints.

## Regression test

`frontend/src/styles/responsiveLayout.test.ts` checks the CSS-level invariants. Visual viewport smoke tests should cover Home, Places, Place Detail and Route Builder whenever Playwright is available in CI.
