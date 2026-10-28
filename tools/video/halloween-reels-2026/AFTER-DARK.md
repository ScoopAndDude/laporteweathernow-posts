# La Porte After Dark, Oct. 2026 (Part 8, Part 7, the 1933 prison break)

Built with the method in `README.md` at commit 7599159: Pillow frames piped to ffmpeg, Kokoro-82M (`kokoro-onnx`,
`af_heart`, 1.02x, one sentence at a time), -14 LUFS. New scripts: `src/film/afterdark_vo.py` (narration) and
`src/film/reel_afterdark.py` (the three reels; drop both into `<root>/film/` of the rebuilt workspace and run
`python3 afterdark_vo.py`, then `python3 reel_afterdark.py belle8|belle7|break33 video`).
Needs `pip install kokoro-onnx soundfile pyloudnorm scipy opencv-python-headless skia-python` (plus `libegl1` on Debian/Ubuntu),
Kokoro's `kokoro-v1.0.onnx`/`voices-v1.0.bin`, Natural Earth + plotly Census county GeoJSON, and the belle-video images.

| Video | Length |
|---|---|
| `out/belle-gunness-part-8-the-woman-in-los-angeles.mp4` | 38.9 s |
| `out/belle-gunness-part-7-the-only-man-convicted.mp4` | 37.5 s |
| `out/ten-men-three-pistols-1933-prison-break.mp4` | 39.7 s |

All pictures are drawn or typeset (cards are our own lettering, not reproduced newspapers). Photos in Parts 7 and 8:
Belle Gunness portraits (public domain), farm photos by Steve Shook (CC BY 2.0), credited on screen. The 1933 reel has no photos.
Each end card says "Narration is an AI voice."
