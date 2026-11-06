# Etsy pins

Tall Pinterest pins (1000 x 1500) for the ScoopAndDude Etsy shop.

- `pins.json` lists each pin: slug, the date it's scheduled, Etsy listing id, color theme, the Etsy photo to use, and the label, headline and sub line printed on the pin.
- `render.py` draws the pins with the Inter fonts in `video/fonts`.
- The **Etsy pins** workflow (`.github/workflows/etsy-pins.yml`) runs whenever `pins.json` or `render.py` changes, or by hand from the Actions tab. It downloads the Etsy photos, renders the pins and commits them to `out/`.

Buffer posts point at `https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/<commit>/etsy-pins/out/<slug>.jpg`. Because each link names a commit, it keeps working even if the files change later. Don't rewrite this repo's history while pins are still scheduled.

To make more pins, add entries to `pins.json` (copy an existing one) and push. Themes: `dark` (prep, money, gag gifts), `rust`, `green`, `red`, `maroon`, `blue`, `lavender`, `sage`, `blush`.

Test the layout without internet: `python etsy-pins/render.py --offline` (gray placeholder photos).
