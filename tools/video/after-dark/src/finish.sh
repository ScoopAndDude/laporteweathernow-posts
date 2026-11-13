#!/bin/bash
# finish.sh <slug>: check the painted render, tame the peak if needed, copy into the repo as out/painted/<slug>.mp4
set -e
slug=$1; S=$slug-painted; O=/root/afterdark/shorts/out; R=/home/claude/laporteweathernow-posts/tools/video/after-dark
cd /root/afterdark/film
if python3 reel_story.py stories/$S.json check 2>&1 | grep -q "true peak"; then
  ffmpeg -v error -y -i $O/$S.mp4 -c:v copy -af "volume=-1.2dB" -c:a aac -b:a 192k $O/_t.mp4 && mv $O/_t.mp4 $O/$S.mp4
fi
python3 reel_story.py stories/$S.json check 2>&1 | tail -2
n=$(ffmpeg -v error -i $O/$S.mp4 -f null - 2>&1 | wc -l); if [ "$n" != "0" ]; then echo "PROBLEM: video does not decode cleanly ($n errors); render it again on its own"; exit 1; fi
mkdir -p $R/out/painted $R/src/film/paint/$slug $R/src/film/stories
cp $O/$S.mp4 $R/out/painted/$slug.mp4
for f in paint/$slug/*.jpg; do ffmpeg -v error -y -i $f -vf scale=1080:1920 -q:v 3 $R/src/film/paint/$slug/$(basename $f); done
cp stories/$S.json $R/src/film/stories/ 2>/dev/null || true
ls -la $R/out/painted/$slug.mp4
