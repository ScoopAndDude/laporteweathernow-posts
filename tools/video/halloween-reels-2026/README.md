# Halloween reels, Oct. 2026 (halloween-reels branch only)

Five vertical reels (1080x1920, 30 fps, -14 LUFS) made from the ideas Meta's Page Assistant suggested for
the La Porte Weather Now Facebook page. Each has a narrator, word-by-word captions and a "double-tap" ask
at the end. Scoop posts them on Facebook by hand; TikTok, YouTube and X go through Buffer.

| Reel | Length | What it says |
|---|---|---|
| `belle-gunness-part-3-the-newspaper-ad` | 28.6 s | Belle Gunness, Part 3: her "comely widow" ad ("Triflers need not apply"), Andrew Helgelien, January 1908 |
| `belle-gunness-part-4-was-the-woman-in-the-fire-belle` | 25.8 s | Part 4: a doctor said the body in the fire wasn't hers ("It is not that of Mrs. Gunness"); her dentist and the coroner said it was |
| `belle-gunness-part-5-los-angeles-1931` | 25.9 s | Part 5: Esther Carlson, the Los Angeles housekeeper two people from La Porte swore was Belle |
| `frankenstein-dracula-and-the-year-without-a-summer` | 29.9 s | Tambora (1815), the Year Without a Summer (1816), the Villa Diodati contest, Frankenstein and The Vampyre |
| `la-porte-weather-anomaly` | 27.1 s | This week's NWS forecast, then the "La Porte weather anomaly" (Changnon, 1968) and why it's still debated |

The weather reel was re-rendered on Sun., Oct. 25 with the NWS forecast for Mon.-Thu. (as of 9:17 AM CDT,
from `nws-snapshot.json` on main): 69, 68, 73, 72, a 20% shower chance Thursday, nights around 50. The
first cut (Oct. 22) showed Thu.-Sun., Oct. 22-25.

## Files

- `out/`: the five videos as posted, each with its cover frame.
- `posts.json`: TikTok, YouTube (title and description) and X text, with the photo credits and post times.
- `facebook-captions-oct-22.txt`, `facebook-caption-belle-part-5.txt`: the Facebook captions.
- `src/`: the scripts that drew them (PIL frames piped to ffmpeg). `reels_vo.py` is the narration (Kokoro
  `af_heart`, one sentence at a time so caption timing is exact); `reel_belle.py`, `reel_frank.py` and
  `reel_wx.py` draw the reels; `reels_common.py` holds the shared look and sound. They were run in the cloud
  workspace and need the belle-video branch's `tools/video/belle-2026/shorts.py`, the halloween-video branch's
  `make.py`, main's `scripts/video_render.py` and Natural Earth / Census map data.

## Pictures and credits

Every CC BY photo is credited on screen and in each post (YouTube descriptions link the license). No
share-alike pictures.

- Belle Gunness's portraits (`belle-07`, `belle-08`): public domain.
- Belle Gunness and her children (`belle-05`): Library of Congress, George Grantham Bain Collection, public domain.
- The farm, the hog pen, the farm after the fire, viewing the cellar, reviewing remains, the 1908 postcard
  and the multiview of case photos (`belle-farm-03`, `-07`, `-10`, `-13`, `-14`, `-15`, `belle-11`, `belle-14`):
  Steve Shook via Wikimedia Commons, CC BY 2.0.
- LaPorte Carriage Company, about 1912 (`laporte-11`): Steve Shook, CC BY 2.0. Hotel Rumely postcard
  (`laporte-09`): Tichnor Bros., public domain.
- The ad (Part 3) and the 1818/1819 title pages are re-set from their published text. Everything in the
  Frankenstein reel is drawn. Maps: Natural Earth; county lines, U.S. Census Bureau.

## Sources

- The ad, Helgelien, Dr. Long's "It is not that of Mrs. Gunness", the dental work and the coroner: Wikipedia's
  Belle Gunness article and Legends of America.
- Esther Carlson (August Lindstrom, 81, died Feb. 9, 1931; she died of TB before trial; two former La Porte
  residents identified her as Belle; the photo of three children): HistoryNet, Crime Library, Daily Herald.
- Weather: Stanley Changnon, "The La Porte Weather Anomaly: Fact or Fiction?" (Bulletin of the American
  Meteorological Society, 1968) and later papers that doubted it.

## Posted

Through Buffer on TikTok (@scoopanddude), YouTube (LaPorteWeatherNow) and X (@ScoopAndDude), with the
videos in `out/` at commit 7f805ce (Scoop's OK, Oct. 25, 2026: "Put the five new reels in Buffer for
YouTube, TikTok and X. Facebook stays by hand."). Buffer post IDs:

| Reel | When (CDT) | YouTube | TikTok | X |
|---|---|---|---|---|
| Weather anomaly | Sun., Oct. 25, 4:30 PM | 6ade202ce4be8a4d86b3547e | 6ade202fbd33ce99c37a85fc | 6ade20323d5b27036bdc1ee0 |
| Belle Gunness, Part 3 | Sun., Oct. 25, 7 PM | 6ade203b8b3d437ddc143207 | 6ade203f3d5b27036bdc2058 | 6ade20420b5343d070dafa5d |
| Belle Gunness, Part 4 | Mon., Oct. 26, 7 PM | 6ade20460b5343d070dafae8 | 6ade20498b3d437ddc1433f2 | 6ade204c6887a2efc1101ec6 |
| Frankenstein, Dracula and the Year Without a Summer | Tue., Oct. 27, 12:15 PM | 6ade20536887a2efc1102000 | 6ade20576887a2efc110206c | 6ade2059bd33ce99c37a8ac9 |
| Belle Gunness, Part 5 | Wed., Oct. 28, 7 PM | 6ade205e8b3d437ddc14364f | 6ade2062e4be8a4d86b35bc5 | 6ade20643d5b27036bdc2ab6 |

With the four posts already queued (rain chances, Hard Hat, the haunted flagman, lake effect), that's 9 of
the free plan's 10 scheduled posts per channel.

The narrator is a computer voice; the photos are real and the drawings are plainly drawings, so the posts
aren't labeled AI-generated (same as the earlier Belle shorts).
