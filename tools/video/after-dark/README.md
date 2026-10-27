# La Porte After Dark (after-dark branch only)

Short vertical videos (1080 x 1920, 30 fps, -14 LUFS, 35 to 50 seconds) about the dark history and legends of
La Porte and the towns around it: jails, prisons, cemeteries, old houses, the dunes. They continue the "La Porte
After Dark" stories Scoop posts on the La Porte Weather Now Facebook page, and each ends with "Comment your town, and
it could be next."

A scheduled Claude task ("La Porte After Dark shorts (Tue & Fri)", 7:37 AM Central, first run Fri., Oct. 30, 2026)
makes one every Tuesday and Friday morning and schedules it for 6:30 PM, following [PLAYBOOK.md](PLAYBOOK.md):
topic from [queue.json](queue.json) or viewers' comments, research with two sources for every fact, an independent
fact-check, then YouTube, TikTok and X through Buffer. Scoop posts the Facebook version himself from the caption the
task sends to his phone. [log.md](log.md) lists what ran.

## How a short is made

Everything is drawn and synthesized, so there's nothing to license: the scenes are code (night skies, jails, cells,
prisons, dunes, lighthouses, main streets, cemeteries, houses, roads, woods, rooms), the narrator is the Kokoro
`af_heart` voice the other reels use, and the music and sound effects are synthesized.

```
bash setup.sh ~/afterdark                     # fresh workspace: code, fonts, packages, voice model
cd ~/afterdark/film
python3 reel_story.py stories/<slug>.json vo        # narration (prints how names will be said)
python3 reel_story.py stories/<slug>.json stills    # contact sheet in ~/afterdark/shorts/out/
python3 reel_story.py stories/<slug>.json video     # <slug>.mp4, -cover.jpg, .srt
python3 reel_story.py stories/<slug>.json check     # loudness, length, narration vs. script, credits
python3 kit_sheet.py jail cell 'dunes:{"trees":true}'   # preview scene kinds
```

- `src/film/reel_story.py`: the engine. A storyboard (`src/film/stories/*.json`) lists beats; each beat is one
  paragraph of narration with its scene, labels, typed text, an optional card and its source credit.
- `src/film/story_kit.py`: the scene kinds and their options (listed at the top of the file).
- `src/film/story_cards.py`: year, quote, headline (real published words only), map and photo cards.
- `src/film/story_sound.py`: cell door, keys, drips, foghorn, train whistle and rumble.
- `src/film/data/region.json`: county lines (U.S. Census Bureau), Lake Michigan (Natural Earth) and town points
  for the map card.
- The rest of `src/film/` is the Halloween reels' code (halloween-reels branch) that the kit builds on, with the
  fonts and logos in `src/doc/` and the Belle series' shared look in `src/belle_src/`.

## Shorts

| Date | Short | Length | Posted |
|---|---|---|---|
| Oct. 27, 2026 | `crown-point-old-jail-dillinger`: Crown Point's "escape-proof" jail, Dillinger's 1934 escape, the voices visitors report | 43 s | Wed., Oct. 28, 6:30 PM (see log.md) |
