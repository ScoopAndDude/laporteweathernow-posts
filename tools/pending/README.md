# Waiting for Scoop: turn on the daily rain totals (Oct. 18, 2026)

laporteweathernow.com/rain-totals reads `rain.json`, made by `scripts/rain_totals.py` (CoCoRaHS and NWS
co-op rain gauges in La Porte County, from the Iowa Environmental Mesonet). The first copy was saved
Oct. 18, 2026. To keep it updating every morning, two small changes need to be made by Scoop (the
agent's GitHub access can't add workflow files):

1. Move `tools/pending/rain-totals.yml` to `.github/workflows/rain-totals.yml`
   (GitHub: open the file, Edit, change the path at the top, Commit).
2. Apply `tools/pending/timer-rain-totals.patch` to `scripts/timer.py`: it adds one line to WINDOWS,
   `("rain-totals.yml", [("08:30", "08:44"), ("10:30", "10:44"), ("13:30", "13:44")], None),`
   and a line to the schedule at the top. Do this only after step 1, or the Timer would ask for a job
   that doesn't exist.

Until then the page still works; it shows when the reports were last checked and says when they're old.
