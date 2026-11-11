# Snow Help promo shorts (Nov. 11, 2026)

Three vertical shorts (1080 x 1920) promoting laporteweathernow.com/snow-help: a bright daytime look (not the
After Dark night scenes), the real site shown on a phone, the series' computer voice, and a card saying Scoop
is volunteering to shovel too. Finished videos are in `out/`.

To remake them: set up the After Dark workspace (`tools/video/after-dark/setup.sh` on the `after-dark` branch,
for the voice and fonts), run `shoot.py` for fresh phone screenshots of the site, then
`python3 promo.py stills` and `python3 promo.py video`. Paths at the top of both scripts assume
`/home/claude/afterdark`, `/home/claude/promo` and a checkout of the website repository.
