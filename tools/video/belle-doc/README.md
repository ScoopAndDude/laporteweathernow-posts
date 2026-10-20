# Belle Gunness: The Black Widow of La Porte (YouTube documentary)

A 16:9, 1920x1080 documentary for the La Porte Weather Now YouTube channel (Oct. 2026; Scoop: "lets make a whole
documentary on belle", "make it for youtube", 15 to 20 minutes, the same narrator as the Halloween shorts).
Nothing here posts anything: the finished file goes to Scoop to look at, and he uploads it himself.

## What's here

| File | What it is |
|---|---|
| `script.py` -> `script.json` | Every narration line and the pictures shown with it (14 chapters). Facts were checked against 1908 newspapers and later sources; disputed points are said as disputed. |
| `doc.py` | The renderer: stills (contact sheets), video segments per chapter, the finished mp4, captions (.srt), the YouTube description and `CREDITS.md`. |
| `music.py` | Music and sound effects, written in code (nothing for Content ID to match). |
| `voice.py`, `lines.json`, `voice/` | The narration (Kokoro-82M, voice af_heart, as in the shorts), recorded by `.github/workflows/belle-doc-voice.yml`. Pushing a change to `lines.json` re-records only the lines that changed. |
| `fetch.py`, `sources.json`, `sources-extra.json` | Picture search (GitHub Actions, `.github/workflows/belle-doc-images.yml`): Wikimedia Commons (public domain, CC0 and CC BY only, no share-alike) and the Library of Congress (photos with no known restrictions; Chronicling America newspaper pages). The pictures themselves are zips on the `belle-doc-images` pre-release; `images/manifest.json` has each one's source, license and credit. |
| `thumb.py` | The 1280x720 thumbnail. |
| `youtube.json` | Title, description (with `{CHAPTERS}` and `{CREDITS}` filled in by `doc.py description`), tags. |
| `CREDITS.md` | Every picture in the film with its author, license and link (made by `doc.py credits`). |

## Making it

```
python3 tools/video/belle-doc/script.py                    # script.json
python3 tools/video/belle-doc/doc.py stills OUT [chapter]  # contact sheets to check the pictures
python3 tools/video/belle-doc/doc.py final OUT             # the mp4 (segments are cached by content)
python3 tools/video/belle-doc/doc.py srt OUT               # English captions
python3 tools/video/belle-doc/doc.py description OUT       # YouTube description + details
python3 tools/video/belle-doc/thumb.py OUT/thumbnail.jpg a
```

The pictures go in `images/` (unzip the pre-release zips there) and the shorts' pictures in
`../belle-2026/images/`. Python needs numpy, pillow, opencv-python, scipy and soundfile; ffmpeg does the encoding.

## Rules the film follows

- Real pictures only: 1908 photos, postcards and newspaper pages (public domain or CC BY, credited on screen and in
  the description). No stock footage and no AI pictures. No photos of remains.
- Quotes are only what the sources print, with who said or wrote them and where it was printed; a summary is
  called a summary. Legends are called legends.
- Uploads over 15 minutes need a phone-verified YouTube channel (youtube.com/verify).
