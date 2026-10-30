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

## Oct. 25: five more (Scoop's OK, Oct. 25: "Yes, those times")

| Reel | Length | What it says |
|---|---|---|
| `posey-chapel-cemetery-the-bells` | 28.7 s | Posey Chapel Cemetery near Hesston: 1833, the 1972 arson, the preacher legend, the woman in white, the bouncing lights |
| `patton-cemetery-belle-gunness-victims` | 28.1 s | Patton Cemetery (1841): Jennie Olson and Andrew Helgelien are buried there; shadows, voices, sadness |
| `orr-lake-road-hangmans-road` | 25.0 s | "Hangman's Road": the Boyfriend's Death legend, told and never shown; no record it happened |
| `belle-gunness-part-6-the-dna-test` | 26.4 s | The 1908 burial near Chicago, the Nov. 2007 exhumation, the DNA test that couldn't be run, the April 2008 headstones |
| `halloween-trick-or-treat-forecast` | 26 s | Trick-or-treat night's NWS forecast, sunset and dark; remade from the newest forecast the morning it posts |

The three hauntings reels are drawn (Belle's portrait in the Patton one is public domain); their history and legends
are the hauntings page's case files. Part 6's sources: Forest Park Review (Dec. 4, 2007), Chicagoist (Feb. 12, 2008),
WBEZ (Apr. 28, 2008), Wikipedia. Post text: `posts-oct-25.json`; Facebook captions: `facebook-captions-oct-25.txt`.

In Buffer (the videos at commit 7599159), put in as the free plan's 10-per-channel queue freed up:

| Reel | When (CDT) | YouTube | TikTok | X |
|---|---|---|---|---|
| Posey Chapel Cemetery | Thu., Oct. 29, 12:15 PM | 6ade2985e4be8a4d86b64754 | 6ade29886887a2efc1130387 | 6ade298be4be8a4d86b6487e |
| Patton Cemetery | Thu., Oct. 29, 7 PM | 6adfe5dfc426e60252ceea65 | 6adfe5e3f266a5f7e103a85f | 6adfe5e6c426e60252ceec39 |
| Hangman's Road | Fri., Oct. 30, 7 PM | 6adfe5eac426e60252ceed42 | 6adfea145837b0fb9bf97e42 | 6adfe5ec14a7789a82f79b4a |
| Belle Gunness, Part 6 | Sat., Oct. 31, 12:15 PM | 6adfea0d0565644c947ff291 | 6adfff0da6170f32b17091eb | 6adfea10f266a5f7e104d7eb |

The trick-or-treat forecast was remade on Wed., Oct. 28 from that morning's NWS forecast (high 64, a 40% chance of
light showers by day, 20% Saturday night) and is in Buffer for Fri., Oct. 30, 7:30 AM (the video at commit ad40a78):
YouTube 6ae1fb4dbaa95856b5f2b331, TikTok 6ae1fb51f8ac381631f619bb, X 6ae1fb54e7fe9e2e3ebf199f.

Oct. 28, 2026: La Porte is said as one word, luh-PORT (Scoop: "Laporte is pronounced as one word not 2").
`src/film/reels_vo.py` now says it from sound symbols (`ləpˈɔɹt`, the weather radio's), and the six scheduled reels
that say it (Belle Part 5, Posey Chapel, Patton, Hangman's Road, the countdown, the trick-or-treat forecast) were
re-recorded; their 18 Buffer posts now use the videos at commit ad40a78. The scheduled task
still runs Fri., Oct. 30 at 5:30 AM: it refreshes the numbers from the newest forecast and updates these three posts
(edit_post with the new video), never adds new ones.

Later on Oct. 28 Scoop chose to spell it **LaPorte**, one word, on screen too. Belle Part 5 (commit c334cec) and the
other five reels (commit 2666267) show LaPorte in their labels and captions; the voice still says luh-PORT. Their 18
Buffer posts use those videos, and the post text and YouTube titles say LaPorte (names stay as published: "La Porte
After Dark", "La Porte County Herald-Dispatch", the News-Dispatch's "La Porte County's Top 10 Most Haunted").

Fri., Oct. 30, 5:30 AM: the trick-or-treat forecast was remade from the 5:02 AM CDT NWS snapshot: mostly cloudy, high
near 60, a 30% chance of a few showers by day; Saturday night a 20% (slight) chance before midnight, low 49. The
forecast discussion (2:58 AM EDT) says "plenty of dry time on Halloween" with isolated showers west of I-69, so the
reel and its posts now say that, and drop "mild" and "the better rain chances arrive Sunday" (Sunday is only 20% now).
No alerts for Saturday and no storm risk (the only statement was patchy dense fog Friday morning). The three Buffer
posts above were edited with the new video and text; still Fri., Oct. 30, 7:30 AM.

## Rebuilding the workspace

`src/` holds everything that isn't already in this repo: `src/film/*.py` (the drawing, sound and narration code; it
expects to sit in `<root>/film/`), `src/doc/fonts` and the logos (`<root>/doc/`), and `src/belle_src` (copies of the
belle-video branch's `shorts.py`, the halloween-video branch's `make.py` and main's `scripts/video_render.py`;
the pictures are the belle-video branch's `tools/video/belle-2026/images/`). The voice is Kokoro-82M (`kokoro-onnx`,
`models/kokoro-v1.0.onnx` and `models/voices-v1.0.bin` from that project's GitHub release), voice `af_heart` at
1.02x. Map data: Natural Earth (`<root>/dl/geo`, `dl/geo10`) and plotly's Census `counties.json`.

```
python3 film/reels_vo.py hwfc            # narration -> shorts/r_hwfc/
python3 film/reel_hwfc.py stills         # a contact sheet in shorts/out/
python3 film/reel_hwfc.py video          # the reel in shorts/out/
```

## Oct. 25: three trend reels

Made from what was trending that Sunday morning (vidIQ's trending Shorts were general entertainment, so these tie the
week's big searches to La Porte):

| Reel | Length | What it says |
|---|---|---|
| `hunters-moon-tonight-la-porte` | 25.2 s | Tonight's Hunter's Moon: moonrise 5:16 PM CDT (east-northeast) before the 5:51 sunset, full at 11:12 PM, NWS "partly cloudy"; Halloween moonrise 10:49 PM, so bring a flashlight |
| `indiana-favorite-halloween-candy-2026` | 27.9 s | CandyStore.com's 2026 rankings: Indiana NERDS Gummy Clusters; Illinois Sour Patch Kids, Michigan Starburst, Ohio Blow Pops (Kentucky Reese's Cups on the map); the U.S. top five |
| `clocks-fall-back-la-porte-sunsets` | 23.2 s | DST ends 2 AM Sun. Nov. 1; sunset 5:43 PM (Oct. 31) to 4:41 PM (Nov. 1), 4:17 by early December; sunrise 7:18 to 6:19 AM. It says "one week from today", so it's for Sun. Oct. 25 |

Moon and sun times: PyEphem for La Porte (41.6106 N, 86.7225 W), standard refraction, rounded to the minute (they
agree with Almanac.com's Hunter's Moon listing and sunrise-sunset.org's La Porte table to the rounding). It's not a
supermoon (368,900 km), so nothing says it is. Candy: CandyStore.com 2026 (projected sales, 18 years of data), as
reported by NBC (Oct. 8) and BroBible (Oct. 5). Everything is drawn; the candy is generic (no packaging, logos or
characters) and brand names appear only as text.

Script: `src/film/reel_trends.py` (`python3 film/reel_trends.py moon|candy|dst stills|video`), narration in
`reels_vo.py` (`moon`, `candy`, `dst`). Post text: `posts-trends-oct-25.json` (`src/film/reel_posts3.py`); Facebook
captions: `facebook-captions-trends-oct-25.txt`.

Posted through Buffer (Scoop's OKs, Oct. 25: "post the moon", then "Candy now, clocks at 2 PM"):

| Reel | When (CDT) | YouTube | TikTok | X |
|---|---|---|---|---|
| Hunter's Moon | Sun., Oct. 25, 11:38 AM (share-now) | 6ade30788b3d437ddc18bc37 | 6ade307cbd33ce99c37f03fb | 6ade30866887a2efc114df71 |
| Indiana's #1 Halloween candy | Sun., Oct. 25, 11:49 AM (share-now) | 6ade32f10b5343d070e062f2 | 6ade32f63d5b27036be1a083 | 6ade3300bd33ce99c37f857e |
| Clocks fall back | Sun., Oct. 25, 2 PM (scheduled) | 6ade3a810b5343d070e2962c | 6ade3a848b3d437ddc1b8f85 | 6ade3a873d5b27036be3c631 |

The clocks posts use the queue slot the 12:15 PM post freed and give it back at 2 PM, so the three slots tonight's
7:10 PM batch needs (Patton, Orr Lake, Part 6) are still there after the 4:30 and 7 PM posts go out.

## Oct. 25: three more La Porte legends

| Reel | Length | What it says |
|---|---|---|
| `orr-lake-road-the-doctors-lantern` | 28.5 s | Orr Lake Road's second legend: a doctor who kept his wife and daughter in barrels, and his lantern moving into the woods on full-moon nights with a hook-handed servant. Opens "Tonight's a full moon," so it's for Oct. 25 |
| `pine-lake-cemetery-buried-alive` | 32.1 s | The 1871 move of the old city cemetery, the woman said to be found upside down and twisted in her coffin, and the mass grave of about ten unknown men from Belle Gunness's farm |
| `la-porte-county-4-places-the-dead-dont-rest` | 33.1 s | A countdown: Orr Lake Road, Pine Lake, Patton and Posey Chapel, ending "Which one would you visit?" |

Sources: Pine Lake Cemetery from Ashley Hood's Haunted Cemeteries of Indiana (2020), via Jeff Mayes in the La Porte
County Herald-Dispatch (Oct. 22, 2020); the doctor legend and Patton's voices from Patricia Harrison's "La Porte
County's Top 10 Most Haunted," The News-Dispatch (Oct. 23, 2011). Everything is drawn; no bodies are shown. The list's
other spots (Gravity Hill's railroad legend, a drowned-boy story, an operating clinic) were left out on purpose.
Script: `src/film/reel_haunts2.py` (`python3 film/reel_haunts2.py pinelake|orr2|top4 stills|video`); post text
`posts-legends-oct-25.json` (`src/film/reel_posts4.py`); Facebook captions `facebook-captions-legends-oct-25.txt`.

In Buffer (Scoop's OK, Oct. 25: "Spread out"; the videos at commit c3a01fa). Orr Lake Road's doctor was planned for
Sun. Oct. 25 at 8:30 PM; that reminder came a day late, and Scoop moved it to Monday ("Post it at 8:30 tonight"):

| Reel | When (CDT) | YouTube | TikTok | X |
|---|---|---|---|---|
| Orr Lake Road's doctor | Mon., Oct. 26, 8:30 PM | 6adfe5c7c426e60252cee620 | 6adfe5cb3bff354cec674557 | 6adfe5cef266a5f7e1039e50 |
| Pine Lake Cemetery | Tue., Oct. 27, 8:30 PM | 6adfe5d3c426e60252cee8b4 | 6adfe5d73bff354cec67473d | 6adfe5dac426e60252cee987 |
| The countdown (4 places) | Sat., Oct. 31, 7 PM | 6adfff02457d00458c0f736f | (Tue., Oct. 27, after the 12:15 PM post frees a slot) | 6adfff05e322dad8011a435c |

## Oct. 26: Canton, Georgia

Scoop's request: "make me another spooky short on Canton GA, including the champlain house in fennin county." The
haunted house the Fannin County Chamber of Commerce lists there is the Chastain House, so that's the one in the reel.

| Reel | Length | What it says |
|---|---|---|
| `canton-georgia-baby-marie-and-the-chastain-house` | 37.1 s | Riverview Cemetery in Canton: a ghost-tour guide says a toddler pointed and said "baby," and named it "Marie"; a baby named Marie, who died in 1891, is buried there. Then the Chastain House in Fannin County (1850s; the Chastains' daughter Alice died of diphtheria at 10; in bad weather, a downstairs room held neighbors' dead); visitors say they hear children laughing and little footsteps. Ends "Comment your town, and it could be next." |

Sources: Rebecca Johnston, "Cemeteries offer haunting experience," Cherokee Tribune (Oct. 29, 2016), for the Riverview
story (the guide, Wilkie, wrote "The Haunting History of Canton"); the Fannin County Chamber's Historic Heritage Trail,
Lower Loop, stop 3, for the Chastain House's history ("reportedly haunted"); what visitors say is from a 2011 visitor's
blog post and Georgia Cabins For You's Blue Ridge ghost-tour page. Everything is drawn; no one is shown in the viewing
room. On screen: "The Chastain House: view it from the road."
Script: `src/film/reel_canton.py` (`python3 film/reel_canton.py stills|video`); narration `src/film/reels_vo.py canton`;
post text `posts-canton-oct-26.json`; Facebook caption `facebook-caption-canton.txt`. Not posted: waiting for Scoop's OK.

The countdown's YouTube text points to laporteweathernow.com/history (the site's Haunted La Porte County section)
instead of laporteweathernow.com/hauntings, which isn't on the site (Oct. 26).

## Oct. 28: power-outage prep, parts 1-3 ("Could your house last 3 days?")

Scoop's requests: "we should make some shorts on survining the upcoming blackout", "its called fortress", "make sure
you know the facts", "you can say your power company", then "post them all through chrome" and "now".

| Reel | Length | What it says |
|---|---|---|
| `outage-part-1-fortress-90-days` | 46.6 s | FORTRESS America as Fox News reported it (Pentagon documents call for major bases to run 90 days on their own); not a blackout notice for homes; your first hour of an outage. |
| `outage-part-2-staying-warm` | 47.5 s | Generators outside only, carbon monoxide, staying warm, Indiana 2-1-1 for a warming center. |
| `outage-part-3-food-and-water` | 41.7 s | Fridge about 4 hours, freezer 48/24, 40°F, when in doubt throw it out, water for 3 days, ask your pharmacist. |

Script `src/film/reel_blackout.py` (`python3 film/reel_blackout.py 1|2|3 stills|video`), drawings
`src/film/blackout_art.py`, narration `src/film/reels_vo.py bo1 bo2 bo3`; post text `posts-blackout.json`, Facebook
captions `facebook-captions-blackout.txt`, sources and fact-check notes `sources-blackout.txt`.

Pentagon is said PEN-tuh-gahn, one word (Scoop, Oct. 28: "its pronounced pent a gone all one word penta gon"). Left
alone, the voice said pen-TAG-un; `reels_vo.py` now swaps in the right sounds (`FIX`), and Part 1 was re-recorded and
re-rendered (commit c30230d). Only Part 1 says it.

Posted Oct. 28:
- YouTube (LaPorteWeatherNow): Part 1 https://youtube.com/shorts/jJupooE451A, Part 2
  https://youtube.com/shorts/PgmE1b0_jSQ, Part 3 https://youtube.com/shorts/mluCQ2bSRLU (Education; AI use disclosed
  for the computer voice).
- TikTok (@scoopanddude): 5:57, 5:59 and 6:01 PM, AI-generated label on.
- X, through Buffer's Share now (Claude in Chrome can't open x.com):
  https://x.com/2103134688416067584/status/2115580294937899018,
  https://x.com/2103134688416067584/status/2115580324260327605,
  https://x.com/2103134688416067584/status/2115580399237660794
- Facebook Page: Part 1 first went out at 5:44 PM (https://facebook.com/reel/2454929945031140), just before the Pentagon
  fix, so that copy had the old pronunciation. Scoop: "remake part 1 and post it" (7:01 PM): the fixed Part 1 is
  https://facebook.com/reel/4579080018972484 (7:04 PM), and the 5:44 copy was set to expired in Meta Business Suite
  (hidden from everyone but the Page's admins; not deleted). Part 2 https://facebook.com/reel/1809919187007193 and
  Part 3 https://facebook.com/reel/1673470677500357. All three have tags Local News and Community and are shared to
  Scoop's personal timeline.
