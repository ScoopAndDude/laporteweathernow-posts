# The Daily Video

A short La Porte forecast video (about 20 to 30 seconds, vertical 1080x1920) made by itself every morning and posted as a Reel on the La Porte Weather Now Facebook Page and Instagram. Added Oct. 8, 2026 (Scoop: "Make it automatic").

## What happens each morning
1. **6:00 AM Central**, the Timer starts the "Daily video" job (`.github/workflows/daily-video.yml`; 6:45 is a second chance, and two GitHub schedules back it up). One video a day, made only between 5:45 and 9:30 AM.
2. `scripts/daily_video.py plan` asks the National Weather Service for La Porte's forecast, hour-by-hour forecast and La Porte County alerts, and picks the opening line by fixed rules (an alert first, then a freeze or frost, snow, the Storm Prediction Center's risk, heat, wind, likely rain, a big change from yesterday at the airport, a temperature far from NOAA's 1991-2020 normal, the weekend's best day, a nice day, or just the forecast).
3. `daily_video.py voice` records it with the weather radio's voice (Kokoro-82M, af_heart, free and open source).
4. `scripts/video_render.py` draws it: the opening line, today (with an hour-by-hour strip), tonight (with sunset and sunrise), the radar when there's rain or snow on it (NOAA's MRMS radar over a U.S. Census county map), the next three days, and the La Porte Weather Now card.
5. `scripts/video_post.py` posts it to Facebook and Instagram (once the Meta key is in; see below).
6. The video, its cover picture and `video.json` (what it said, the caption, where it was posted) go to the `video` branch. Only the newest is kept.

Watch today's video: `https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/video/video.json` names the file; the MP4 is next to it on the `video` branch.

## Rules (same as the radio and the Daily Scoop)
- Every number comes from NWS, NOAA or the La Porte airport. The pictures are drawn from the numbers. No AI pictures, no stock footage.
- No fear words and never a warning of our own. When there's an alert, the alert is the news, in NWS's words.
- **No video while a short-fused warning is in effect** for La Porte County (tornado, severe thunderstorm, flash flood, snow squall, extreme wind): a recorded video would be out of date within minutes.
- No video if NWS can't give both the forecast and the alerts.
- Right before posting it checks the alerts again: if one came or went since the video was made, it doesn't post. It posts only today's video, made in the last 2 hours, once per platform per day.

## Turning on the posting (one time, about 15 minutes, Scoop)
Meta's own Graph API is free for posting to your own Page and Instagram. It needs one key, saved as a GitHub secret. Never paste the key into a chat.

1. On a computer, go to **developers.facebook.com** and log in with the Facebook account that runs the La Porte Weather Now Page. If it asks, register as a developer (free).
2. **My Apps > Create app.** Name it `LPWN Daily Video`, contact email `laporteweathernow@gmail.com`. When it asks what the app does, pick the use cases for **managing a Page** and **Instagram content** (publishing). If it asks for a business portfolio, pick La Porte Weather Now.
3. In the app's settings, set the **Privacy Policy URL** to `https://laporteweathernow.com/privacy`. If the app has a Development/Live switch, set it to **Live** (it only posts to your own Page; no app review is needed for that).
4. **Tools > Graph API Explorer.** Pick the app. Under permissions add: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management`. Click **Generate Access Token** and allow it for the La Porte Weather Now Page and its Instagram.
5. Make it last: **Tools > Access Token Debugger**, paste that token, click **Extend Access Token**, and copy the new one. Back in the Graph API Explorer, paste the new token in the token box and run `me/accounts`. In the answer, copy the `access_token` next to "La Porte Weather Now" (a Page token made this way doesn't expire).
6. On GitHub: **ScoopAndDude/laporteweathernow-posts > Settings > Secrets and variables > Actions > New repository secret.** Name: `META_TOKEN`. Secret: paste the Page token. **Add secret.**
7. Check it: Actions > **Daily video** > Run workflow, mode `check`. It finds the Page and the Instagram account and posts nothing (or tell Claude the key is in and Claude runs it).

## YouTube Shorts (one time, about 5 minutes, Scoop)
YouTube's own API is free, and since 2026 uploads from new, unverified projects are no longer held as private. A small Google Apps Script in the business Google account uploads each morning's video to youtube.com/@laporteweathernow as a Short (6:00-9:30 AM, once a day, with the same alert checks as above). The code and the steps are at the top of `tools/video/youtube-upload.gs`: new project at script.google.com, paste, add the "YouTube Data API v3" service, run `setup`, and Allow.

TikTok and X aren't automatic: TikTok keeps posts from new apps private until TikTok audits the app, and X's posting API isn't free. Today's video is on the `video` branch each morning for posting by hand.

To stop posting on one platform, set it to `false` in `video/config.json` (the video is still made). To stop the video entirely, take the `daily-video.yml` line out of `scripts/timer.py` and disable the workflow in Actions.

## By hand
Actions > **Daily video** > Run workflow:
- `preview`: makes one now without posting; it goes to the `video-preview` branch. Tick "radar" to show the radar scene even on a dry morning (for checking it).
- `force`: makes one now and posts it (still once per platform per day).
- `check`: tests the Meta key (which Page and Instagram account it reaches); posts nothing.

## Files
- `config.json`: which platforms to post on, Meta's Graph API version, the voice speed.
- `fonts/`: Inter (SIL Open Font License, see `fonts/LICENSE-OFL.txt`).
- `logo-512.png`, `logo-mark.png`: the LPWN logo.
- `basemap-fallback.json`: a simple county map, used only if the Census Bureau's detailed map can't be downloaded.
- Tests: `python3 tools/video/test_plan.py` (no network needed).
