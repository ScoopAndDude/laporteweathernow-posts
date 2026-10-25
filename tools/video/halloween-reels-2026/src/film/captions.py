"""Write the SRT captions and the YouTube chapter list from the timeline.

python3 captions.py OUTDIR
"""
import os
import re
import sys

import numpy as np

import shots as S

REPL = [
    ("seventeen eighty-five", "1785"), ("In eight thirty-five", "In 835"), ("seven hundreds", "700s"),
    ("fifteen hundreds", "1500s"), ("eighteen-forties", "1840s"), ("eighteen-hundreds", "1800s"),
    ("eighteen ninety-two", "1892"), ("eighteen ninety-four", "1894"), ("nineteen-hundreds", "1900s"),
    ("November third, nineteen twenty-seven", "November 3, 1927"), ("nineteen-thirties", "1930s"),
    ("nineteen thirty-eight", "1938"), ("nineteen forty-two", "1942"), ("nineteen forty-seven", "1947"),
    ("nineteen fifty-one", "1951"), ("nineteen fifty-two", "1952"), ("nineteen fifty", "1950"),
    ("nineteen sixty-five", "1965"), ("nineteen-sixties", "1960s"), ("nineteen seventy-four", "1974"),
    ("nineteen eighty-four", "1984"), ("nineteen-oh-eight", "1908"), ("October thirty-first", "October 31"),
    ("a three-hundred-million-dollar business", "a $300 million business"),
    ("thirteen and a half billion dollars", "$13.5 billion"), ("four point four billion dollars", "$4.4 billion"),
    ("four point one billion", "$4.1 billion"), ("five forty-four", "5:44"), ("about ten forty", "about 10:40"),
    ("two hundred boys", "200 boys"), ("La Porte Weather Now dot com", "laporteweathernow.com"),
]

MAXC = 42


def clean(text):
    t = text
    for a, b in REPL:
        t = t.replace(a, b)
    return t


def units(text, limit=80):
    """Split a paragraph into caption-sized pieces at sentence, then clause, then word boundaries."""
    parts = re.findall(r"[^.?!]+(?:\.\.\.|[.?!])\"?\s*|[^.?!]+$", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) <= limit:
            out.append(p)
            continue
        bits = re.split(r"(?<=,)\s+", p)
        cur = ""
        for b in bits:
            if len(cur) + len(b) + 1 > limit and cur:
                out.append(cur)
                cur = b
            else:
                cur = (cur + " " + b).strip()
        if cur:
            out.append(cur)
    final = []
    for u in out:
        while len(u) > limit:
            words = u.split(" ")
            # most balanced split into two pieces
            best = None
            for i in range(1, len(words)):
                a, b = " ".join(words[:i]), " ".join(words[i:])
                score = max(len(a), len(b))
                if best is None or score < best[0]:
                    best = (score, a, b)
            if len(best[1]) <= limit:
                final.append(best[1])
                u = best[2]
            else:
                cut = u.rfind(" ", 0, limit)
                final.append(u[:cut])
                u = u[cut + 1:]
        final.append(u)
    return final


def wrap(u):
    if len(u) <= MAXC:
        return u
    best = None
    for i, ch in enumerate(u):
        if ch == " ":
            a, b = u[:i], u[i + 1:]
            score = max(len(a), len(b))
            if best is None or score < best[0]:
                best = (score, a, b)
    return best[1] + "\n" + best[2] if best else u


def ts(t):
    t = max(0.0, t)
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t % 60
    return "%02d:%02d:%02d,%03d" % (h, m, int(s), int(round((s - int(s)) * 1000)) % 1000)


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    tl, shots, ovs, total = S.build()
    cues = []
    for q in tl.list:
        text = q["text"]
        us = units(text)
        pos = 0
        starts = []
        for u in us:
            i = text.find(u, pos)
            pos = i + len(u)
            starts.append(i)
        times = []
        for k, i in enumerate(starts):
            if k == 0:
                times.append(q["s"])
            else:
                times.append(tl.w(q["section"], q["para"], text[i:i + 12]))
        for k, u in enumerate(us):
            t0 = times[k]
            t1 = times[k + 1] - 0.05 if k + 1 < len(us) else q["e"] + 0.25
            cues.append([t0, max(t1, t0 + 0.9), wrap(clean(u))])
    # no overlaps
    for a, b in zip(cues, cues[1:]):
        if a[1] > b[0] - 0.02:
            a[1] = b[0] - 0.02
    with open(os.path.join(outdir, "the-dark-history-of-halloween.srt"), "w", encoding="utf-8") as f:
        for i, (t0, t1, txt) in enumerate(cues, 1):
            f.write("%d\n%s --> %s\n%s\n\n" % (i, ts(t0), ts(t1), txt))
    # chapters
    lines = ["0:00 Cold open"]
    for s in shots:
        if s.name.startswith("ch") and s.name[2:].isdigit():
            n = int(s.name[2:])
            t = int(s.t)
            lines.append("%d:%02d %d. %s" % (t // 60, t % 60, n, S.TITLES[n]))
    outro = [s for s in shots if s.name == "outro"][0]
    t = int(outro.t + 0.6)
    lines.append("%d:%02d Watch next" % (t // 60, t % 60))
    open(os.path.join(outdir, "chapters.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(len(cues), "captions; total %.1f s" % total)


if __name__ == "__main__":
    main(sys.argv[1])
