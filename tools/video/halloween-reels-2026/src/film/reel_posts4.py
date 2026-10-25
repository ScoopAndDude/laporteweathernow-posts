"""TikTok, YouTube and X text for the second batch of La Porte legends (Oct. 25; not posted until Scoop OKs them).

python3 reel_posts4.py  ->  shorts/out/posts-legends-oct-25.json
"""
import json
import os

from reel_posts import x_len

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOD = "Ashley Hood, Haunted Cemeteries of Indiana (2020), via the La Porte County Herald-Dispatch"
ND = "Patricia Harrison, \"La Porte County's Top 10 Most Haunted,\" The News-Dispatch (2011)"
P = [
    {
        "file": "orr-lake-road-the-doctors-lantern.mp4", "cover_ms": 800,
        "youtube_title": "The doctor's lantern: Orr Lake Road's full-moon legend (La Porte)",
        "body": "Tonight's a full moon 🌕 On Orr Lake Road, legend says that's when the doctor walks. The story goes that "
                "sometime in the 1900s, a doctor lived out here with his wife and daughter. When they died, he couldn't "
                "let them go, and kept their bodies in barrels. On full-moon nights, people say his lantern moves into the "
                "woods beside a servant with a hook for a hand. There's no record any of it happened. People live on Orr "
                "Lake Road, so if you drive it tonight, keep rolling. #LaPorte #Haunted #Halloween #FullMoon "
                "#UrbanLegend #Indiana",
        "credit_short": "All pictures are drawn. Legend: The News-Dispatch (2011).",
        "credit": "All pictures are drawn. Legend: " + ND + ". More La Porte legends: laporteweathernow.com/hauntings",
        "x": "Tonight's a full moon 🌕 On Orr Lake Road, legend says that's when the doctor walks, his lantern moving "
             "into the woods beside a servant with a hook for a hand. No record it ever happened. People live there, so "
             "keep rolling. #LaPorte #Haunted\n\nPictures drawn.",
    },
    {
        "file": "pine-lake-cemetery-buried-alive.mp4", "cover_ms": 800,
        "youtube_title": "Buried alive? Pine Lake Cemetery's darkest story (La Porte, Indiana)",
        "body": "When La Porte moved its old city cemetery in 1871, a story came up with the coffins ⚰️ Many of the dead "
                "were reburied at Pine Lake Cemetery, marked only as unknown. People say one woman was found upside down "
                "and twisted in her coffin, as if she'd been buried alive. Pine Lake also holds a mass grave: the bones "
                "of about ten unknown men from Belle Gunness's farm, split between two caskets. Visitors report shadows "
                "like mist above the stones. Please visit in daylight, and pull into the cemetery rather than stopping "
                "on US-35. #LaPorte #Haunted #Halloween #BelleGunness #Indiana #History",
        "credit_short": "All pictures are drawn. Source: Haunted Cemeteries of Indiana (2020); "
                        "laporteweathernow.com/hauntings",
        "credit": "All pictures are drawn. History and legends: " + HOOD + ". The full case file: "
                  "laporteweathernow.com/hauntings",
        "x": "When La Porte moved its old city cemetery in 1871, a story came up with the coffins: a woman found upside "
             "down and twisted in hers, as if buried alive. Pine Lake Cemetery, a La Porte legend ⚰️ #LaPorte #Haunted "
             "#Halloween\n\nPictures drawn.",
    },
    {
        "file": "la-porte-county-4-places-the-dead-dont-rest.mp4", "cover_ms": 800,
        "youtube_title": "4 places in La Porte County where the dead don't rest",
        "body": "4 places in La Porte County where people say the dead don't rest 👻 4. Orr Lake Road, where a doctor's "
                "lantern is said to move through the woods under a full moon. 3. Pine Lake Cemetery, where shadows like "
                "mist drift over a mass grave of Belle Gunness's victims. 2. Patton Cemetery, where a neighbor says they "
                "hear people talking at night, and no one's there. 1. Posey Chapel Cemetery near Hesston: bells, "
                "bouncing lights and a woman in white. Which one would you visit? Tell us in the comments! Cemeteries "
                "are for daylight, and people live on Orr Lake Road, so keep rolling. #LaPorte #Haunted #Halloween "
                "#Indiana #GhostStories",
        "credit_short": "All pictures are drawn. Sources: The News-Dispatch (2011); Haunted Cemeteries of Indiana (2020).",
        "credit": "All pictures are drawn. Sources: " + ND + "; " + HOOD + ". The full case files: "
                  "laporteweathernow.com/hauntings",
        "x": "4 places in La Porte County where people say the dead don't rest 👻 4. Orr Lake Road 3. Pine Lake "
             "Cemetery 2. Patton Cemetery 1. Posey Chapel Cemetery. Which one would you visit? #LaPorte #Haunted "
             "#Halloween\n\nPictures drawn.",
    },
]


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
        print("%-48s x=%3d yt_title=%2d yt=%4d tt=%4d" % (p["file"], q["x_length"], len(p["youtube_title"]),
                                                          len(q["youtube"]), len(q["tiktok"])))
    json.dump(out, open(os.path.join(ROOT, "shorts", "out", "posts-legends-oct-25.json"), "w"), indent=1,
              ensure_ascii=False)


if __name__ == "__main__":
    main()
