"""Post text for the five reels on TikTok, YouTube and X (Buffer), plus the X length check.

python3 reel_posts.py  ->  shorts/out/posts.json
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CC2 = "CC BY 2.0 (creativecommons.org/licenses/by/2.0)"
P = [
    {
        "file": "la-porte-weather-anomaly.mp4", "when": "2026-10-25T16:30:00-05:00", "cover_ms": 800,
        "youtube_title": "La Porte's weather anomaly: the Indiana town scientists studied",
        "body": "La Porte's weather was once so strange, scientists studied it ⛈️ This week: mostly dry and near 70 "
                "right up to Halloween, with nights around 50. But for decades in the mid-1900s, La Porte got more "
                "rain, thunderstorms and hail than the towns around it. Follow for the daily forecast and more La Porte "
                "weather history: laporteweathernow.com #LaPorte #Indiana #Weather #History #MichiganCity #NWIndiana",
        "credit_short": "Forecast: National Weather Service. Photos: Steve Shook, CC BY 2.0; Tichnor Bros. postcard "
                        "(public domain). Map: U.S. Census Bureau, Natural Earth.",
        "credit": "Forecast: National Weather Service. Photos: LaPorte Carriage Company, about 1912, Steve Shook via "
                  "Wikimedia Commons, " + CC2 + "; Hotel Rumely postcard, Tichnor Bros. (public domain). "
                  "Map: U.S. Census Bureau, Natural Earth.",
        "x": "La Porte's weather was once so strange, scientists studied it ⛈️ This week: mostly dry and near 70 "
             "right up to Halloween. #LaPorte #INwx\n\nForecast: NWS. Photos: Steve Shook, CC BY 2.0; Tichnor Bros. "
             "(public domain)",
    },
    {
        "file": "belle-gunness-part-3-the-newspaper-ad.mp4", "when": "2026-10-25T19:00:00-05:00", "cover_ms": 600,
        "youtube_title": "The newspaper ad that lured men to Belle Gunness's farm (Part 3)",
        "body": "Part 3: The newspaper ad 🕯️ \"Triflers need not apply.\" Belle Gunness advertised as a comely widow "
                "with a large farm in La Porte County. Andrew Helgelien, a South Dakota farmer, answered it, and in "
                "January 1908 he came to La Porte with nearly $3,000. Follow for Part 4: the clue that didn't fit. "
                "#BelleGunness #LaPorte #Indiana #History #TrueStory #Halloween",
        "credit_short": "The ad is re-created from its published text. Photos: public domain; Steve Shook, CC BY 2.0. "
                        "Map: Natural Earth.",
        "credit": "The ad is re-created from its published text. Photos: Belle Gunness, public domain; the Gunness "
                  "farm, its hog pen, the farm after the fire and photos from the case, 1908, Steve Shook via "
                  "Wikimedia Commons, " + CC2 + ". Map: Natural Earth.",
        "x": "Men answered her newspaper ad. Then one of them disappeared. Belle Gunness, part 3 🕯️ #LaPorte "
             "#BelleGunness #Halloween\n\nPhotos: public domain; Steve Shook, CC BY 2.0",
    },
    {
        "file": "belle-gunness-part-4-was-the-woman-in-the-fire-belle.mp4", "when": "2026-10-26T19:00:00-05:00",
        "cover_ms": 600,
        "youtube_title": "Belle Gunness: the clue that didn't fit (Part 4)",
        "body": "Part 4: Was the woman in the fire really Belle Gunness? 🔥 A doctor who knew her said the body was "
                "shorter and far lighter: \"It is not that of Mrs. Gunness.\" Her dentist and the coroner said it was "
                "her. Follow for Part 5: the woman arrested in Los Angeles in 1931. #BelleGunness #LaPorte #Indiana "
                "#History #Mystery #Halloween",
        "credit_short": "Photos: public domain; Steve Shook, CC BY 2.0",
        "credit": "Photos: Belle Gunness, public domain; the farm after the fire, a 1908 postcard, viewing the cellar "
                  "and reviewing remains at the farm, 1908, Steve Shook via Wikimedia Commons, " + CC2 + ".",
        "x": "A doctor who knew Belle Gunness said the body in the fire wasn't hers. Her dentist said it was. "
             "Part 4 🔥 #LaPorte #BelleGunness #Halloween\n\nPhotos: public domain; Steve Shook, CC BY 2.0",
    },
    {
        "file": "frankenstein-dracula-and-the-year-without-a-summer.mp4", "when": "2026-10-27T12:15:00-05:00",
        "cover_ms": 800,
        "youtube_title": "Frankenstein, Dracula and the Year Without a Summer",
        "body": "Frankenstein and Dracula trace back to the same rainy summer, and it started with a volcano 🌋⚡ Mount "
                "Tambora erupted in 1815, 1816 became the Year Without a Summer, and a ghost-story contest on Lake "
                "Geneva gave us Frankenstein and The Vampyre. Follow for La Porte's own Halloween stories. They're "
                "just as strange. #Halloween #Frankenstein #Dracula #History #LaPorte #Indiana",
        "credit_short": "All pictures are drawn; the 1818 and 1819 title pages are re-set from the first editions "
                        "(public domain).",
        "credit": "All pictures are drawn; the 1818 and 1819 title pages are re-set from the first editions "
                  "(public domain).",
        "x": "Frankenstein and Dracula trace back to the same rainy summer, and it started with a volcano 🌋⚡ "
             "#Halloween #Frankenstein #Dracula",
    },
    {
        "file": "belle-gunness-part-5-los-angeles-1931.mp4", "when": "2026-10-28T19:00:00-05:00", "cover_ms": 600,
        "youtube_title": "Was Belle Gunness still alive in 1931? (Part 5)",
        "body": "Part 5: Was Belle Gunness still alive in 1931? 🕯️ In Los Angeles, a housekeeper named Esther Carlson "
                "was charged with poisoning the 81-year-old man she worked for. She died of tuberculosis before her "
                "trial. Two people from La Porte viewed her body and swore it was Belle, and her trunk held a photo of "
                "three children said to be Belle's. No one ever proved it. Do you think Belle got away with it? "
                "#BelleGunness #LaPorte #Indiana #History #Mystery #Halloween",
        "credit_short": "Photos: public domain; Library of Congress (public domain); Steve Shook, CC BY 2.0. "
                        "Map: Natural Earth.",
        "credit": "Photos: Belle Gunness, public domain; Belle Gunness's children, Library of Congress, Bain "
                  "Collection (public domain); the Gunness farm and the farm after the fire, 1908, Steve Shook via "
                  "Wikimedia Commons, " + CC2 + ". Map: Natural Earth.",
        "x": "Was Belle Gunness still alive in 1931? Two people from La Porte swore a woman who died in Los Angeles "
             "was Belle. Part 5 🕯️ #LaPorte #BelleGunness\n\nPhotos: public domain; Library of Congress; "
             "Steve Shook, CC BY 2.0",
    },
]


def x_len(s):
    """X's weighted length: URLs count 23; code points outside X's light ranges count 2."""
    s = re.sub(r"(https?://\S+|\b[a-z0-9.-]+\.(?:com|org|gov)\S*)", "x" * 23, s)
    n = 0
    for ch in s:
        o = ord(ch)
        light = o <= 4351 or 8192 <= o <= 8205 or 8208 <= o <= 8223 or 8242 <= o <= 8247
        n += 1 if light else 2
    return n


def main():
    out = []
    for p in P:
        q = dict(p)
        q["tiktok"] = p["body"] + "\n\n" + p["credit_short"]
        q["youtube"] = p["body"] + "\n\n" + p["credit"]
        q["x_length"] = x_len(p["x"])
        assert q["x_length"] <= 280, (p["file"], q["x_length"])
        assert len(p["youtube_title"]) <= 100 and "<" not in q["youtube"] and ">" not in q["youtube"]
        out.append(q)
        print("%-58s x=%3d yt_title=%2d yt=%4d tt=%4d" % (p["file"], q["x_length"], len(p["youtube_title"]),
                                                          len(q["youtube"]), len(q["tiktok"])))
    json.dump(out, open(os.path.join(ROOT, "shorts", "out", "posts.json"), "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
