"""long_story.py <new-slug> '<json>'  -> stories/<new-slug>.json

Stitches several finished storyboards into one longer video (the weekly long video).
No new facts: every line comes from storyboards that were already fact-checked; the only new
narration is the opening line, which must only repeat things the stories themselves say.

json: {"title": "...", "hook": "opening line", "hook_title": "3 STORIES", "label": "LAPORTE COUNTY, INDIANA",
       "hook_src": "paint/<slug>/p1.jpg", "stories": ["<slug>-painted", ...], "music": {"seed": 141, "prog": 6}}
Then: reel_story.py stories/<new-slug>.json vo | stills | video   (one render at a time).
"""
import json, sys
F = '/root/afterdark/film'
slug = sys.argv[1]; o = json.loads(sys.argv[2])
out = {"slug": slug, "title": o["title"], "series": "LA PORTE AFTER DARK", "music": o.get("music", {"seed": 141, "prog": 6}),
       "say": [], "sources": [], "long": True, "made_from": o["stories"], "beats": []}
out["beats"].append({
    "text": o["hook"], "pause": 0.6,
    "scene": {"kind": "paint", "src": o["hook_src"], "move": "in", "amount": 0.10, "dim": 0.8},
    "label": o.get("label", ""), "title": {"text": o.get("hook_title", ""), "size": 110, "style": "red"},
    "credit": "Pictures: AI-generated (Canva)"})
ai = False
for k, s in enumerate(o["stories"]):
    d = json.load(open('%s/stories/%s.json' % (F, s)))
    ai = ai or d.get("ai_pictures", False)
    for r in d.get("say", []):
        if r not in out["say"]: out["say"].append(r)
    out["sources"] += d.get("sources", [])
    last = k == len(o["stories"]) - 1
    for b in d["beats"]:
        if b.get("end") and not last: continue
        out["beats"].append(b)
out["ai_pictures"] = ai
json.dump(out, open('%s/stories/%s.json' % (F, slug), 'w'), indent=1)
print('ok', len(out["beats"]), 'beats from', len(o["stories"]), 'stories')
