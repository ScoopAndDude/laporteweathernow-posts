# America After Dark, Oct. 2026

Three reels in the La Porte After Dark look, series name "AMERICA AFTER DARK" (`EndCard(..., series=...)` in
`src/film/reel_afterdark.py`; the earlier reels keep the default). Narration: `src/film/afterdark_us_vo.py`; reels:
`src/film/reel_afterdark_us.py`; `python3 afterdark_us_vo.py` then `python3 reel_afterdark_us.py wh_lincoln|eastern_state|stanley video`.
Photos (all public domain, verified on Wikimedia Commons) are in `src/america_images/` with their manifest entries;
copy them into the workspace's `belle_src/images/` and append the manifest. `src/film/run_us.py` is the Windows runner
(copies instead of symlinking, repoints the two Linux fonts hard-coded in shorts.py: GFS Baskerville, DejaVu Sans Mono Bold).

| Video | Length | Loudness / true peak |
|---|---|---|
| `out/white-house-lincolns-ghost.mp4` | 38.8 s | -13.9 LUFS / -2.5 dBFS (limiter added after render) |
| `out/eastern-state-penitentiary-philadelphia.mp4` | 39.3 s | -13.9 LUFS / -1.7 dBFS |
| `out/the-stanley-hotel-estes-park.mp4` | 37.8 s | -13.9 LUFS / -1.9 dBFS |

Sources: Wikipedia ("Lincoln's ghost", "Lincoln Bedroom", "Wilhelmina of the Netherlands", "Eastern State Penitentiary",
"Al Capone", "The Stanley Hotel"); White House Historical Association (origin of the Lincoln ghost story, ghost-stories
backgrounder, Q&A); easternstate.org (history page, audio-tour transcript, FAQ); stanleyhotel.com (Room 217, Elizabeth's
Spirited Grand King, The Stanley). Every sighting is worded reported / said to / legend. Narration is an AI voice.

Single-source details: Truman family knocks and "Lincoln's day it was his office" (Wikipedia), King's one night in
1974 and the 1911 explosion details, including the Wilson/Lambert name conflict (Wikipedia, citing 1911 papers).
