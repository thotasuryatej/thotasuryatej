"""
ASCII portrait for the profile README, typed out from my real photo (not generated).

    python scripts/portrait.py [photo]

Needs Pillow. Run by hand when the photo changes; writes portrait.svg at the same size as stats.svg.
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageEnhance, ImageOps

from art import AMBER, MONO, frame

ROOT = Path(__file__).resolve().parent.parent
W, H = 600, 760
RAMP = ' .:-=+*#%@'  # dark to bright, so on the dark card light reads as ink


def ascii_rows(photo, cols, rows):
    # The red channel only: the wall behind is lit blue, which would otherwise outshine the face
    im = Image.open(photo).convert('RGB').getchannel('R')
    # Head and shoulders, cut to the card's shape
    w, h = im.size
    cw, ch = w * 0.86, w * 0.86 * rows * 1.85 / cols
    im = im.crop((int((w - cw) / 2), int(h * 0.06), int((w + cw) / 2), int(h * 0.06 + min(ch, h * 0.94))))
    im = ImageOps.autocontrast(im, cutoff=1)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    im = im.resize((cols, rows), Image.LANCZOS)
    px = im.load()
    return [''.join(RAMP[px[x, y] * (len(RAMP) - 1) // 255] for x in range(cols)) for y in range(rows)]


def render(photo):
    pad, top = 20, 44
    inner_w, inner_h = W - pad * 2, H - top - pad
    cols = 96
    cw = inner_w / cols
    lh = cw * 1.85  # monospace cells are close to twice as tall as they are wide
    rows = int(inner_h / lh)
    lines = ascii_rows(photo, cols, rows)
    y0 = top + (inner_h - rows * lh) / 2
    out = frame(W, H, 'thotasuryatej@github: ~$ ./portrait.sh')
    out.insert(0, (
        '<style>.r{opacity:0;animation:on .25s linear both}@keyframes on{to{opacity:1}}'
        '@media (prefers-reduced-motion: reduce){.r{opacity:1!important;animation:none!important}}</style>'
    ))
    size = cw * 1.65
    for i, line in enumerate(lines):
        # Printed line by line, top to bottom
        out.append(f'<text class="r" xml:space="preserve" x="{pad}" y="{y0 + (i + 1) * lh - lh * 0.25:.1f}" fill="{AMBER}" '
                   f'font-size="{size:.2f}" textLength="{inner_w}" lengthAdjust="spacing" '
                   f'style="animation-delay:{i * 0.03:.2f}s">{escape(line)}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{MONO}">'
            + ''.join(out) + '</svg>\n')


if __name__ == '__main__':
    photo = sys.argv[1] if len(sys.argv) > 1 else ROOT / 'photo.webp'
    (ROOT / 'portrait.svg').write_text(render(photo), encoding='utf-8')
    print('portrait.svg written')
