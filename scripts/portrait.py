"""
ASCII portrait for the profile README, typed out in colour from an illustration of me (portrait-source.jpg).

    python scripts/portrait.py [image]

Needs Pillow. Run by hand when the picture changes; writes portrait.svg at the same size as stats.svg.
"""
import sys
from collections import deque
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

from art import MONO, frame

ROOT = Path(__file__).resolve().parent.parent
W, H = 600, 760
RAMP = ' .:-=+*#%@'  # sparse to dense: on the dark card, brighter parts of the picture get more ink


def cells(image, cols, rows):
    """The picture cut to the card's shape and averaged into one colour per character cell."""
    im = Image.open(image).convert('RGB')
    w, h = im.size
    want = cols / (rows * 1.85)  # width over height of the grid, in pixels
    if w / h > want:
        cw = h * want
        im = im.crop((int((w - cw) / 2), 0, int((w + cw) / 2), h))
    else:
        im = im.crop((0, 0, w, int(w / want)))
    small = im.resize((cols, rows), Image.BOX)
    return [[small.getpixel((x, y)) for x in range(cols)] for y in range(rows)]


def background(grid, tolerance=34):
    """Cells joined to the edges that match the paper colour in the corner: left blank, so the card shows through."""
    rows, cols = len(grid), len(grid[0])
    paper = grid[0][0]
    near = lambda c: sum(abs(a - b) for a, b in zip(c, paper)) < tolerance
    seen = [[False] * cols for _ in range(rows)]
    todo = deque((y, x) for y in range(rows) for x in range(cols) if y in (0, rows - 1) or x in (0, cols - 1))
    while todo:
        y, x = todo.popleft()
        if seen[y][x] or not near(grid[y][x]):
            continue
        seen[y][x] = True
        todo.extend((y + dy, x + dx) for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= y + dy < rows and 0 <= x + dx < cols)
    return seen


def lift(c, floor=0.3):
    """Dark ink (hair, outlines) would vanish on the dark card, so every colour is raised to a minimum lightness."""
    top = max(c)
    if top >= 255 * floor:
        return c
    k = 255 * floor / max(top, 1)
    return tuple(min(255, int(v * k)) for v in c)


def hexc(c):
    # Quantised a little, so neighbouring characters share a colour and the runs merge
    return '#' + ''.join(f'{min(255, v // 12 * 12 + 6):02x}' for v in c)


def render(image):
    pad, top = 20, 44
    inner_w, inner_h = W - pad * 2, H - top - pad
    cols = 96
    cw = inner_w / cols
    lh = cw * 1.85  # monospace cells are close to twice as tall as they are wide
    rows = int(inner_h / lh)
    grid = cells(image, cols, rows)
    blank = background(grid)
    y0 = top + (inner_h - rows * lh) / 2
    out = frame(W, H, 'thotasuryatej@github: ~$ ./portrait.sh')
    out.insert(0, (
        '<style>.r{opacity:0;animation:on .25s linear both}@keyframes on{to{opacity:1}}'
        '@media (prefers-reduced-motion: reduce){.r{opacity:1!important;animation:none!important}}</style>'
    ))
    size = cw * 1.65
    for y, row in enumerate(grid):
        runs, last = [], None
        for x, c in enumerate(row):
            if blank[y][x]:
                ch, colour = ' ', None
            else:
                light = sum(c) / (3 * 255)
                # Never sparse inside the figure: the dark hair still reads as a mass, just a thinner one
                ch = RAMP[min(len(RAMP) - 1, 2 + round(light * (len(RAMP) - 3)))]
                colour = hexc(lift(c))
            if runs and (colour == last or ch == ' '):
                runs[-1][0] += ch
            else:
                runs.append([ch, colour])
                last = colour
        spans = ''.join(f'<tspan fill="{c}">{escape(t)}</tspan>' if c else escape(t) for t, c in runs)
        # Printed line by line, top to bottom
        out.append(f'<text class="r" xml:space="preserve" x="{pad}" y="{y0 + (y + 1) * lh - lh * 0.25:.1f}" '
                   f'font-size="{size:.2f}" textLength="{inner_w}" lengthAdjust="spacing" '
                   f'style="animation-delay:{y * 0.03:.2f}s">{spans}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{MONO}">'
            + ''.join(out) + '</svg>\n')


if __name__ == '__main__':
    image = sys.argv[1] if len(sys.argv) > 1 else ROOT / 'portrait-source.jpg'
    (ROOT / 'portrait.svg').write_text(render(image), encoding='utf-8')
    print('portrait.svg written')
