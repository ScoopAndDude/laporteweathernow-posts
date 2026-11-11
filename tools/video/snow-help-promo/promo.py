"""Snow Help website promos (Nov. 11, 2026): bright daytime shorts that show the real laporteweathernow.com
pages on a phone, with the series' usual computer voice. 1080 x 1920, 30 fps.

  python3 promo.py stills        a contact sheet per video -> out/<slug>_preview.jpg
  python3 promo.py video [slug]  the videos -> out/<slug>.mp4 (+ -cover.jpg)
"""
import json, math, os, random, subprocess, sys
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
AD = "/home/claude/afterdark"
sys.path.insert(0, os.path.join(AD, "film"))
W, H, FPS = 1080, 1920, 30
NAVY, ORANGE, AMBER, WHITE = (16, 38, 62), (232, 112, 22), (255, 184, 0), (255, 255, 255)
F = os.path.join(AD, "doc", "fonts")
def font(size, w="Black"): return ImageFont.truetype(os.path.join(F, f"Inter-{w}.otf"), size)
SHOT = {n: Image.open(os.path.join(HERE, "shots", n + ".jpg")).convert("RGB") for n in ("home", "sh_hero", "sh_ask", "sh_board", "sh_offer")}
LOGO = Image.open(os.path.join(AD, "doc", "logo-512.png")).convert("RGBA")
SAY = [["laporteweathernow\\.com", "LaPorte Weather Now dot com"]]
PX, PY, PW, PH, BEZ = 160, 430, 760, 990, 14           # the phone's screen

# beats: text, head (top headline), shot + scroll (start, end as fractions of the scrollable height) or "scoop"/"end"
STORIES = {
 "snow-help-ask-a-neighbor": ("Snow Help: snowed in? Ask a neighbor for a hand", [
  ("Snowed in, and can't clear the driveway? In LaPorte County, you can ask a neighbor for a hand.", "SNOWED IN?", "sh_hero", (0, .28)),
  ("Snow Help is new on laporteweathernow.com. Tell us what needs clearing, your town, and whether you need free help or can pay.", "NEW: SNOW HELP", "sh_ask", (.08, .55)),
  ("Your name and phone number are never posted. And we never ask for your address.", "ONLY YOUR TOWN SHOWS", "sh_board", (0, .3)),
  ("When a neighbor or a plow service offers to help, they call or text you. You decide who helps.", "A HELPER STEPS UP", "sh_board", (.3, .75)),
  ("And Scoop, who runs LaPorte Weather Now, will be out there himself, volunteering with a shovel.", "", "scoop", None),
  ("It's free to ask. Find it at laporteweathernow.com, right next to your forecast, radar, and alerts.", "FREE TO ASK", "home", (0, .62))],
  ("SNOWED IN?", "ASK A NEIGHBOR")),
 "snow-help-helpers-wanted": ("Snow Help: got a shovel or a plow? Helpers wanted", [
  ("Got a shovel, a snowblower, or a plow? Your neighbors in LaPorte County could use you this winter.", "HELPERS WANTED", "sh_board", (0, .4)),
  ("Join the Snow Help list at laporteweathernow.com. When someone near you can't dig out, you get an email.", "JOIN THE HELPER LIST", "sh_offer", (0, .35)),
  ("Tap I can help, and we send you that neighbor's first name and phone number. You call. You set the time. You clear the snow.", "YOU PICK THE JOBS", "sh_board", (.05, .6)),
  ("Volunteers and paid plow services are both welcome. Just agree on any price before you start.", "FREE OR PAID", "sh_offer", (.35, .75)),
  ("You won't be out there alone. Scoop, who runs LaPorte Weather Now, is volunteering to shovel too.", "", "scoop", None),
  ("Sign up before the snow flies, at laporteweathernow.com. Your forecast, radar, and alerts are there too.", "SIGN UP TODAY", "home", (0, .62))],
  ("HELPERS WANTED", "SHOVEL, BLOWER OR PLOW")),
 "snow-help-someone-who-cant-shovel": ("Snow Help: know someone who can't shovel?", [
  ("Know someone who can't shovel? A senior next door. A friend with a bad back. Your mom across town.", "CAN'T SHOVEL?", "sh_hero", (0, .28)),
  ("With their okay, you can ask for them on Snow Help, at laporteweathernow.com.", "ASK FOR THEM", "sh_ask", (.08, .4)),
  ("Check the box that says someone there can't safely shovel, and the request is marked priority.", "MARKED PRIORITY", "sh_board", (0, .3)),
  ("Helpers nearby get an email. When one offers, they get a first name and a phone number. Never an address.", "NEVER AN ADDRESS", "sh_board", (.3, .75)),
  ("Scoop, who runs LaPorte Weather Now, will be out there volunteering with a shovel himself.", "", "scoop", None),
  ("It's free to ask. And while you're there, check your forecast, radar, and alerts.", "FREE TO ASK", "home", (0, .62))],
  ("KNOW SOMEONE", "WHO CAN'T SHOVEL?")),
}
TAIL = 2.6            # the end card holds this long after the last word


def background():
    """A bright winter morning: blue sky, soft sun, snowy hills."""
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([112, 176, 232.0]), np.array([226, 241, 252.0])
    img = Image.fromarray(np.broadcast_to((top + (bot - top) * (y ** 0.8))[:, None, :], (H, W, 3)).astype(np.uint8).copy())
    sun = Image.new("L", (W, H), 0); ImageDraw.Draw(sun).ellipse((700, -120, 1180, 360), fill=120)
    img.paste(Image.new("RGB", (W, H), (255, 248, 220)), mask=sun.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(img)
    d.ellipse((-500, 1560, 900, 2500), fill=(236, 245, 252)); d.ellipse((300, 1640, 1700, 2500), fill=(246, 251, 255))
    d.ellipse((-300, 1740, 1400, 2700), fill=(255, 255, 255))
    return img

BG = background()
random.seed(7)
FLAKES = [(random.uniform(0, W), random.uniform(0, H), random.uniform(3, 9), random.uniform(55, 150), random.uniform(0, 6.3), random.uniform(.5, 1)) for _ in range(110)]

def snow(img, t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for x, y, r, v, ph, a in FLAKES:
        yy = (y + v * t) % (H + 40) - 20
        xx = (x + 26 * math.sin(t * 0.9 + ph)) % W
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 255, 255, int(235 * a)))
    img.alpha_composite(ov)

def rounded(size, r):
    m = Image.new("L", size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255); return m
SCREEN_MASK = rounded((PW, PH), 44)

def brand(img):
    d = ImageDraw.Draw(img)
    lg = LOGO.resize((92, 92), Image.LANCZOS); img.alpha_composite(lg, (60, 64))
    d.text((170, 74), "LAPORTE WEATHER NOW", font=font(34, "ExtraBold"), fill=NAVY)
    d.text((170, 116), "laporteweathernow.com", font=font(28, "SemiBold"), fill=(40, 78, 120))

def fit(d, text, weight, size, width):
    while size > 40 and d.textlength(text, font=font(size, weight)) > width: size -= 4
    return font(size, weight)

def headline(text):
    ov = Image.new("RGBA", (W, 230), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    f = fit(d, text, "Black", 104, W - 120)
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, 60), text, font=f, fill=NAVY, stroke_width=6, stroke_fill=WHITE)
    bw = min(w, 420); d.rounded_rectangle(((W - bw) / 2, 196, (W + bw) / 2, 210), 7, fill=ORANGE)
    return ov

def caption(text):
    ov = Image.new("RGBA", (W, 170), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    f = fit(d, text, "ExtraBold", 62, W - 200)
    w = d.textlength(text, font=f); pad = 34
    d.rounded_rectangle(((W - w) / 2 - pad, 22, (W + w) / 2 + pad, 142), 34, fill=NAVY + (242,))
    d.text(((W - w) / 2, 82), text, font=f, fill=WHITE, anchor="lm")
    return ov

def phone(img, shot, frac):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((PX - BEZ + 8, PY - BEZ + 14, PX + PW + BEZ + 8, PY + PH + BEZ + 14), 58, fill=(16, 38, 62, 70))
    d.rounded_rectangle((PX - BEZ, PY - BEZ, PX + PW + BEZ, PY + PH + BEZ), 58, fill=(18, 22, 30, 255))
    s = SHOT[shot]; sw = PW; sh = int(s.height * sw / s.width)
    top = int(max(0, sh - PH) * frac)
    key = (shot, sw)
    if key not in phone.cache: phone.cache[key] = s.resize((sw, sh), Image.LANCZOS)
    img.paste(phone.cache[key].crop((0, top, sw, top + PH)), (PX, PY), SCREEN_MASK)
phone.cache = {}

def shovel(d, cx, cy, s):
    """A simple snow shovel, drawn."""
    d.line((cx - 150 * s, cy - 250 * s, cx + 60 * s, cy + 80 * s), fill=(150, 98, 52), width=int(26 * s))
    d.line((cx - 195 * s, cy - 222 * s, cx - 105 * s, cy - 278 * s), fill=(150, 98, 52), width=int(26 * s))
    pts = [(cx - 30, cy + 40), (cx + 150, cy - 70), (cx + 250, cy + 110), (cx + 70, cy + 240)]
    d.polygon([(cx + (x - cx) * s, cy + (y - cy) * s) for x, y in pts], fill=ORANGE, outline=NAVY)
    d.line([(cx + (x - cx) * s, cy + (y - cy) * s) for x, y in (pts[3], pts[2])], fill=NAVY, width=int(12 * s))

def scoop_card(img, u):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((90, 440, W - 90, 1400), 56, fill=(255, 255, 255, 245), outline=ORANGE, width=8)
    shovel(d, 500, 760, 1.0)
    for i, (txt, col, size) in enumerate((("SCOOP WILL BE", NAVY, 92), ("OUT THERE", NAVY, 92), ("SHOVELING TOO", ORANGE, 92))):
        f = fit(d, txt, "Black", size, W - 280); w = d.textlength(txt, font=f)
        d.text(((W - w) / 2, 1014 + i * 100), txt, font=f, fill=col)
    f = font(34, "SemiBold"); t = "He runs LaPorte Weather Now. Volunteering, no charge."; w = d.textlength(t, font=f)
    d.text(((W - w) / 2, 1338), t, font=f, fill=(70, 90, 110))

def end_card(img, lines, u):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 380, W - 70, 1480), 60, fill=(255, 255, 255, 248))
    lg = LOGO.resize((300, 300), Image.LANCZOS); img.alpha_composite(lg, ((W - 300) // 2, 430))
    y = 780
    for txt, col in ((lines[0], NAVY), (lines[1], ORANGE)):
        f = fit(d, txt, "Black", 100, W - 240); w = d.textlength(txt, font=f)
        d.text(((W - w) / 2, y), txt, font=f, fill=col); y += 118
    f = font(40, "SemiBold"); t = "Free to ask  ·  LaPorte County, Indiana"; w = d.textlength(t, font=f)
    d.text(((W - w) / 2, 1050), t, font=f, fill=(60, 84, 110))
    url = "laporteweathernow.com/snow-help"; f = fit(d, url, "ExtraBold", 54, W - 300); w = d.textlength(url, font=f)
    d.rounded_rectangle(((W - w) / 2 - 44, 1150, (W + w) / 2 + 44, 1262), 56, fill=ORANGE)
    d.text((W / 2, 1206), url, font=f, fill=WHITE, anchor="mm")
    f = font(38, "Bold"); t = "Forecast  ·  Radar  ·  Alerts  ·  Snow Help"; w = d.textlength(t, font=f)
    d.text(((W - w) / 2, 1330), t, font=f, fill=NAVY)

def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def narrate(slug):
    import reel_story as RS
    title, beats, _ = STORIES[slug]
    st = {"slug": "promo-" + slug, "title": title, "say": SAY, "beats": [{"text": b[0]} for b in beats]}
    d = os.path.join(AD, "shorts", "r_" + RS.name_of(st))
    if not os.path.exists(os.path.join(d, "vo.json")) or json.load(open(os.path.join(d, "vo.json"))).get("script") != [b[0] for b in beats]:
        RS.narrate(st)
        j = json.load(open(os.path.join(d, "vo.json"))); j["script"] = [b[0] for b in beats]; json.dump(j, open(os.path.join(d, "vo.json"), "w"))
    return json.load(open(os.path.join(d, "vo.json"))), os.path.join(d, "vo.wav")


def plan(slug):
    """Scenes [(start, end, beat)] and caption chunks [(start, end, text)]."""
    vo, wav = narrate(slug)
    _, beats, _ = STORIES[slug]
    scenes = []
    for i in range(len(beats)):
        its = [x for x in vo["items"] if x["para"] == i]
        s = 0.0 if i == 0 else scenes[-1][1]
        nxt = [x for x in vo["items"] if x["para"] == i + 1]
        e = (its[-1]["e"] + nxt[0]["s"]) / 2 if nxt else its[-1]["e"] + 0.35
        scenes.append((s, e, i))
    caps = []
    for it in vo["items"]:
        words = it["text"].split(); groups = []; cur = []
        for w in words:
            cur.append(w)
            if len(cur) >= 4 or (w[-1] in ",.?!" and len(cur) >= 2): groups.append(" ".join(cur)); cur = []
        if cur:
            if groups and len(cur) == 1: groups[-1] += " " + cur[0]
            else: groups.append(" ".join(cur))
        total = sum(len(g) for g in groups); t = it["s"]
        for g in groups:
            dur = (it["e"] - it["s"]) * len(g) / total; caps.append((t, t + dur, g)); t += dur
    total = scenes[-1][1] + TAIL
    return scenes, caps, total, wav


def frame(slug, t, scenes, caps, total, cache):
    _, beats, endl = STORIES[slug]
    img = BG.convert("RGBA")
    snow(img, t)
    brand(img)
    end_at = scenes[-1][1]
    if t >= end_at:
        end_card(img, endl, (t - end_at) / TAIL)
    else:
        s, e, i = next(sc for sc in scenes if sc[0] <= t < sc[1] or sc is scenes[-1])
        text, head, shot, scroll = beats[i]
        u = (t - s) / (e - s)
        if shot == "scoop":
            scoop_card(img, u)
        else:
            phone(img, shot, scroll[0] + (scroll[1] - scroll[0]) * ease(u))
        if head:
            if ("h", head) not in cache: cache[("h", head)] = headline(head)
            a = ease((t - s) / 0.3); h = cache[("h", head)]
            if a < 1: h = Image.eval(h, lambda v: v) ; h.putalpha(h.getchannel("A").point(lambda v: int(v * a)))
            img.alpha_composite(h, (0, int(170 + 24 * (1 - a))))
        c = next((c for c in caps if c[0] <= t < c[1] + 0.12), None)
        if c:
            if ("c", c[2]) not in cache: cache[("c", c[2])] = caption(c[2])
            img.alpha_composite(cache[("c", c[2])], (0, 1470))
        d = ImageDraw.Draw(img); f = font(26, "SemiBold"); note = "Example requests are made up. Narration is a computer voice."
        d.text(((W - d.textlength(note, font=f)) / 2, 1668), note, font=f, fill=(60, 84, 110))
    return img.convert("RGB")


def music(total):
    """A light, bright bed: soft plucked arpeggios in C major."""
    sr = 44100; n = int(total * sr); out = np.zeros(n, np.float32)
    chords = [(261.63, 329.63, 392.0, 523.25), (196.0, 246.94, 293.66, 392.0), (220.0, 261.63, 329.63, 440.0), (174.61, 220.0, 261.63, 349.23)]
    step = 0.32; k = 0; t = 0.0
    while t < total - 0.5:
        ch = chords[(k // 8) % 4]; f0 = ch[(0, 2, 1, 3, 2, 1, 3, 2)[k % 8]] * (2 if k % 8 in (3, 6) else 1)
        ln = int(1.4 * sr); tt = np.arange(ln) / sr
        note = (np.sin(2 * np.pi * f0 * tt) + 0.35 * np.sin(4 * np.pi * f0 * tt) + 0.12 * np.sin(6 * np.pi * f0 * tt)) * np.exp(-tt * 3.2) * np.minimum(1, tt / 0.008)
        a = int(t * sr); b = min(n, a + ln); out[a:b] += (0.22 * note[:b - a]).astype(np.float32)
        if k % 8 == 0:
            bl = int(2.4 * sr); bt = np.arange(bl) / sr; bass = np.sin(2 * np.pi * ch[0] / 2 * bt) * np.exp(-bt * 1.1) * np.minimum(1, bt / 0.02)
            b2 = min(n, a + bl); out[a:b2] += (0.2 * bass[:b2 - a]).astype(np.float32)
        t += step; k += 1
    fade = int(1.2 * sr); out[:fade] *= np.linspace(0, 1, fade); out[-fade:] *= np.linspace(1, 0, fade)
    return out, sr


def stills(slug):
    scenes, caps, total, _ = plan(slug)
    times = [s + (e - s) * f for s, e, _ in scenes for f in (0.25, 0.8)] + [total - 1.0]
    cache = {}; fr = [frame(slug, t, scenes, caps, total, cache) for t in times]
    cols = 7; rows = math.ceil(len(fr) / cols); sheet = Image.new("RGB", (cols * 360, rows * 640), (0, 0, 0))
    for i, f in enumerate(fr): sheet.paste(f.resize((360, 640), Image.LANCZOS), ((i % cols) * 360, (i // cols) * 640))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    sheet.save(os.path.join(HERE, "out", slug + "_preview.jpg"), quality=88)
    fr[0].save(os.path.join(HERE, "out", slug + "_f0.jpg"), quality=90); fr[-1].save(os.path.join(HERE, "out", slug + "_fend.jpg"), quality=90)
    print(slug, "%.1f s" % total)


def video(slug):
    scenes, caps, total, wav = plan(slug)
    out = os.path.join(HERE, "out"); tmp = os.path.join(out, "tmp_" + slug); os.makedirs(tmp, exist_ok=True)
    cuts = [(s, e) for s, e, _ in scenes] + [(scenes[-1][1], total)]
    files = []; cache = {}; n0 = 0
    for k, (s, e) in enumerate(cuts):
        n1 = round(e * FPS); part = os.path.join(tmp, "s%02d.part.mp4" % k); final = os.path.join(tmp, "s%02d.mp4" % k)
        p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS), part], stdin=subprocess.PIPE)
        for n in range(n0, n1): p.stdin.write(frame(slug, n / FPS, scenes, caps, total, cache).tobytes())
        p.stdin.close()
        if p.wait() != 0: raise SystemExit("ffmpeg failed on scene %d" % k)
        os.replace(part, final); files.append(final); n0 = n1
    lst = os.path.join(tmp, "list.txt"); open(lst, "w").write("".join("file '%s'\n" % f for f in files))
    silent = os.path.join(tmp, "silent.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)
    vo, vsr = sf.read(wav, dtype="float32"); m, sr = music(total)
    idx = np.minimum(len(vo) - 1, (np.arange(int(len(vo) * sr / vsr)) * vsr / sr).astype(int)); voice = vo[idx]
    mix = m * 0.5; mix[:len(voice)] += voice[:len(mix)] * 1.0
    mixw = os.path.join(tmp, "mix.wav"); sf.write(mixw, mix / max(1.0, np.abs(mix).max() / 0.95), sr)
    final = os.path.join(out, slug + ".mp4"); part = os.path.join(out, slug + ".part.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", silent, "-i", mixw, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart",
                    "-metadata", "title=" + STORIES[slug][0], part], check=True)
    os.replace(part, final)
    frame(slug, 1.2, scenes, caps, total, cache).save(os.path.join(out, slug + "-cover.jpg"), quality=90)
    print(slug, "%.1f s" % total, final)


if __name__ == "__main__":
    mode = sys.argv[1]; slugs = sys.argv[2:] or list(STORIES)
    for s in slugs: (stills if mode == "stills" else video)(s)
