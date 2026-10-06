#!/usr/bin/env node
/*
  The Sky Devotion for La Porte (La Porte Weather Now, Oct. 6, 2026): once each morning, picks today's
  devotion by what the sky is doing and saves it in devotion.json, which the Faith page, the free
  church widget (devotion/index.html) and later emails read.

  Weather: the morning NWS snapshot (nws-snapshot.json) when it's from the last 4 hours, otherwise the
  National Weather Service directly. The pick itself is devotion/sky.js, the same code the widget runs.
  Once a day: if today's devotion is already saved it stays (pass "force" to pick again).
  It also remembers the season's first frost and first snow, and yesterday's sky ("after the storm").
*/
const fs = require("fs");
const path = require("path");
const Sky = require("../devotion/sky.js");

const ROOT = path.join(__dirname, "..");
const OUT = path.join(ROOT, "devotion.json");
const LAT = 41.6081, LON = -86.7189;          // La Porte (the same spot as the Daily Scoop)
const TZ = "America/Chicago";
const UA = { "User-Agent": "LaPorteWeatherNow/1.0 (laporteweathernow.com; laporteweathernow@gmail.com)", Accept: "application/geo+json" };

function localParts(d) {
  const f = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
  const p = Object.fromEntries(f.formatToParts(d).map((x) => [x.type, x.value]));
  return { ymd: `${p.year}-${p.month}-${p.day}`, month: +p.month, year: +p.year, hour: +p.hour % 24 };
}
function addDays(ymd, n) {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}
async function getJson(url, tries = 3) {
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(url, { headers: UA });
      if (!r.ok) throw new Error(`${r.status} ${url}`);
      return await r.json();
    } catch (e) { last = e; await new Promise((s) => setTimeout(s, 3000 * (i + 1))); }
  }
  throw last;
}
async function weather(now) {
  try {
    const snap = JSON.parse(fs.readFileSync(path.join(ROOT, "nws-snapshot.json"), "utf8"));
    const age = (now - new Date(snap.fetched)) / 3600000;
    if (age >= 0 && age <= 4 && snap.forecast && snap.forecast.periods && snap.forecast.periods.length) {
      return { periods: snap.forecast.periods, alerts: (snap.alertsLaPorteCounty || []).map((a) => a.event), source: `NWS snapshot ${snap.fetched}` };
    }
  } catch (e) { /* fall through to the NWS */ }
  const pt = await getJson(`https://api.weather.gov/points/${LAT},${LON}`);
  const fc = await getJson(pt.properties.forecast);
  let alerts = [];
  try {
    const al = await getJson(`https://api.weather.gov/alerts/active?point=${LAT},${LON}`);
    alerts = (al.features || []).map((f) => f.properties.event);
  } catch (e) { console.log("alerts didn't answer:", e.message); }
  return { periods: fc.properties.periods, alerts, source: `NWS forecast ${fc.properties.updateTime || fc.properties.generatedAt || ""}` };
}

(async () => {
  const now = new Date();
  const lp = localParts(now);
  const force = process.argv.includes("force");
  let saved = {};
  try { saved = JSON.parse(fs.readFileSync(OUT, "utf8")); } catch (e) { /* first run */ }
  if (saved.date === lp.ymd && !force) { console.log(`Today's devotion is already saved (${saved.entry && saved.entry.id}).`); return; }

  const library = JSON.parse(fs.readFileSync(path.join(ROOT, "devotion", "library.json"), "utf8"));
  const seasonYear = lp.month >= 7 ? lp.year : lp.year - 1;     // a frost/snow season runs July to June
  let season = saved.season && saved.season.year === seasonYear ? saved.season : { year: seasonYear, firstFrost: null, firstSnow: null };
  const history = (saved.history || []).filter((h) => h.date !== lp.ymd);
  const yesterday = history.find((h) => h.date === addDays(lp.ymd, -1));

  const w = await weather(now);
  const state = { firstFrostSeen: !!season.firstFrost, firstSnowSeen: !!season.firstSnow, yesterdaySky: yesterday ? yesterday.sky : null };
  const c = Sky.classify({ periods: w.periods, alerts: w.alerts, month: lp.month, state });
  // Frost or snow days also count as the season's first, even when a louder sky (a warning) won the pick.
  const lowTonight = w.periods.slice(0, 2).map(Sky.normPeriod).filter((p) => !p.isDaytime).map((p) => p.temp)[0];
  if (!season.firstFrost && (c.sky === "first-frost" || c.sky === "frost" || (lowTonight != null && lowTonight <= 32 && lp.month >= 8))) season.firstFrost = lp.ymd;
  if (!season.firstSnow && (c.sky === "first-snow" || c.sky === "snow" || c.sky === "winter-storm")) season.firstSnow = lp.ymd;
  const e = Sky.pick(library, c.sky, lp.ymd);
  history.push({ date: lp.ymd, sky: c.sky, id: e.id });
  const out = {
    about: "Today's Sky Devotion for La Porte, Indiana, picked each morning by what the sky is doing (devotion/sky.js). By La Porte Weather Now. Scripture: KJV (public domain). Weather: National Weather Service.",
    date: lp.ymd,
    generated: now.toISOString(),
    place: "La Porte, Indiana",
    lat: LAT, lon: LON,
    sky: c.sky, reason: c.reason, alert: c.alert,
    forecastLine: Sky.forecastLine(w.periods),
    weatherSource: w.source,
    entry: { id: e.id, sky: e.sky, ref: e.ref, kjv: e.kjv, text: e.text },
    season,
    history: history.slice(-60),
  };
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1) + "\n");
  console.log(`Saved ${lp.ymd}: ${c.sky} (${c.reason}) -> ${e.id} ${e.ref}`);
})().catch((e) => { console.error("Couldn't pick today's devotion:", e); process.exit(1); });
