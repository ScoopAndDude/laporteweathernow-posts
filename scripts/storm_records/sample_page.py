#!/usr/bin/env python3
"""Sample Hard Hat Weather storm record page (artifact) from one record JSON made by the storm-records test.

  python3 make_page.py RECORD.json SUMMARY.json OUT.html
"""
import datetime as dt
import html
import json
import sys
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
e = html.escape


def t(s):
    return dt.datetime.fromisoformat(s).astimezone(CT)


def hr(d):
    if d.hour == 0:
        return "midnight"
    if d.hour == 12:
        return "noon"
    return f"{d.hour % 12} {'AM' if d.hour < 12 else 'PM'}"


def when(s):
    d = t(s)
    if d.hour == 0:  # midnight belongs to the night before: "Fri midnight"
        return f"{d - dt.timedelta(minutes=1):%a} midnight"
    return f"{d:%a} {hr(d)}"


def chart(rec):
    """Inline SVG: hourly snow bars and the running total, with the plow amount line. One inch scale for both."""
    rows = [h for h in rec["hours"] if t(rec["start"]) < t(h["t"]) <= t(rec["end"])]
    n = len(rows)
    W, H = 480, 280
    L, R, T, B = 40, 12, 22, 46
    top = max(rec["snow_total_in"], rec["plow_at"]) * 1.12
    top = max(2, (int(top) + 1))
    x = lambda i: L + (W - L - R) * (i + 0.5) / n  # noqa: E731
    y = lambda v: T + (H - T - B) * (1 - v / top)  # noqa: E731
    bw = (W - L - R) / n * 0.62
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Snow by the hour and running total" class="chart">']
    for v in range(0, top + 1, 2 if top > 6 else 1):
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                     f'<text x="{L - 8}" y="{y(v) + 4:.1f}" class="tick" text-anchor="end">{v}</text>')
    parts.append(f'<text x="{L - 8}" y="{T - 6}" class="tick" text-anchor="end">in.</text>')
    pa = rec["plow_at"]
    parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y(pa):.1f}" y2="{y(pa):.1f}" class="plow"/>'
                 f'<text x="{W - R}" y="{y(pa) - 6:.1f}" class="plowlab" text-anchor="end">Plow amount, {pa:g} in.</text>')
    for i, h in enumerate(rows):
        v = h["snow_in"]
        if v > 0:
            parts.append(f'<rect x="{x(i) - bw / 2:.1f}" y="{y(v):.1f}" width="{bw:.1f}" height="{y(0) - y(v):.1f}" rx="2" class="bar"/>')
        if i % 2 == 0 or n <= 8:
            parts.append(f'<text x="{x(i):.1f}" y="{H - B + 18}" class="tick" text-anchor="middle">{hr(t(h["t"]))}</text>')
    pts = " ".join(f"{x(i):.1f},{y(h['cum_in']):.1f}" for i, h in enumerate(rows))
    parts.append(f'<polyline points="{pts}" class="cum"/>')
    last = rows[-1]
    parts.append(f'<circle cx="{x(n - 1):.1f}" cy="{y(last["cum_in"]):.1f}" r="4" class="dot"/>'
                 f'<text x="{x(n - 1) - 8:.1f}" y="{y(last["cum_in"]) - 10:.1f}" class="endlab" text-anchor="end">{last["cum_in"]:.1f} in. total</text>')
    if rec["plow_reached"]:
        k = next(i for i, h in enumerate(rows) if h["t"] == rec["plow_reached"])
        parts.append(f'<circle cx="{x(k):.1f}" cy="{y(rows[k]["cum_in"]):.1f}" r="4" class="dotplow"/>')
    parts.append(f'<text x="{(L + W - R) / 2:.1f}" y="{H - 4}" class="tick" text-anchor="middle">Hour ending</text></svg>')
    return "".join(parts), rows


def main(rec_p, sum_p, out_p):
    rec = json.load(open(rec_p))
    s = json.load(open(sum_p))
    svg, rows = chart(rec)
    coco = s["checks"]["snow_vs_cocorahs_24h"]
    lsr = s["checks"]["snow_vs_storm_reports"]
    lot, storm = rec["lot"], rec["storm"]
    facts = []
    facts.append(("Snow fell", f"{when(rec['start'])} to {when(rec['end'])}"))
    facts.append((f"Plow amount ({rec['plow_at']:g} in.)", f"reached around {when(rec['plow_reached'])}" if rec["plow_reached"] else "not reached"))
    if rec["heaviest"]:
        facts.append(("Heaviest hour", f"about {rec['heaviest']['in']:.1f} in. in the hour ending {when(rec['heaviest']['t'])}"))
    facts.append(("Ice", f"about {rec['ice_in']:.2f} in. of freezing rain" if rec["ice_in"] >= 0.01 else "no freezing rain or sleet reported"))
    facts.append(("Temperature", f"{rec['low_f']:.0f} to {rec['high_f']:.0f}&deg;F during the snow"))
    if rec["refreeze"]:
        facts.append(("Refreeze", f"above freezing from {when(rec['melt'])}, back below 32&deg;F around {when(rec['refreeze'])}"))
    elif rec["after_high_f"] is not None and rec["after_high_f"] <= 32:
        facts.append(("After the snow", f"stayed below freezing for the next 18 hours (high {rec['after_high_f']:.0f}&deg;F), so no melting and refreezing"))
    dl = "".join(f"<div class=fact><dt>{a}</dt><dd>{b}</dd></div>" for a, b in facts)
    near = "".join(f"<li><span class=num>{n['inches']:.1f} in.</span> at {e(n['place'])}, {n['miles']:.1f} mi away <span class=muted>({e(n['what'])})</span></li>"
                   for n in rec["nearby"][:4]) or "<li class=muted>No measured reports within 6 miles.</li>"
    trs = []
    for h in rows:
        temp = "" if h["temp_f"] is None else f"{h['temp_f']:.0f}&deg;"
        trs.append(f"<tr><td>{e(when(h['t']))}</td><td class=num>{h['snow_in']:.1f}</td><td class=num>{h['cum_in']:.1f}</td>"
                   f"<td>{e(h['type'] or '-')}</td><td class=num>{temp}</td></tr>")
    sd = t(rec["start"])
    page = f"""<title>Hard Hat Storm Record</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Barlow:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap">
<style>
/* Layout: one column, like the email a plow customer gets the morning after a storm: total first, then facts, nearby measurements, the hour-by-hour chart and table, sources. */
:root {{
  --bg: #EDF1F5; --surface: #FFFFFF; --ink: #15202B; --muted: #566472; --line: #D2DAE2;
  --accent: #C2410C; --snow: #2D69B0; --snow-soft: #D9E6F5; --plow: #9A3412;
  --display: "Barlow Condensed", "Arial Narrow", system-ui, sans-serif;
  --body: "Barlow", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #0D141B; --surface: #15202A; --ink: #E4EAF0; --muted: #9AA7B4; --line: #2A3745;
  --accent: #F2894F; --snow: #7EB0EE; --snow-soft: #1E3550; --plow: #F5A06E; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #0D141B; --surface: #15202A; --ink: #E4EAF0; --muted: #9AA7B4; --line: #2A3745;
  --accent: #F2894F; --snow: #7EB0EE; --snow-soft: #1E3550; --plow: #F5A06E; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--ink); font-family: var(--body); font-size: 16px; line-height: 1.45;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 20px 48px; }}
.wrap {{ max-width: 720px; margin: 0 auto; display: grid; gap: 14px; }}
.sample {{ display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: baseline; justify-content: space-between; color: var(--muted); font-size: .9rem; }}
.brand {{ font-family: var(--display); font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--accent); font-size: .95rem; }}
.card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px 18px; min-width: 0; }}
h1 {{ font-family: var(--display); font-weight: 700; font-size: 2rem; line-height: 1.05; margin: 0; text-wrap: balance; }}
h2 {{ font-family: var(--display); font-weight: 600; font-size: 1.15rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); margin: 0 0 8px; }}
.storm {{ color: var(--muted); margin: 4px 0 0; }}
.total {{ display: flex; align-items: baseline; gap: 10px; margin: 12px 0 2px; flex-wrap: wrap; }}
.total b {{ font-family: var(--display); font-size: 3.4rem; line-height: 1; font-weight: 700; }}
.total span {{ font-size: 1.1rem; color: var(--muted); }}
dl {{ margin: 12px 0 0; display: grid; gap: 8px; }}
.fact {{ display: grid; grid-template-columns: minmax(120px, 34%) 1fr; gap: 10px; padding-top: 8px; border-top: 1px solid var(--line); }}
dt {{ color: var(--muted); font-size: .92rem; }} dd {{ margin: 0; min-width: 0; }}
ul {{ margin: 0; padding-left: 18px; display: grid; gap: 6px; }}
.num {{ font-family: var(--mono); font-variant-numeric: tabular-nums; font-size: .95rem; }}
.muted {{ color: var(--muted); }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart .grid {{ stroke: var(--line); stroke-width: 1; }}
.chart .tick {{ fill: var(--muted); font: 500 13px var(--mono); }}
.chart .bar {{ fill: var(--snow); opacity: .85; }}
.chart .cum {{ fill: none; stroke: var(--ink); stroke-width: 2.2; stroke-linejoin: round; }}
.chart .dot {{ fill: var(--ink); }} .chart .dotplow {{ fill: var(--plow); stroke: var(--surface); stroke-width: 2; }}
.chart .plow {{ stroke: var(--plow); stroke-width: 1.5; stroke-dasharray: 5 4; }}
.chart .plowlab {{ fill: var(--plow); font: 600 14px var(--body); }}
.chart .endlab {{ fill: var(--ink); font: 600 14px var(--body); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 6px 16px; color: var(--muted); font-size: .85rem; margin-top: 6px; }}
.sw {{ display: inline-block; width: 12px; height: 12px; border-radius: 2px; vertical-align: -1px; margin-right: 6px; }}
.scroll {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: .88rem; }}
th, td {{ text-align: left; padding: 6px 5px; border-bottom: 1px solid var(--line); white-space: nowrap; }}
th {{ color: var(--muted); font-weight: 600; font-size: .85rem; }}
td.num, th.num {{ text-align: right; }} th.num {{ font-family: var(--body); font-size: .85rem; }}
.fine {{ color: var(--muted); font-size: .86rem; margin: 10px 0 0; max-width: 70ch; }}
.note {{ background: var(--snow-soft); border-radius: 8px; padding: 10px 12px; font-size: .92rem; }}
@media (max-width: 460px) {{ .fact {{ grid-template-columns: 1fr; gap: 2px; }} h1 {{ font-size: 1.7rem; }} .total b {{ font-size: 2.8rem; }} }}
</style>
<div class="wrap">
  <div class="sample"><span class="brand">Hard Hat Weather &middot; Storm record</span><span>Sample made from last winter's real data</span></div>
  <section class="card">
    <h1>{e(lot['label'])}</h1>
    <p class="storm">Snow of {e(storm['name'])}, the night of {sd:%A, %B} {sd.day}</p>
    <div class="total"><b>{rec['snow_total_in']:.1f} in.</b><span>of snow at this lot</span></div>
    <dl>{dl}</dl>
  </section>
  <section class="card">
    <h2>Measured nearby</h2>
    <ul>{near}</ul>
    <p class="fine">Reports from National Weather Service spotters and CoCoRaHS volunteer observers.</p>
  </section>
  <section class="card">
    <h2>Hour by hour</h2>
    {svg}
    <div class="legend"><span><i class="sw" style="background:var(--snow)"></i>Snow that hour</span><span><i class="sw" style="background:var(--ink)"></i>Running total</span><span><i class="sw" style="background:var(--plow)"></i>Plow amount</span></div>
    <div class="scroll" style="margin-top:12px"><table>
      <tr><th>Hour ending</th><th class="num">Snow (in.)</th><th class="num">Total</th><th>Type</th><th class="num">Temp</th></tr>
      {''.join(trs)}
    </table></div>
  </section>
  <section class="card note">
    In the live version, this record also lists the PLOW, SALT and WATCH calls your crew got before the storm, with the time each one went out, and it lands in your email the morning after.
  </section>
  <p class="fine">Snow at this lot: NOAA National Snowfall Analysis (NOHRSC), split by hour with NOAA MRMS radar at this spot and the snow reported at the {e(rec['station']['name'])} ({rec['station']['miles']:.0f} miles away), which also gives the type and temperature. Estimates from public NOAA data, not a certified report. Checked against {coco['n']} volunteer snow reports from last winter's five big storms around La Porte County: within 1 inch {round(100 * coco['within_1'])}% of the time and within 2 inches {round(100 * coco['within_2'])}%. The analysis uses many of those reports, so between them expect a bit more; against spotters' storm totals the typical difference was {lsr['median_abs_diff']:.1f} inches, and in narrow lake-effect bands it can miss by more. That's why the nearest measured reports are listed too.</p>
</div>
"""
    open(out_p, "w").write(page)
    print("wrote", out_p, len(page))


if __name__ == "__main__":
    main(*sys.argv[1:4])
