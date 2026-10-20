# Halloween fall fun video (Oct. 20, 2026)

A one-off 15.6-second vertical video (1080x1920, the Daily Video's format) for TikTok and YouTube Shorts.
Scoop asked for it on Oct. 20 ("make it festive for halloween") and approved posting it.

- `make.py` draws it: the Daily Video's fonts, logo and text helpers (`scripts/video_render.py`) on a
  night sky with a moon, bats and jack-o'-lanterns drawn in code. The music is written in code too
  (organ chords, a music-box arpeggio, a heartbeat bass and a theremin glide in D minor), so nothing in
  it is a recording, stock footage or an AI picture or sound. There's no voice, because the Daily
  Video's voice (Kokoro-82M) downloads its model from Hugging Face, which this session couldn't reach.
- What it says comes from the trick-or-treat page's fall fun list (`trick-or-treat.json`, checked Oct. 20)
  and the NWS forecast for La Porte checked Oct. 20 at 11:35 a.m. (Saturday 66°, Sunday 69°, mostly sunny;
  Friday night 41°, Saturday night 47°).
- `python3 tools/video/halloween-2026/make.py OUTDIR` makes it in about 40 seconds; add `stills` for one
  PNG per scene. Loudness is normalized to -14 LUFS like the Daily Video.

## Posted (through Buffer, Oct. 20, 2026, about 12:00 PM CDT)
- YouTube Short on LaPorteWeatherNow: https://www.youtube.com/watch?v=8KLAtAV4UBM (Travel & Events, public)
- TikTok @scoopanddude, with the same caption
- The video file is on this branch (`halloween-video`), which Buffer read it from; keep the branch so the
  link in Buffer's records keeps working.
