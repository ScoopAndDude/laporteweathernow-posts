/*
  The Sky Devotion: picks a short devotion by what the sky is doing (La Porte Weather Now, Oct. 6, 2026).
  One file for every place it runs: the free widget (devotion/index.html), the Faith page on
  laporteweathernow.com, and the daily La Porte job (scripts/sky_devotion.js, which runs it in Node).

  classify({periods, alerts, month, state, now}) -> {sky, reason, alert}
    periods: the National Weather Service forecast periods (the NWS API's own periods, or the morning
             snapshot's); a period that's over or ends within the hour is skipped (so a 5:30 AM pick
             reads today and tonight, not the night that just ended), then the next two are used.
             alerts: names of the NWS alerts in effect ("Tornado Watch"),
    month:   1-12, state: optional {firstFrostSeen, firstSnowSeen, yesterdaySky} (only the La Porte
             job keeps these; without them "first frost/snow" and "after the storm" are never picked).
    now:     optional time to judge "over" by (a Date or milliseconds; the default is right now).
  forecastLine(periods, now) -> "Today: Sunny, high near 73°. Tonight: Clear, low around 52°."
  pick(library, sky, ymd) -> the day's devotion for that sky (the same one for everyone that day).

  Safety first: on days with a Weather Service watch or warning the pick says so, and every place
  that shows a devotion shows the official alert with it. We never issue our own warnings.
*/
(function (root) {
  "use strict";
  var SEVERE = ["Tornado Warning", "Tornado Watch", "Severe Thunderstorm Warning", "Severe Thunderstorm Watch",
    "Extreme Wind Warning", "Severe Weather Statement", "Tornado Emergency", "Particularly Dangerous Situation"];
  var WINTER = ["Winter Storm Warning", "Winter Storm Watch", "Blizzard Warning", "Blizzard Watch", "Ice Storm Warning",
    "Lake Effect Snow Warning", "Lake Effect Snow Watch", "Snow Squall Warning"];
  var FLOOD = ["Flash Flood Warning", "Flash Flood Watch", "Flash Flood Emergency", "Flood Warning", "Flood Watch"];
  var HEAT = ["Excessive Heat Warning", "Excessive Heat Watch", "Extreme Heat Warning", "Extreme Heat Watch", "Heat Advisory"];
  var COLD = ["Extreme Cold Warning", "Extreme Cold Watch", "Wind Chill Warning", "Wind Chill Watch", "Wind Chill Advisory",
    "Cold Weather Advisory"];
  var ICE = ["Freezing Rain Advisory", "Ice Storm Warning"];
  var SNOWY = ["Winter Weather Advisory", "Lake Effect Snow Advisory"];
  var FROST = ["Frost Advisory", "Freeze Warning", "Freeze Watch", "Hard Freeze Warning", "Hard Freeze Watch"];
  var FOG = ["Dense Fog Advisory", "Freezing Fog Advisory"];
  var WIND = ["Wind Advisory", "High Wind Warning", "High Wind Watch", "Lake Wind Advisory"];
  var STORMY = ["storm", "severe", "rain", "flood", "winter-storm", "snow", "ice"];
  var FALLBACK = { "first-snow": "snow", "first-frost": "frost", "after-storm": "clear", "beautiful": "clear" };

  function low(s) { return String(s || "").toLowerCase(); }
  function num(v) { return v === null || v === undefined || v === "" || isNaN(+v) ? null : +v; }

  function normPeriod(p) {
    p = p || {};
    var pop = p.probabilityOfPrecipitation ? p.probabilityOfPrecipitation.value : p.rainChancePercent;
    return {
      name: p.name || "",
      isDaytime: !!p.isDaytime,
      temp: num(p.temperature !== undefined ? p.temperature : p.temperatureF),
      pop: num(pop) || 0,
      short: p.shortForecast || p.short || "",
      detailed: p.detailedForecast || p.detailed || "",
      wind: p.windSpeed || p.wind || "",
      end: Date.parse(p.endTime || p.end || "") || null
    };
  }

  // The periods still ahead: drops any that are over or end within the hour (the NWS sometimes still
  // lists "Overnight" after it ends). If that would leave nothing, keeps them all.
  function upcoming(periods, now) {
    var t = now === undefined || now === null ? Date.now() : +now;
    var all = (periods || []).map(normPeriod);
    var ahead = all.filter(function (p) { return p.end === null || p.end > t + 3600000; });
    return ahead.length ? ahead : all;
  }

  function windMax(p) {
    var nums = (String(p.wind).match(/\d+/g) || []).map(Number);
    var g = low(p.detailed).match(/gusts? (?:as high as |up to |to )?(\d+)/);
    var m = nums.length ? Math.max.apply(null, nums) : 0;
    return { wind: m, gust: g ? +g[1] : 0 };
  }

  function first(list, alerts) {
    for (var i = 0; i < alerts.length; i++) if (list.indexOf(alerts[i]) >= 0) return alerts[i];
    return null;
  }

  function classify(input) {
    input = input || {};
    var periods = upcoming(input.periods, input.now).slice(0, 2);
    var alerts = (input.alerts || []).map(function (a) { return String(a && a.event ? a.event : a); });
    var month = input.month || (new Date().getMonth() + 1);
    var st = input.state || {};
    var day = null, night = null;
    periods.forEach(function (p) { if (p.isDaytime && !day) day = p; if (!p.isDaytime && !night) night = p; });
    var shortText = low(periods.map(function (p) { return p.short; }).join(" | "));
    var allText = low(periods.map(function (p) { return p.short + " " + p.detailed; }).join(" "));
    var maxPop = Math.max.apply(null, [0].concat(periods.map(function (p) { return p.pop; })));
    var high = day ? day.temp : null, lowT = night ? night.temp : null;
    var wind = 0, gust = 0;
    periods.forEach(function (p) { var w = windMax(p); wind = Math.max(wind, w.wind); gust = Math.max(gust, w.gust); });
    var a;
    function out(sky, reason, alert) { return { sky: sky, reason: reason, alert: alert || null }; }

    if ((a = first(SEVERE, alerts))) return out("severe", a + " in effect", a);
    if ((a = first(WINTER, alerts))) return out("winter-storm", a + " in effect", a);
    if ((a = first(FLOOD, alerts))) return out("flood", a + " in effect", a);
    if ((a = first(HEAT, alerts)) || (high !== null && high >= 92))
      return out("heat", a ? a + " in effect" : "A hot day", a);
    if ((a = first(COLD, alerts)) || (high !== null && high <= 20) || (lowT !== null && lowT <= 0))
      return out("cold", a ? a + " in effect" : "Bitter cold", a);
    if ((a = first(ICE, alerts)) || (/freezing rain|freezing drizzle|sleet|ice pellets/.test(allText) && maxPop >= 30))
      return out("ice", a ? a + " in effect" : "Freezing rain or sleet in the forecast", a);
    a = first(SNOWY, alerts);
    if (a || (/snow|flurries/.test(shortText) && maxPop >= 30)) {
      if (st.firstSnowSeen === false && [8, 9, 10, 11, 12, 1].indexOf(month) >= 0)
        return out("first-snow", "The first snow of the season", a);
      return out("snow", a ? a + " in effect" : "Snow in the forecast", a);
    }
    var frostAlert = first(FROST, alerts);
    var frosty = !!frostAlert || (lowT !== null && lowT <= 32 && [3, 4, 5, 6, 8, 9, 10, 11].indexOf(month) >= 0);
    if (frosty && st.firstFrostSeen === false && [8, 9, 10, 11, 12].indexOf(month) >= 0)
      return out("first-frost", "The first frost of the season", frostAlert);
    if (/thunder|t-storm/.test(allText) && maxPop >= 30) return out("storm", "Thunderstorms in the forecast");
    if (/rain|showers|drizzle/.test(shortText) && maxPop >= 40) return out("rain", "Rain in the forecast");
    if (/fog/.test(shortText) || (a = first(FOG, alerts))) return out("fog", a ? a + " in effect" : "Fog", a);
    if (frosty) return out("frost", frostAlert ? frostAlert + " in effect" : "Frost tonight", frostAlert);
    if ((a = first(WIND, alerts)) || wind >= 20 || gust >= 30 || /breezy|windy|blustery/.test(shortText))
      return out("wind", a ? a + " in effect" : "Windy", a);
    var dshort = low(day ? day.short : (night ? night.short : ""));
    var sunny = /sunny|clear|fair/.test(dshort) && !/partly sunny/.test(dshort);
    if (sunny && st.yesterdaySky && STORMY.indexOf(st.yesterdaySky) >= 0 && maxPop < 30)
      return out("after-storm", "Clearing after the storm");
    if (sunny && high !== null && high >= 62 && high <= 82 && wind < 15 && maxPop < 20)
      return out("beautiful", "Sunny and mild");
    if (sunny || /partly cloudy/.test(dshort)) return out("clear", /clear/.test(dshort) ? "Clear skies" : "Sunshine");
    if (/cloud|overcast|partly sunny|gr[ae]y/.test(dshort) || /cloud|overcast|rain|showers|drizzle/.test(shortText))
      return out("gray", "Cloudy");
    return out("clear", "Sunshine");
  }

  function dayNumber(ymd) {
    var p = String(ymd).split("-").map(Number);
    return Math.floor((Date.UTC(p[0], p[1] - 1, p[2]) - Date.UTC(2026, 0, 1)) / 86400000);
  }

  function pick(library, sky, ymd) {
    var s = sky;
    while (s && !(library.skies[s] && library.skies[s].length)) s = FALLBACK[s] || (s === "clear" ? null : "clear");
    var pool = library.skies[s || "clear"];
    var n = ((dayNumber(ymd) % pool.length) + pool.length) % pool.length;
    var id = pool[n];
    for (var i = 0; i < library.entries.length; i++) if (library.entries[i].id === id) return library.entries[i];
    return library.entries[0];
  }

  function forecastLine(periods, now) {
    return upcoming(periods, now).slice(0, 2).map(function (p) {
      var t = p.temp === null ? "" : (p.isDaytime ? ", high near " : ", low around ") + p.temp + "°";
      return p.name + ": " + p.short + t + ".";
    }).join(" ");
  }

  var api = { classify: classify, pick: pick, forecastLine: forecastLine, normPeriod: normPeriod, upcoming: upcoming, dayNumber: dayNumber,
    ALERTS: { severe: SEVERE, winter: WINTER, flood: FLOOD, heat: HEAT, cold: COLD } };
  root.SkyDevotion = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof self !== "undefined" ? self : this);
