"""
Contribution graph and stats card for the profile README, drawn from this year's public contribution calendar.

    python scripts/art.py <github-user> [saved-calendar.html]

Reads https://github.com/users/<user>/contributions for 1 Jan to 31 Dec of the current year (public, no token),
saves the days so far to data/contributions.json
and writes contrib.svg and stats.svg. A saved copy of that page can be passed instead of fetching it. Standard library only. Every number on the card is counted from those days.
"""
import calendar
import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The portfolio's dark palette (suryatejpatel.in): warm board, amber trace, arc blue for what is live
BG_TOP, BG_BOTTOM = '#171512', '#0f0e0c'
PANEL, LINE = '#1c1a17', '#2f2b26'
TEXT, MUTED = '#eee8de', '#918a80'
AMBER, ARC, EMBER = '#f0be64', '#8cd4fa', '#de6e58'
LEVELS = ['#24211d', '#4f3a1d', '#86602a', '#c28c3c', '#f0be64']
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'


def fetch(user, year, saved=None):
    if saved:
        html = Path(saved).read_text(encoding='utf-8')
    else:
        url = f'https://github.com/users/{user}/contributions?from={year}-01-01&to={year}-12-31'
        req = urllib.request.Request(url, headers={'User-Agent': 'profile-art'})
        html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
    # Each day is a cell with its date, level and id; its count is in the tooltip that points at that id
    counts = {}
    for cell_id, text in re.findall(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>([^<]*)', html):
        m = re.match(r'\s*(\d[\d,]*) contributions?', text)
        counts[cell_id] = int(m.group(1).replace(',', '')) if m else 0
    days = []
    for attrs in re.findall(r'<td([^>]*ContributionCalendar-day[^>]*)>', html):
        get = lambda k: re.search(rf'\b{k}="([^"]*)"', attrs).group(1)
        days.append({'date': get('data-date'), 'level': int(get('data-level')), 'count': counts.get(get('id'), 0)})
    if not days:
        sys.exit('No contribution cells found: the page layout may have changed')
    return sorted(days, key=lambda d: d['date'])


def streaks(days):
    today = date.fromisoformat(days[-1]['date'])
    active = {d['date'] for d in days if d['count'] > 0}
    longest = run = 0
    for d in days:
        run = run + 1 if d['date'] in active else 0
        longest = max(longest, run)
    # Today still counts as part of a streak until it ends empty
    day = today if today.isoformat() in active else today - timedelta(days=1)
    current = 0
    while day.isoformat() in active:
        current += 1
        day -= timedelta(days=1)
    return current, longest


def frame(w, h, title):
    return [
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG_TOP}"/>'
        f'<stop offset="1" stop-color="{BG_BOTTOM}"/></linearGradient></defs>',
        f'<rect width="{w}" height="{h}" rx="12" fill="url(#bg)"/>',
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="none" stroke="{LINE}"/>',
        f'<line x1="0" y1="30" x2="{w}" y2="30" stroke="{LINE}"/>',
        f'<circle cx="20" cy="15" r="5" fill="{EMBER}"/><circle cx="36" cy="15" r="5" fill="{AMBER}"/>'
        f'<circle cx="52" cy="15" r="5" fill="{ARC}"/>',
        f'<text x="{w / 2}" y="19" fill="{MUTED}" font-size="12" text-anchor="middle">{title}</text>',
    ]


def heatmap(days, user, today):
    cell, gap, left, top = 13, 3, 46, 80
    first = date.fromisoformat(days[0]['date'])
    offset = (first.weekday() + 1) % 7  # weeks start on Sunday, as on GitHub
    weeks = (offset + len(days) + 6) // 7
    w = left + weeks * (cell + gap) + 24
    h = top + 7 * (cell + gap) + 44
    total = sum(d['count'] for d in days)
    year = days[0]['date'][:4]
    out = frame(w, h, f'{user}@github: ~$ ./contributions.sh')
    out.insert(0, (
        '<style>.c{transform-box:fill-box;transform-origin:center;opacity:0;animation:pop .5s ease-out both}'
        '@keyframes pop{0%{opacity:0;transform:scale(.2)}60%{opacity:1;transform:scale(1.12)}100%{opacity:1;transform:scale(1)}}'
        '@media (prefers-reduced-motion: reduce){.c{opacity:1!important;animation:none!important}}</style>'
    ))
    out.append(f'<text x="{left}" y="52" fill="{TEXT}" font-size="14" font-weight="700">{total:,} contributions'
               f'<tspan fill="{MUTED}" font-weight="400"> in {year}</tspan></text>')
    for row, name in ((1, 'Mon'), (3, 'Wed'), (5, 'Fri')):
        out.append(f'<text x="12" y="{top + row * (cell + gap) + 10}" fill="{MUTED}" font-size="10">{name}</text>')
    month, labelled = None, -9
    for i, d in enumerate(days):
        col, row = divmod(offset + i, 7)
        x, y = left + col * (cell + gap), top + row * (cell + gap)
        day = date.fromisoformat(d['date'])
        if day.month != month:
            # Labelled at the first week that starts in it; a label too close to the last one is left out
            if row == 0 and col - labelled >= 3 and col < weeks - 2:
                labelled = col
                out.append(f'<text x="{x}" y="{top - 6}" fill="{MUTED}" font-size="10">{calendar.month_abbr[day.month]}</text>')
            if row == 0:
                month = day.month
        # Days still to come are outlines only
        if d['date'] > today:
            out.append(f'<rect x="{x + 0.5}" y="{y + 0.5}" width="{cell - 1}" height="{cell - 1}" rx="3" fill="none" '
                       f'stroke="{LEVELS[0]}"/>')
            continue
        # Sweeps in column by column, with a ripple down each week
        delay = col * 0.035 + row * 0.03
        out.append(f'<rect class="c" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{LEVELS[d["level"]]}" '
                   f'style="animation-delay:{delay:.3f}s"><title>{d["count"]} on {d["date"]}</title></rect>')
    lx = w - 24 - 5 * (cell + gap) - 70
    ly = h - 22
    out.append(f'<text x="{lx}" y="{ly + 10}" fill="{MUTED}" font-size="10">Less</text>')
    for i, c in enumerate(LEVELS):
        out.append(f'<rect x="{lx + 30 + i * (cell + gap)}" y="{ly}" width="{cell}" height="{cell}" rx="3" fill="{c}"/>')
    out.append(f'<text x="{lx + 34 + 5 * (cell + gap)}" y="{ly + 10}" fill="{MUTED}" font-size="10">More</text>')
    return svg(w, h, out)


def stats(days, user, w=600, h=760):
    total = sum(d['count'] for d in days)
    current, longest = streaks(days)
    active = sum(1 for d in days if d['count'] > 0)
    best = max(days, key=lambda d: d['count'])
    weekday = Counter()
    for d in days:
        weekday[date.fromisoformat(d['date']).weekday()] += d['count']
    busiest = calendar.day_name[weekday.most_common(1)[0][0]] if total else '—'
    months = Counter()
    for d in days:
        months[d['date'][:7]] += d['count']
    months = sorted(months.items())[-12:]

    out = frame(w, h, f'{user}@github: ~$ ./stats.sh')
    out.insert(0, (
        '<style>.t{opacity:0;animation:in .5s ease-out both}'
        '@keyframes in{0%{opacity:0;transform:translateY(12px)}100%{opacity:1;transform:none}}'
        '.b{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .7s ease-out both}'
        '@keyframes grow{to{transform:scaleY(1)}}'
        '@media (prefers-reduced-motion: reduce){.t,.b{opacity:1!important;transform:none!important;animation:none!important}}</style>'
    ))
    pad, gap = 20, 16
    tile_w = (w - pad * 2 - gap) / 2

    def tile(i, label, value, unit, colour, y, height=120):
        x = pad + (i % 2) * (tile_w + gap)
        return (f'<g class="t" style="animation-delay:{i * 0.12:.2f}s">'
                f'<rect x="{x}" y="{y}" width="{tile_w}" height="{height}" rx="10" fill="{PANEL}" stroke="{LINE}"/>'
                f'<text x="{x + 20}" y="{y + 34}" fill="{MUTED}" font-size="15">$ {label}</text>'
                f'<text x="{x + 20}" y="{y + 88}" fill="{colour}" font-size="40" font-weight="700">{value}'
                f'<tspan fill="{MUTED}" font-size="17" font-weight="400"> {unit}</tspan></text></g>')

    plural = lambda n, one, many: one if n == 1 else many
    best_day = date.fromisoformat(best['date']).strftime('%d %b %Y') if best['count'] else 'none yet'
    rows = [
        ('current streak', current, plural(current, 'day', 'days'), ARC),
        ('longest streak', longest, plural(longest, 'day', 'days'), AMBER),
        (f'in {days[0]["date"][:4]}', f'{total:,}', plural(total, 'contribution', 'contributions'), TEXT),
        ('active days', active, f'of {len(days)}', TEXT),
    ]
    y0 = 50
    for i, (label, value, unit, colour) in enumerate(rows):
        out.append(tile(i, label, value, unit, colour, y0 + (i // 2) * (120 + gap)))

    y = y0 + 2 * (120 + gap)
    out.append(f'<g class="t" style="animation-delay:.5s">'
               f'<rect x="{pad}" y="{y}" width="{w - pad * 2}" height="78" rx="10" fill="{PANEL}" stroke="{LINE}"/>'
               f'<text x="{pad + 20}" y="{y + 32}" fill="{MUTED}" font-size="15">$ best day '
               f'<tspan fill="{TEXT}" font-weight="700">{best["count"]}</tspan> on <tspan fill="{TEXT}">{best_day}</tspan></text>'
               f'<text x="{pad + 20}" y="{y + 58}" fill="{MUTED}" font-size="15">$ busiest weekday '
               f'<tspan fill="{TEXT}" font-weight="700">{busiest}</tspan></text></g>')

    # Contributions per month, as bars on a trace
    y = y + 78 + gap
    ch = h - y - pad
    out.append(f'<g class="t" style="animation-delay:.62s"><rect x="{pad}" y="{y}" width="{w - pad * 2}" height="{ch}" '
               f'rx="10" fill="{PANEL}" stroke="{LINE}"/>'
               f'<text x="{pad + 20}" y="{y + 32}" fill="{MUTED}" font-size="15">$ per month</text></g>')
    peak = max((c for _, c in months), default=0) or 1
    base = y + ch - 34
    span = ch - 90
    bw = (w - pad * 2 - 40) / len(months)
    out.append(f'<line x1="{pad + 20}" y1="{base}" x2="{w - pad - 20}" y2="{base}" stroke="{LINE}"/>')
    for i, (ym, c) in enumerate(months):
        x = pad + 20 + i * bw
        bh = max(2, c / peak * span)
        colour = AMBER if c == peak and c else LEVELS[3]
        out.append(f'<rect class="b" x="{x + bw * 0.18:.1f}" y="{base - bh:.1f}" width="{bw * 0.64:.1f}" height="{bh:.1f}" '
                   f'rx="3" fill="{colour}" style="animation-delay:{0.75 + i * 0.05:.2f}s"><title>{c} in {ym}</title></rect>')
        if c:
            out.append(f'<text class="t" x="{x + bw / 2:.1f}" y="{base - bh - 6:.1f}" fill="{MUTED}" font-size="10" '
                       f'text-anchor="middle" style="animation-delay:{0.9 + i * 0.05:.2f}s">{c}</text>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{base + 18}" fill="{MUTED}" font-size="11" text-anchor="middle">'
                   f'{calendar.month_abbr[int(ym[5:])]}</text>')
    return svg(w, h, out)


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{MONO}">' + ''.join(body) + '</svg>\n')


if __name__ == '__main__':
    user = sys.argv[1] if len(sys.argv) > 1 else 'thotasuryatej'
    today = date.today()
    days = fetch(user, today.year, sys.argv[2] if len(sys.argv) > 2 else None)
    # The calendar runs to 31 Dec; the stats only count the days that have happened
    past = [d for d in days if d['date'] <= today.isoformat()]
    (ROOT / 'data').mkdir(exist_ok=True)
    (ROOT / 'data' / 'contributions.json').write_text(json.dumps(past, indent=1) + '\n')
    (ROOT / 'contrib.svg').write_text(heatmap(days, user, today.isoformat()), encoding='utf-8')
    (ROOT / 'stats.svg').write_text(stats(past, user), encoding='utf-8')
    print(f'{len(past)} days so far in {today.year}, {sum(d["count"] for d in past)} contributions')
