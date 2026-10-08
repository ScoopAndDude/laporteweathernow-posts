/**
 * LPWN Daily Video to YouTube (La Porte Weather Now, Oct. 8, 2026)
 *
 * Uploads the Daily Video to the La Porte Weather Now YouTube channel (youtube.com/@laporteweathernow)
 * as a Short, once a day. The video is made at 6:00 AM Central on GitHub (laporteweathernow-posts,
 * branch "video", see video/README.md); this script picks it up between 6:00 and 9:30 AM.
 * Free: YouTube's own API through Apps Script. (Since 2026, uploads from unverified API projects are
 * no longer held as private.)
 *
 * Same safety rules as the Facebook and Instagram posting:
 * - Only a video made today, in the last 2 hours, and only once a day.
 * - Right before uploading it checks NWS alerts for La Porte again: no upload if a short-fused warning
 *   is in effect, or if an alert came or went since the video was made.
 *
 * SETUP (one time, about 5 minutes, signed in as laporteweathernow@gmail.com, which owns the channel):
 *   1. Go to script.google.com > New project. Name it "LPWN Daily Video to YouTube".
 *   2. Delete the starter code, paste this whole file, and Save.
 *   3. On the left, Services (+) > "YouTube Data API v3" > Add.
 *   4. At the top, pick the function "setup" and click Run. Google asks once: Review permissions >
 *      laporteweathernow@gmail.com > Allow. The log should say the channel's name.
 *   That's it: setup() makes a trigger that runs tick() every 15 minutes.
 * To stop it: Triggers (the clock on the left) > delete the "tick" trigger.
 * The last upload is in Project Settings > Script Properties (lastDate, lastVideoId, lastNote).
 */
const VIDEO_BRANCH = "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/video/";
const NWS_ALERTS = ["https://api.weather.gov/alerts/active?point=41.6081,-86.7189",
                    "https://api.weather.gov/alerts/active/zone/INZ103", "https://api.weather.gov/alerts/active/zone/INZ203",
                    "https://api.weather.gov/alerts/active/zone/INC091"];
const UA = { "User-Agent": "LaPorteWeatherNow/1.0 (+https://laporteweathernow.com)", "Accept": "application/geo+json" };
const TZ = "America/Chicago";
const SHORT_FUSED = ["Tornado Warning", "Severe Thunderstorm Warning", "Flash Flood Warning", "Extreme Wind Warning",
                     "Snow Squall Warning", "Dust Storm Warning", "Tornado Emergency", "Flash Flood Emergency"];

function setup() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "tick") ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger("tick").timeBased().everyMinutes(15).create();
  const ch = YouTube.Channels.list("snippet", { mine: true });
  const name = ch.items && ch.items.length ? ch.items[0].snippet.title : "(no channel found)";
  Logger.log("Ready. Uploads go to the YouTube channel: " + name + ". Checks every 15 minutes, 6:00-9:30 AM Central.");
}

function note_(props, text) {
  props.setProperty("lastNote", Utilities.formatDate(new Date(), TZ, "yyyy-MM-dd HH:mm") + " " + text);
  Logger.log(text);
}

function tick() {
  const now = new Date();
  const hm = Utilities.formatDate(now, TZ, "HH:mm");
  if (hm < "06:00" || hm > "09:30") return;
  const today = Utilities.formatDate(now, TZ, "yyyy-MM-dd");
  const props = PropertiesService.getScriptProperties();
  if (props.getProperty("lastDate") === today) return;

  const res = UrlFetchApp.fetch(VIDEO_BRANCH + "video.json?t=" + now.getTime(), { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) return;                 // no video branch yet, or GitHub is slow
  const rec = JSON.parse(res.getContentText());
  if (rec.date !== today || !rec.video) return;              // today's isn't made yet
  const made = new Date(rec.planned || rec.made);
  if (now - made > 2 * 3600 * 1000) {
    props.setProperty("lastDate", today);
    return note_(props, "Not uploaded: today's video is more than 2 hours old.");
  }

  // NWS alerts for La Porte County, again (the same places the video job asks: La Porte itself and
  // the county's zones): nothing short-fused, and the same alerts as when the video was made.
  const events = [];
  const seen = {};
  for (const url of NWS_ALERTS) {
    let a;
    try {
      a = UrlFetchApp.fetch(url, { headers: UA, muteHttpExceptions: true });
    } catch (e) {
      return;                                                // try again in 15 minutes
    }
    if (a.getResponseCode() !== 200) return;
    (JSON.parse(a.getContentText()).features || []).forEach(function (f) {
      const p = f.properties || {};
      if (!p.event || seen[p.id] || p.messageType === "Cancel" || (p.status || "Actual") !== "Actual") return;
      if (new Date(p.ends || p.expires || 0) <= now) return;
      seen[p.id] = true;
      events.push(p.event);
    });
  }
  const short = events.filter(function (e) { return SHORT_FUSED.some(function (k) { return e.indexOf(k) >= 0; }); });
  if (short.length) {
    props.setProperty("lastDate", today);
    return note_(props, "Not uploaded: " + short.join(", ") + " in effect for La Porte County.");
  }
  const key = function (list) { return Array.from(new Set(list)).sort().join("|"); };
  if (key(events) !== key((rec.alerts || []).map(function (a) { return a.event; }))) {
    props.setProperty("lastDate", today);
    return note_(props, "Not uploaded: NWS alerts for La Porte County changed since the video was made.");
  }

  const blob = UrlFetchApp.fetch(VIDEO_BRANCH + rec.video).getBlob().setContentType("video/mp4").setName(rec.video);
  const day = Utilities.formatDate(made, TZ, "EEE, MMM d");
  const hook = (rec.hook && rec.hook.say) || "today's forecast";
  let title = "La Porte weather, " + day + ": " + hook;
  if (title.length > 100) title = title.slice(0, 97).replace(/\s+\S*$/, "") + "...";
  const video = YouTube.Videos.insert({
    snippet: {
      title: title,
      description: rec.caption || "La Porte, Indiana weather from the National Weather Service. laporteweathernow.com",
      categoryId: "25",
      tags: ["La Porte", "La Porte Indiana", "La Porte County", "weather", "forecast", "Indiana weather"],
    },
    status: { privacyStatus: "public", selfDeclaredMadeForKids: false },
  }, "snippet,status", blob);
  props.setProperty("lastDate", today);
  props.setProperty("lastVideoId", video.id);
  note_(props, "Uploaded https://youtube.com/shorts/" + video.id + " (" + title + ")");
}
