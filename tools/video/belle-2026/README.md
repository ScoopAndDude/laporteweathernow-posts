# Halloween shorts, 2026 (belle-video branch only)

Scoop asked for "a few different shorts and posts for retention rate", "really cool and spooky", with
"real images". Four short vertical videos (1080x1920, 30 fps), each with a narrator, word-by-word
captions, a scene change every few seconds and no end card, so they loop:

| Short | Length | What it says |
|---|---|---|
| `belle-1` | 18.5 s | Belle Gunness, part 1: the newspaper ads, the April 28, 1908 fire, "what they dug up next is in part two" |
| `belle-2` | 21.1 s | Part 2: was the woman in the fire really Belle? 11+ remains found; DNA couldn't settle it; the museum |
| `ghost-train` | 10.7 s | Last chance: the Hesston Ghost Train's final weekend, Sat. and Sun., noon to 5 |
| `hours` | 18.1 s | Trick-or-treat hours for every La Porte County town (from the posts repo's trick-or-treat.json) |

## Files

- `lines.json`: what the narrator says. Pushing a change runs `.github/workflows/belle-voice.yml`, which
  makes `voice/<id>.wav` and `voice/voice.json` (word timings) with the Kokoro-82M voice `af_heart`
  (`voice.py`; the voice can't be downloaded from the cloud workspace, so it runs on GitHub).
- `images.json` + `fetch_images.py`: pushing a change runs `.github/workflows/belle-images.yml`, which finds
  pictures on Wikimedia Commons and saves them in `images/` with `images/manifest.json` (title, page,
  license, artist). Only public domain, CC0 and CC BY pictures are used in the videos; no share-alike.
- `shorts.py`: draws every frame (PIL) and the sound (music, effects, the narrator on top), and pipes
  them to ffmpeg. The drawn version of each scene is kept (`SHORTS_DRAWN`); `SHORTS` uses the photos.
- `posts.json`: the captions, YouTube titles and descriptions, X text and photo credits.
- `out/`: the four videos as posted.

```
python3 tools/video/belle-2026/shorts.py /tmp/out --stills    # one frame per scene, plus the cover (0.4 s)
python3 tools/video/belle-2026/shorts.py /tmp/out             # all four videos (about 10 minutes)
python3 tools/video/belle-2026/shorts.py /tmp/out belle-1     # just one
```

Needs Python 3 with numpy and Pillow, ffmpeg, the repo's `scripts/video_render.py` (the Daily Video's
helpers) and the halloween-video branch's `tools/video/halloween-2026/make.py` (copied to this branch).

## The pictures and their credits

Every CC BY photo is credited on screen under the picture and in each post (YouTube descriptions link the
license).

- Belle Gunness's portrait (`belle-08`, the clean print): public domain.
- Belle Gunness and her children (`belle-05`): Library of Congress, George Grantham Bain Collection, public domain.
- The farm after the fire, the crowds at the farm and the Gunness farm, 1908 (`belle-farm-13`, `-15`, `-14`):
  Steve Shook, CC BY 2.0. Searchers at the farm (`belle-01`): Steve Shook, CC BY 4.0.
- Hesston's No. 242 (`hesston-02`, `-03`): Franklin Campbell, CC BY 2.0.
- Pumpkin patch (`pumpkins-04`, `-07`, `-08`): Rob Bertholf, CC BY 2.0.

Left out: share-alike pictures, and the 1908 photos of the remains being dug up.

## Posted (Scoop's OK, Oct. 20, 2026)

Through Buffer, on TikTok (@scoopanddude), YouTube (LaPorteWeatherNow) and X (@ScoopAndDude), with the
videos from `out/` at commit 6858362:

- Belle Gunness, Part 1: Oct. 20, 1:24 PM CDT (TikTok https://tiktok.com/@scoopanddude/video/7698817452683169038,
  YouTube https://www.youtube.com/watch?v=iWNOV9x96oQ, X https://x.com/2103134688416067584/status/2112610975459209400).
- Belle Gunness, Part 2: scheduled Wed., Oct. 21, 7 PM CDT (Buffer posts: TikTok 6ad7b1ea25c4beedd138e095,
  YouTube 6ad7b1eee519c58f0e118ebd, X 6ad7b1f0e519c58f0e118fba).
- Hesston Ghost Train: scheduled Thu., Oct. 22, 6 PM CDT (TikTok 6ad7b1f6ec26959816677e5b, YouTube
  6ad7b1fae519c58f0e119275, X 6ad7b1fc59e93798fafab6a7).
- Trick-or-treat hours: scheduled Fri., Oct. 23, 6 PM CDT (TikTok 6ad7b202adf3e386a7609592, YouTube
  6ad7b206adf3e386a7609668, X 6ad7b209ec26959816678a3d).

The narrator is a computer voice; every picture is a real photo, so the posts aren't labeled AI-generated.
These three scheduled sets filled the free Buffer plan's 10 scheduled posts per channel.
