// Tests for devotion/sky.js (run: node tools/devotion/test_sky.js from the posts repo root).
const S = require("../../devotion/sky.js");
const lib = require("../../devotion/library.json");
let fails = 0;
function P(name, isDaytime, temp, pop, short, wind, detailed) {
  return { name, isDaytime, temperatureF: temp, rainChancePercent: pop, short, wind: wind || "W 5 to 10 mph", detailed: detailed || short };
}
const day = (short, t, pop, wind, det) => P("Today", true, t, pop || 0, short, wind, det);
const night = (short, t, pop, wind, det) => P("Tonight", false, t, pop || 0, short, wind, det);
function check(label, input, want) {
  const got = S.classify(input).sky;
  if (got !== want) { fails++; console.log("FAIL", label, "got", got, "want", want, S.classify(input)); }
  else console.log("ok  ", label, "->", got);
}
const oct = 10, jan = 1, jul = 7;
check("sunny mild", { periods: [day("Sunny", 70), night("Mostly Clear", 54)], month: oct }, "beautiful");
check("sunny hot-ish", { periods: [day("Sunny", 88), night("Clear", 66)], month: jul }, "clear");
check("mostly cloudy", { periods: [day("Mostly Cloudy", 60), night("Mostly Cloudy", 48)], month: oct }, "gray");
check("partly sunny is gray", { periods: [day("Partly Sunny", 58), night("Partly Cloudy", 45)], month: oct }, "gray");
check("partly cloudy is clear", { periods: [night("Partly Cloudy", 45), day("Sunny", 85)], month: jul }, "clear");
check("storms", { periods: [day("Chance Showers And Thunderstorms", 78, 60), night("Showers And Thunderstorms Likely", 64, 70)], month: jul }, "storm");
check("rain", { periods: [day("Rain Likely", 55, 70), night("Rain", 50, 90)], month: oct }, "rain");
check("slight chance rain is not rain", { periods: [day("Slight Chance Rain Showers", 60, 20), night("Mostly Cloudy", 48, 10)], month: oct }, "gray");
check("fog", { periods: [day("Patchy Fog then Sunny", 68), night("Clear", 50)], month: oct }, "fog");
check("first frost", { periods: [day("Sunny", 50), night("Clear", 30)], month: oct, state: { firstFrostSeen: false } }, "first-frost");
check("frost after first", { periods: [day("Sunny", 50), night("Clear", 30)], month: oct, state: { firstFrostSeen: true } }, "frost");
check("frost advisory", { periods: [day("Sunny", 52), night("Clear", 34)], alerts: ["Frost Advisory"], month: oct, state: { firstFrostSeen: true } }, "frost");
check("cold night in January is not frost", { periods: [day("Mostly Cloudy", 31), night("Mostly Cloudy", 22)], month: jan }, "gray");
check("first snow", { periods: [day("Snow Showers Likely", 33, 60), night("Chance Snow Showers", 28, 40)], month: 11, state: { firstSnowSeen: false } }, "first-snow");
check("snow", { periods: [day("Snow", 28, 90), night("Snow Likely", 22, 70)], month: jan, state: { firstSnowSeen: true } }, "snow");
check("snow without state", { periods: [day("Snow", 28, 90), night("Snow Likely", 22, 70)], month: 12 }, "snow");
check("tornado watch", { periods: [day("Showers And Thunderstorms", 80, 80), night("Thunderstorms", 65, 70)], alerts: ["Tornado Watch"], month: 5 }, "severe");
check("alert object shape", { periods: [day("Sunny", 70)], alerts: [{ event: "Severe Thunderstorm Warning" }], month: 6 }, "severe");
check("winter storm warning", { periods: [day("Snow", 25, 100), night("Snow", 18, 100)], alerts: ["Winter Storm Warning"], month: jan }, "winter-storm");
check("flood watch", { periods: [day("Rain", 60, 100), night("Rain", 55, 100)], alerts: ["Flood Watch"], month: 4 }, "flood");
check("heat advisory", { periods: [day("Sunny", 93), night("Clear", 74)], alerts: ["Heat Advisory"], month: jul }, "heat");
check("hot without alert", { periods: [day("Sunny", 95), night("Clear", 74)], month: jul }, "heat");
check("bitter cold", { periods: [day("Sunny", 12), night("Clear", -5)], month: jan }, "cold");
check("wind chill advisory", { periods: [day("Mostly Sunny", 24), night("Clear", 8)], alerts: ["Wind Chill Advisory"], month: jan }, "cold");
check("freezing rain", { periods: [day("Freezing Rain Likely", 31, 70), night("Freezing Drizzle", 29, 40)], month: jan }, "ice");
check("windy", { periods: [day("Mostly Sunny", 58, 0, "W 15 to 25 mph", "Mostly sunny. Windy, with gusts as high as 40 mph."), night("Clear", 40)], month: oct }, "wind");
check("breezy word", { periods: [day("Sunny and Breezy", 65), night("Clear", 45)], month: oct }, "wind");
check("after the storm", { periods: [day("Sunny", 72), night("Clear", 55)], month: oct, state: { yesterdaySky: "storm" } }, "after-storm");
check("rain beats first frost? no: first frost wins", { periods: [day("Rain Likely", 45, 70), night("Mostly Clear", 31)], month: oct, state: { firstFrostSeen: false } }, "first-frost");
// NWS API shape
const api = [{ name: "This Afternoon", isDaytime: true, temperature: 71, probabilityOfPrecipitation: { value: 5 }, shortForecast: "Sunny", detailedForecast: "Sunny, with a high near 71.", windSpeed: "5 to 10 mph" },
             { name: "Tonight", isDaytime: false, temperature: 52, probabilityOfPrecipitation: { value: 0 }, shortForecast: "Clear", detailedForecast: "Clear, with a low around 52.", windSpeed: "5 mph" }];
check("NWS API shape", { periods: api, month: oct }, "beautiful");
// pick: deterministic, cycles the whole pool on consecutive days, every sky has entries or a fallback
const a = S.pick(lib, "rain", "2026-10-06"), b = S.pick(lib, "rain", "2026-10-06");
if (a.id !== b.id) { fails++; console.log("FAIL pick not deterministic"); }
const seen = new Set(); for (let d = 1; d <= lib.skies.rain.length; d++) seen.add(S.pick(lib, "rain", `2026-11-${String(d).padStart(2, "0")}`).id);
if (seen.size !== lib.skies.rain.length) { fails++; console.log("FAIL pool not cycled", seen.size); } else console.log("ok   rain pool cycles through all", seen.size);
for (const sky of ["severe","winter-storm","flood","heat","cold","ice","first-snow","snow","first-frost","storm","rain","fog","frost","wind","after-storm","beautiful","clear","gray"]) {
  const e = S.pick(lib, sky, "2026-10-06"); if (!e || !e.kjv || !e.text) { fails++; console.log("FAIL no entry for", sky); }
}
console.log("forecastLine:", S.forecastLine(api));
// Periods that are over (or end within the hour) are skipped (Oct. 7, 2026: the 5:30 AM pick showed
// "Overnight: ... low around 55°", the night that had just ended, because the NWS still listed it).
const snap = [{ name: "Overnight", start: "2026-10-07T05:00:00-04:00", end: "2026-10-07T06:00:00-04:00", isDaytime: false, temperatureF: 55, rainChancePercent: 70, short: "Showers Likely", wind: "W 5 mph" },
              { name: "Wednesday", start: "2026-10-07T06:00:00-04:00", end: "2026-10-07T18:00:00-04:00", isDaytime: true, temperatureF: 73, rainChancePercent: 2, short: "Sunny", wind: "W 10 mph" },
              { name: "Wednesday Night", start: "2026-10-07T18:00:00-04:00", end: "2026-10-08T06:00:00-04:00", isDaytime: false, temperatureF: 53, rainChancePercent: 1, short: "Mostly Clear", wind: "NW 5 mph" }];
const at530 = new Date("2026-10-07T10:30:00Z"), at3am = new Date("2026-10-07T08:00:00Z");
function same(label, got, want) { if (got !== want) { fails++; console.log("FAIL", label, "got", JSON.stringify(got), "want", JSON.stringify(want)); } else console.log("ok  ", label); }
same("5:30 AM line skips the night that ended", S.forecastLine(snap, at530), "Wednesday: Sunny, high near 73°. Wednesday Night: Mostly Clear, low around 53°.");
same("5:30 AM sky ignores the showers that ended", S.classify({ periods: snap, month: oct, now: at530 }).sky, "beautiful");
same("3 AM still reads the night", S.forecastLine(snap, at3am).slice(0, 10), "Overnight:");
same("all over: keeps them rather than nothing", S.upcoming(snap, new Date("2026-10-09T00:00:00Z")).length, 3);
same("no end times: nothing skipped", S.upcoming(api, at530).length, 2);
same("beautiful reason has no repeated high", S.classify({ periods: snap, month: oct, now: at530 }).reason, "Sunny and mild");
console.log(fails ? `${fails} FAILED` : "ALL PASSED");
process.exit(fails ? 1 : 0);
