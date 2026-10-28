"""America After Dark (Oct. 2026): reported US ghost sightings, in the La Porte After Dark reels' look (same shared
drawing, captions, sound and mix as reel_afterdark.py). Three reels: the White House and Lincoln's ghost, Eastern State
Penitentiary, and the Stanley Hotel.

    python3 reel_afterdark_us.py wh_lincoln|eastern_state|stanley stills|video [times]

Everything on screen is typeset or drawn here; no AI pictures and no newspaper images. The photos are public domain
(verified on Wikimedia Commons) and credited on screen. Every sighting is worded "reported", "said to" or "legend".
"""
import math
import os
import sys

from PIL import Image, ImageDraw

import reels_common as C
from reels_common import bs, W, H, T, glow, paste, appear, BONE, INKC, BLOOD
from reel_belle import label_fn, typed, red_title, dot, PageCam, build_us_map
from reel_afterdark import EndCard, card_scene, stamp_over, jail_bars, PAPER

SERIES = "AMERICA AFTER DARK"
HEAD = "AMERICA AFTER DARK · "


# ----------------------------------------------------------------------------- shared pieces

def photo_hook(fname, tone, c1, titles, cred, f0=(0.5, 0.5), f1=(0.5, 0.5), z=(1.08, 1.2)):
    """The opening: a photo slowly pushing in, with a red title (titles: [(text, size, at)], the latest one shows)."""
    def prep(ctx):
        ctx["im"] = bs.photo(fname, tone)

    def draw(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c1, z=z, f0=f0, f1=f1)
        bs.shade(f)
        cur = titles[0]
        for x in titles:
            if t >= x[2] - 0.1:
                cur = x
        red_title(f, cur[0], cur[1], t, cur[2])
        bs.credit_line(f, cred)
    return C.Scene(0.0, c1, draw, prep)


def pin_map_scene(c0, c1, date, date_at, title, title_at, lonlat, label, shared, ring_at, cred="Map: Natural Earth"):
    """A map of the US: the camera drifts from the Midwest to the place, which gets a pin and a ring."""
    def prep(ctx):
        if "map" not in shared:
            shared["map"], shared["P"] = build_us_map()
        ctx.update(map=shared["map"], P=shared["P"], dot=dot(13, BLOOD),
                   lab=glow(T(label, "oldst_b", 40, INKC), PAPER, radius=10, strength=0.9))
        bx, by = shared["P"](*lonlat)
        ctx["cam"] = PageCam([(c0, 1.0, 1420, 960), (c0 + 0.4, 1.0, 1400, 965), (c1 - 0.2, 1.45, bx, by),
                              (c1, 1.45, bx, by)], ys=760)

    def draw(f, u, t, ctx):
        to, s = ctx["cam"].draw(f, ctx["map"], t)
        B = to(*ctx["P"](*lonlat))
        paste(f, ctx["dot"], B[0], B[1], appear(t, c0 + 0.5, 0.3))
        lab = ctx["lab"]
        if 70 + lab.width * 0.3 < B[0] < 1000 - lab.width * 0.3:
            paste(f, lab, min(max(B[0], 70 + lab.width / 2), 1000 - lab.width / 2), B[1] - 52,
                  appear(t, c0 + 0.7, 0.3))
        k = (t - ring_at) / 0.6
        if 0 <= k < 1:
            paste(f, C.ring(16 + 50 * k, 5, BLOOD, 1 - k), B[0], B[1])
        bs.shade(f)
        typed(f, date, t, date_at, 330, size=64, rate=0.04)
        bs.title(f, title, "bask", 96, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, title_at - 0.05, 0.2))
        bs.credit_line(f, cred)
    return C.Scene(c0, c1, draw, prep)


# ----------------------------------------------------------------------------- 1. the White House

def build_wh(R):
    """The White House and Lincoln's ghost. Facts (Wikipedia 'Lincoln's ghost', 'Lincoln Bedroom', 'Wilhelmina of the
    Netherlands'; White House Historical Association 'The Origin of the Abraham Lincoln Ghost Story', the ghost-stories
    backgrounder, and the Q&A on the most famous White House ghost): Lincoln was shot April 14, 1865 and died April 15;
    First Lady Grace Coolidge claimed to see him in the Yellow Oval Room; Queen Wilhelmina visited the US June 24 - Aug.
    11, 1942, and is said to have seen him at her door (some tellings: fainted; a 1996 Dutch newspaper: she did not);
    Truman family knocks at the Lincoln Bedroom door (Wikipedia only); the room was Lincoln's office in his day; the
    legend may trace to Jeremiah 'Jerry' Smith, a servant from the Grant years who told ghost stories to reporters
    (WHHA). Nothing is stated as fact."""
    t_since, t_staff = R.at("Since his"), R.at("staff and")
    t_grace = R.at("First Lady")
    t_wil, t_rep, t_acc = R.at("In 1942,"), R.at("reportedly"), R.at("Accounts differ")
    t_oth, t_day = R.at("Others reported"), R.at("In Lincoln's day,")
    t_jerry, t_serv, t_who = R.at("Some of"), R.at("a longtime"), R.at("who told")
    t_no, t_proved = R.at("No one"), R.at("proved")
    t_fol = R.at("Follow")
    c1, c2, c3 = t_since - 0.12, t_grace - 0.12, t_wil - 0.12
    c4, c5, c6, c7 = t_oth - 0.12, t_jerry - 0.12, t_no - 0.12, t_fol - 0.12
    GARD = "Photo: Alexander Gardner, 1863 · public domain"
    ROOM = "Yellow Oval Room, 1886 · Library of Congress · public domain"

    s_hook = photo_hook("ad-lincoln.jpg", "sepia", c1, [("LINCOLN'S GHOST?", 104, -0.2)], GARD,
                        f0=(0.5, 0.30), f1=(0.5, 0.33), z=(1.1, 1.3))

    s_lin = card_scene(c1, c2, "ABRAHAM LINCOLN", [
        ("— Shot April 14, 1865", t_since + 0.1), ("  Died April 15", None),
        ("— Since then: sightings", t_staff - 0.4), ("  reported by staff", None), ("  and guests", None)],
        "ad-lincoln.jpg", 31, date="1865", date_at=c1 + 0.05, cred=GARD)

    def p_room(ctx):
        ctx["im"] = bs.photo("ad-yellowoval.jpg", "sepia")
        ctx["lab"] = glow(T("YELLOW OVAL ROOM", "bold", 36, BONE, tracking=5), (0, 0, 0), radius=14, strength=0.9)

    def d_room(f, u, t, ctx):
        bs.kenburns(f, ctx["im"], u, c3 - c2, z=(1.05, 1.18), f0=(0.40, 0.5), f1=(0.55, 0.5))
        bs.shade(f)
        paste(f, ctx["lab"], W / 2, 450, appear(t, c2 + 0.1, 0.3))
        typed(f, "GRACE COOLIDGE", t, c2 + 0.1, 330, size=64, rate=0.05)
        bs.title(f, "SAID SHE SAW HIM", "bask", 92, BONE, 1205, glow=(0, 0, 0), alpha=appear(t, t_grace + 1.6, 0.25))
        bs.credit_line(f, ROOM)
    s_room = C.Scene(c2, c3, d_room, p_room)

    s_wil = card_scene(c3, c4, "QUEEN WILHELMINA", [
        ("— Visit: June–Aug. 1942", t_wil + 0.1),
        ("— Reportedly saw Lincoln", t_rep - 0.1), ("  at her door", None),
        ("— Did she faint?", t_acc - 0.3), ("  The accounts differ", None)],
        "ad-yellowoval.jpg", 33, date="1942", date_at=c3 + 0.05,
        over=stamp_over([("ACCOUNTS", 80), ("DIFFER", 112)], t_acc + 0.4, 150),
        cred="Queen Wilhelmina visited the U.S. June 24–Aug. 11, 1942")

    s_bed = card_scene(c4, c5, "LINCOLN BEDROOM", [
        ("— Reported: knocks at", t_oth + 0.1), ("  the door", None),
        ("— In Lincoln's day,", t_day - 0.1), ("  it was his office", None)],
        "ad-lincoln.jpg", 35, date="REPORTED KNOCKS", date_at=c4 + 0.05,
        cred=GARD)

    s_jerry = card_scene(c5, c6, "JERRY SMITH", [
        ("— Some of the legend", t_jerry + 0.1), ("  may trace to him", None),
        ("— A longtime servant", t_serv - 0.1), ("  who told ghost stories", t_who), ("  to reporters", None)],
        "ad-yellowoval.jpg", 37, date="THE 1880s", date_at=c5 + 0.05,
        cred="Source: White House Historical Association")

    s_ver = card_scene(c6, c7, "THE VERDICT", [
        ("— Sightings: reported", t_no + 0.05), ("— Proof: none", t_proved - 0.1)],
        "ad-lincoln.jpg", 39, date="LEGEND", date_at=c6 + 0.05,
        over=stamp_over([("NOT", 100), ("PROVEN", 108)], t_proved + 0.05, 120),
        cred=GARD)

    end = EndCard("ad-lincoln.jpg",
                  ["Wikipedia: Lincoln's ghost · Queen Wilhelmina",
                   "White House Historical Association",
                   "Photos: A. Gardner, 1863 · Yellow Oval Room: LoC"],
                  "The White House and Lincoln's Ghost", series=SERIES)

    def d_end(f, u, t, ctx):
        end.draw(f, u, R.dur - c7)

    scenes = [s_hook, s_lin, s_room, s_wil, s_bed, s_jerry, s_ver, C.Scene(c7, R.dur + 1, d_end, None)]
    film = C.Film(R, scenes, flashes=[(0.35, 0.32)], label=label_fn(HEAD + "WASHINGTON, D.C.", c1))
    ev = [("thunder", 0.33, 0.9), ("whoosh", c1, 0.7), ("type", c1 + 0.05, 0.9), ("type", t_since + 0.1, 0.8),
          ("whoosh", c2, 0.6), ("pop", c2 + 0.1, 0.7), ("whoosh", c3, 0.6), ("type", c3 + 0.05, 0.9),
          ("type", t_rep - 0.1, 0.8), ("hit", t_acc + 0.4, 1.0), ("whoosh", c4, 0.6), ("type", t_oth + 0.1, 0.8),
          ("thud", t_oth + 0.1, 0.6), ("whoosh", c5, 0.6), ("type", t_jerry + 0.1, 0.8), ("whoosh", c6, 0.6),
          ("type", t_no + 0.05, 0.8), ("hit", t_proved + 0.05, 1.0), ("whoosh", c7, 0.6), ("pop", c7 + 0.3, 0.8)]
    return film, ev, "lullaby", "America After Dark: The White House and Lincoln's Ghost"


# ----------------------------------------------------------------------------- 2. Eastern State

def build_es(R):
    """Eastern State Penitentiary, Philadelphia. Facts (easternstate.org: History of Eastern State, audio-tour
    transcript, FAQ; Wikipedia): opened 1829 around solitary confinement (the Pennsylvania System); Dickens visited
    in 1842 and wrote he believed it 'cruel and wrong'; Al Capone served time there in 1929, oral tradition names an
    empty cell as his but the site 'can't be sure'; Pennsylvania ceased operating it in 1970, the city used it
    briefly as a jail in 1971; the audio tour says of hauntings 'Who knows?', that visitors 'sensed something', and an
    author (Charles Adams, Philadelphia Ghost Stories) tells of a locksmith who described a powerful energy at an
    abandoned cell. Hauntings are not proven; the site does not allow paranormal investigations."""
    t_who, t_open, t_soli = R.at("who knows?"), R.at("It opened"), R.at("built around")
    t_dick, t_cruel = R.at("Charles Dickens"), R.at("called the")
    t_cap, t_trad, t_site = R.at("Al Capone"), R.at("Tradition names"), R.at("but the site")
    t_sure = R.at("sure.")
    t_pa, t_city = R.at("Pennsylvania stopped"), R.at("The city")
    t_vis, t_lock = R.at("Visitors have"), R.at("A locksmith")
    t_none, t_proven = R.at("None of"), R.at("proven.")
    t_fol = R.at("Follow")
    c1, c2, c3 = t_open - 0.12, t_dick - 0.12, t_cap - 0.12
    c4, c5, c6, c7 = t_pa - 0.12, t_vis - 0.12, t_none - 0.12, t_fol - 0.12
    CELLS = "Photo: Carol M. Highsmith, Library of Congress · public domain"
    AERIAL = "Aerial: Jack Boucher, HABS/Library of Congress · public domain"

    s_hook = photo_hook("ad-es-cells.jpg", "night", c1,
                        [("IS IT HAUNTED?", 104, -0.2), ("“WHO KNOWS?”", 104, t_who - 0.1)], CELLS,
                        f0=(0.5, 0.55), f1=(0.5, 0.5), z=(1.0, 1.25))

    s_open = jail_bars("ad-es-aerial.jpg", c1, c2, "PHILADELPHIA · 1829", c1 + 0.05, "SOLITARY CONFINEMENT",
                       t_soli + 0.1, AERIAL)

    s_dick = card_scene(c2, c3, "CHARLES DICKENS", [
        ("— Visited in 1842", t_dick + 0.3),
        ("— Called the practice", t_cruel), ("  “cruel and wrong”", None)],
        "ad-es-aerial.jpg", 41, date="1842", date_at=c2 + 0.05, cred=AERIAL)

    s_cap = card_scene(c3, c4, "AL CAPONE", [
        ("— 1929: served time here", t_cap + 0.1),
        ("— Tradition names one cell", t_trad), ("  as his", None),
        ("— The site: can't be sure", t_site)],
        "ad-es-cells.jpg", 43, date="1929", date_at=c3 + 0.05,
        over=stamp_over([("CAN'T BE", 90), ("SURE", 120)], t_sure - 0.1, 140),
        cred=CELLS)

    s_close = card_scene(c4, c5, "THE CLOSING", [
        ("— 1970: Pennsylvania", t_pa + 0.1), ("  stops running it", None),
        ("— 1971: the city holds", t_city - 0.1), ("  inmates, briefly", None)],
        "ad-es-aerial.jpg", 45, date="1970 – 1971", date_at=c4 + 0.05,
        cred=AERIAL)

    s_rep = card_scene(c5, c6, "VISITORS REPORT", [
        ("— Some “sensed something”", t_vis + 0.1),
        ("— A locksmith told an", t_lock - 0.1), ("  author of a powerful", None), ("  energy at an old cell", None)],
        "ad-es-cells.jpg", 47, date="REPORTED", date_at=c5 + 0.05,
        cred="Source: Eastern State audio tour · photo: C. Highsmith")

    s_ver = card_scene(c6, c7, "THE VERDICT", [
        ("— Reported by visitors", t_none + 0.05), ("— Proof: none", t_proven - 0.2)],
        "ad-es-cells.jpg", 49, date="LEGEND", date_at=c6 + 0.05,
        over=stamp_over([("NOT", 100), ("PROVEN", 108)], t_proven - 0.05, 120),
        cred=CELLS)

    end = EndCard("ad-es-cells.jpg",
                  ["easternstate.org: History · Audio tour · FAQ",
                   "Wikipedia: Eastern State Penitentiary",
                   "Photos: C. Highsmith, J. Boucher · Library of Congress"],
                  "Eastern State Penitentiary", series=SERIES)

    def d_end(f, u, t, ctx):
        end.draw(f, u, R.dur - c7)

    scenes = [s_hook, s_open, s_dick, s_cap, s_close, s_rep, s_ver, C.Scene(c7, R.dur + 1, d_end, None)]
    film = C.Film(R, scenes, flashes=[(0.35, 0.32)], label=label_fn(HEAD + "PHILADELPHIA", c1))
    ev = [("thunder", 0.33, 0.9), ("heartbeat", t_who, 0.6), ("whoosh", c1, 0.7), ("type", c1 + 0.05, 0.9),
          ("hit", t_soli + 0.1, 0.9), ("whoosh", c2, 0.6), ("type", c2 + 0.05, 0.9), ("type", t_cruel, 0.8),
          ("whoosh", c3, 0.6), ("type", t_cap + 0.1, 0.8), ("hit", t_sure - 0.1, 1.0), ("whoosh", c4, 0.6),
          ("type", t_pa + 0.1, 0.8), ("whoosh", c5, 0.6), ("type", t_vis + 0.1, 0.8), ("thud", t_lock, 0.7),
          ("whoosh", c6, 0.6), ("type", t_none + 0.05, 0.8), ("hit", t_proven - 0.05, 1.0), ("whoosh", c7, 0.6),
          ("pop", c7 + 0.3, 0.8)]
    return film, ev, "lullaby", "America After Dark: Eastern State Penitentiary"


# ----------------------------------------------------------------------------- 3. the Stanley Hotel

def build_st(R):
    """The Stanley Hotel, Estes Park, Colorado. Facts (Wikipedia 'The Stanley Hotel'; stanleyhotel.com Room 217 and
    Elizabeth's Spirited Grand King pages): built by Freelan Oscar Stanley of the Stanley Motor Carriage Company,
    opened 1909; in 1974 Stephen King and his wife spent one night as the hotel was closing for the season; Room 217 is
    alleged to be the room he was offered; The Shining was published in 1977; on June 25, 1911 a gas explosion
    (auxiliary gas lighting) injured a maid, and 1911 newspapers differ on her name (Wilson / Lambert) and details; the
    hotel's legend calls her Elizabeth Wilson and says her spirit returned to tend to guests, folding clothes. Said to,
    never proven."""
    t_steam, t_stan = R.at("The steam-car"), R.at("Estes Park")
    t_1974 = R.at("In 1974,")
    t_217, t_stay, t_nov = R.at("Room 217"), R.at("where he"), R.at("The novel")
    t_june, t_news, t_det = R.at("In June"), R.at("Newspapers"), R.at("details.")
    t_leg, t_calls, t_says = R.at("The hotel's"), R.at("names her"), R.at("says her")
    t_its, t_proved = R.at("It's a"), R.at("been proved.")
    t_fol = R.at("Follow")
    c1, c2 = t_steam - 0.12, t_1974 - 0.12
    c3, c4, c5, c6 = t_june - 0.12, t_leg - 0.12, t_its - 0.12, t_fol - 0.12
    PHOTO = "Photo: Rominator, 2007 · public domain (Wikimedia Commons)"
    shared = {}

    s_hook = photo_hook("ad-stanley.jpg", "night", c1, [("INSPIRED THE SHINING", 96, -0.2)], PHOTO,
                        f0=(0.5, 0.45), f1=(0.5, 0.40), z=(1.05, 1.25))

    s_map = pin_map_scene(c1, c2, "1909", c1 + 0.05, "THE STANLEY HOTEL", t_steam + 0.4, (-105.52, 40.38),
                          "ESTES PARK, COLO.", shared, t_stan - 0.2)

    s_king = card_scene(c2, c3, "STEPHEN KING", [
        ("— 1974: one night here", t_1974 + 0.2), ("  King and his wife", None),
                ("— Room 217: said to be", t_217 - 0.1), ("  where he stayed", t_stay - 0.1),
        ("— The Shining: 1977", t_nov - 0.1)],
        "ad-stanley.jpg", 51, date="1974", date_at=c2 + 0.05, cred=PHOTO)

    s_1911 = card_scene(c3, c4, "JUNE 25, 1911", [
        ("— A gas explosion", t_june + 0.2), ("  injures a maid", None),
        ("— Newspapers differ:", t_news - 0.1), ("  Wilson? Lambert?", None), ("  And on the details", t_det - 0.9)],
        "ad-stanley.jpg", 53, date="1911", date_at=c3 + 0.05,
        over=stamp_over([("ACCOUNTS", 80), ("DIFFER", 112)], t_det - 0.05, 150),
        cred="Source: Wikipedia, citing 1911 newspapers")

    s_leg = card_scene(c4, c5, "THE HOTEL'S LEGEND", [
        ("— Named: Elizabeth Wilson", t_calls - 0.1),
        ("— Her spirit is said to", t_says - 0.1), ("  still tidy rooms", None)],
        "ad-stanley.jpg", 55, date="LEGEND", date_at=c4 + 0.05,
        cred="Source: stanleyhotel.com · Wikipedia")

    s_ver = card_scene(c5, c6, "THE VERDICT", [
        ("— A reported haunting", t_its + 0.05), ("— Proof: none", t_proved - 0.3)],
        "ad-stanley.jpg", 57, date="LEGEND", date_at=c5 + 0.05,
        over=stamp_over([("NEVER", 96), ("PROVED", 104)], t_proved - 0.05, 120),
        cred=PHOTO)

    end = EndCard("ad-stanley.jpg",
                  ["Wikipedia: The Stanley Hotel",
                   "stanleyhotel.com: Room 217 · Elizabeth Wilson",
                   "Photo: Rominator · public domain"],
                  "The Stanley Hotel, Estes Park", series=SERIES)

    def d_end(f, u, t, ctx):
        end.draw(f, u, R.dur - c6)

    scenes = [s_hook, s_map, s_king, s_1911, s_leg, s_ver, C.Scene(c6, R.dur + 1, d_end, None)]
    film = C.Film(R, scenes, flashes=[(0.35, 0.32)], label=label_fn(HEAD + "ESTES PARK, COLO.", c1))
    ev = [("thunder", 0.33, 0.9), ("whoosh", c1, 0.7), ("type", c1 + 0.05, 0.9), ("pop", t_stan - 0.2, 0.8),
          ("whoosh", c2, 0.6), ("type", t_1974 + 0.2, 0.8), ("thud", t_217 - 0.1, 0.7), ("whoosh", c3, 0.6),
          ("type", t_june + 0.2, 0.8), ("hit", t_det - 0.05, 1.0), ("whoosh", c4, 0.6),
          ("type", t_calls - 0.1, 0.8), ("whoosh", c5, 0.6), ("type", t_its + 0.05, 0.8),
          ("hit", t_proved - 0.05, 1.0), ("whoosh", c6, 0.6), ("pop", c6 + 0.3, 0.8)]
    return film, ev, "lullaby", "America After Dark: The Stanley Hotel"


BUILD = {"wh_lincoln": build_wh, "eastern_state": build_es, "stanley": build_st}
FILES = {"wh_lincoln": "white-house-lincolns-ghost.mp4",
         "eastern_state": "eastern-state-penitentiary-philadelphia.mp4",
         "stanley": "the-stanley-hotel-estes-park.mp4"}


def main(name, mode, times=None):
    R = C.Reel(name)
    film, ev, music, title = BUILD[name](R)
    if mode == "stills":
        ts = times or [round(R.dur * k / 18, 2) for k in range(18)]
        print(R.dur, film.stills([t for t in ts if t < R.dur], name))
        return
    os.makedirs(C.OUT, exist_ok=True)
    vid = os.path.join(C.OUT, "_" + name + "_video.mp4")
    film.video(vid, cover_t=0.6)
    mix = C.soundtrack(R, music, ev)
    out = os.path.join(C.OUT, FILES[name])
    C.finish(R, vid, mix, out, title)
    os.replace(vid.replace(".mp4", "-cover.jpg"), out.replace(".mp4", "-cover.jpg"))
    os.remove(vid)
    print("made", out, C.measure(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else None)


