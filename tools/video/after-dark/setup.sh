#!/bin/bash
# Rebuild the La Porte After Dark workspace in a fresh cloud session (nothing else needed from earlier sessions).
#
#   bash tools/video/after-dark/setup.sh [WORK_DIR]        default WORK_DIR: $HOME/afterdark
#
# Afterwards:  cd WORK_DIR/film && python3 reel_story.py stories/<slug>.json vo|stills|video|check
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:-$HOME/afterdark}"
mkdir -p "$WORK" "$WORK/models" "$WORK/shorts/out" "$WORK/doc" "$WORK/belle_src/images"
rm -rf "$WORK/film"
cp -r "$HERE/src/film" "$WORK/film"
cp -r "$HERE/src/doc/." "$WORK/doc/"
cp "$HERE/src/belle_src/"*.py "$HERE/src/belle_src/"*.json "$WORK/belle_src/"

python3 - <<'PY' || pip install --quiet --break-system-packages "kokoro-onnx==0.6.1" skia-python opencv-python-headless soundfile scipy numpy pillow
import importlib
for m in ("kokoro_onnx", "skia", "cv2", "soundfile", "scipy", "numpy", "PIL"):
    importlib.import_module(m)
PY

for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  if [ ! -s "$WORK/models/$f" ]; then
    curl -sSL --retry 3 -o "$WORK/models/$f" \
      "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
  fi
done
command -v ffmpeg >/dev/null || { echo "ffmpeg is missing (apt-get install -y ffmpeg)"; exit 1; }
cd "$WORK/film" && python3 -c "import reel_story, story_kit, story_cards" && echo "workspace ready: $WORK"
