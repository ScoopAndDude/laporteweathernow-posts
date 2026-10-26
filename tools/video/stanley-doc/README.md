# Room 217: The True Story of the Real Shining Hotel (YouTube documentary)

A 16:9, 1920x1080 documentary about the Stanley Hotel in Estes Park, Colorado, for the La Porte Weather Now
YouTube channel (Oct. 2026; Scoop: "make a youtube documentary on the stanley hotel", "end with comment your
city or town and we will make a video on the haunted history"). About 11 minutes, the same narrator as the
Halloween shorts and the Belle Gunness documentary. Nothing here posts anything: the finished file goes to
Scoop, and he uploads it himself.

It is built with the Belle Gunness documentary's engine (tools/video/belle-doc on the belle-doc branch), with
a new script, new music cues (an original waltz) and drawn night scenes (a hallway, a dining room after
closing, a window on the mountains, a room door, a snowed-in hotel for the novel's Overlook) and the closing
"comment your city or town" card.

## What's here

| File | What it is |
|---|---|
| `script.py` -> `script.json` | Every narration line and the pictures shown with it (8 chapters, an opening and an epilogue). The hotel's own stories are called the hotel's, ghost stories are called what guests say, and where 1911 newspapers disagree the film says so. |
| `doc.py` | The renderer: stills (contact sheets), video segments per chapter, the finished mp4, captions (.srt), the YouTube description and `CREDITS.md`. |
| `music.py` | Music and sound effects, written in code (nothing for Content ID to match). |
| `voice.py`, `lines.json`, `voice/` | The narration (Kokoro-82M, voice af_heart), recorded by `.github/workflows/stanley-doc-voice.yml`. Pushing a change to `lines.json` re-records only the lines that changed. |
| `fetch.py`, `sources.json` | Picture search (GitHub Actions, `.github/workflows/stanley-doc-images.yml`): Wikimedia Commons (public domain, CC0 and CC BY only, no share-alike) and the Library of Congress (photos with no known restrictions; Chronicling America newspaper pages, 1909-1912). The pictures are zips on the `stanley-doc-images` pre-release; `images/manifest.json` has each one's source, license and credit. |
| `art/` | The channel logo for the closing card. |
| `thumb.py` | The 1280x720 thumbnail. |
| `youtube.json` | Title, description (with `{CHAPTERS}` and `{CREDITS}` filled in by `doc.py description`), tags. |
| `CREDITS.md` | Every picture in the film with its author, license and link (made by `doc.py credits`). |

## Making it

```
python3 tools/video/stanley-doc/script.py                    # script.json
python3 tools/video/stanley-doc/doc.py lines                 # lines.json for the voice job
python3 tools/video/stanley-doc/doc.py stills OUT [chapter]  # contact sheets to check the pictures
python3 tools/video/stanley-doc/doc.py final OUT             # the mp4 (segments are cached by content)
python3 tools/video/stanley-doc/doc.py srt OUT               # English captions
python3 tools/video/stanley-doc/doc.py description OUT       # YouTube description + details
python3 tools/video/stanley-doc/thumb.py OUT/thumbnail.jpg a
```

The pictures go in `images/` (unzip the pre-release zips there). Python needs numpy, pillow, opencv-python,
scipy and soundfile; ffmpeg does the encoding.

## Rules the film follows

- Real pictures, credited: public domain or CC BY only (no share-alike), on screen and in the description.
  No stock footage and no AI pictures. Drawn scenes (maps, cards, the door) are said to be drawn.
- Quotes are only what the sources print. Stephen King's night at the Stanley is told the way he told it.
- Legends are called legends: none of the ghost stories is presented as proven.
- The closing card leaves the lower part of the frame quiet for YouTube's end-screen buttons (the last 20
  seconds).
