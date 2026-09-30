# laporteweathernow-posts
Daily Scoop posts for laporteweathernow.com. Every post and edit is saved here with its time.

- `scoop-posts.json`: the Daily Scoop posts, newest first (laporteweathernow.com/daily-scoop).
- `nws-snapshot.json`: the official NWS, SPC and WPC weather each morning's post is written from, saved by the "NWS weather snapshot" job (clock times already in La Porte's Central time).
- `scorecard.json`: every Scoop forecast graded against the La Porte airport (same rules as the Track Record page), saved with the snapshot. The homepage's "How we've done" line reads it.
- `health.json`: the daily site health check (pages, files, version stamps, data freshness, on-time Scoops, failed jobs), saved by the "Site health check" job.
- `markets-data.json`: BLS jobs and prices for laporteweathernow.com/markets, saved twice a day by the "Markets numbers from BLS" job.
- `world-watch.json`: El Niño status and climate facts for laporteweathernow.com/disasters, updated weekly.
- Branch `live`, file `home.json`: La Porte's latest NWS reading and forecast, replaced every hour by the "Homepage weather copy" job. The homepage shows it (with its time) when NWS is slow or down.
