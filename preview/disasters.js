// World Disaster Watch: current events from GDACS (UN + European Commission) and USGS earthquakes.
// Both feeds are free, need no key, and allow loading from any site.
(function () {
  const GDACS = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP";
  const USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson";
  // Volcanoes: NASA's event tracker (ongoing eruptions worldwide, from the Smithsonian's Global Volcanism Program)
  // and USGS's U.S. volcanoes at an elevated alert level. GDACS rarely lists volcanoes.
  const EONET_VOLCANOES = "https://eonet.gsfc.nasa.gov/api/v3/events?category=volcanoes&status=open";
  const USGS_VOLCANOES = "https://volcanoes.usgs.gov/vsc/api/volcanoApi/elevated";
  // USGS sends these codes in lowercase ("hvo"), so lookups use the uppercase form.
  const OBSERVATORY = { HVO: "Hawaii", AVO: "Alaska", CVO: "Washington and Oregon", CALVO: "California", YVO: "Yellowstone", NMI: "Northern Mariana Islands" };
  const MIN_QUAKE = 5.5;
  const MAX_SHOWN = 120;
  const TYPES = {
    EQ: "Earthquake", TC: "Tropical storm", FL: "Flood", VO: "Volcano", DR: "Drought", WF: "Wildfire",
  };
  const PLURAL = { EQ: "Earthquakes", TC: "Tropical storms", FL: "Floods", VO: "Volcanoes", DR: "Droughts", WF: "Wildfires" };
  const RANK = { red: 0, orange: 1, green: 2 };
  const COLOR = { red: "#c62828", orange: "#d98b00", green: "#2f7d4f" };

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeUrl = (u) => (/^https:\/\/[^\s"'<>]+$/.test(String(u || "")) ? String(u) : "");

  // "maximum wind speed of 287 km/h" -> "peak winds of 178 mph (287 km/h)", for American readers.
  function kmh(s) { const m = /([\d.]+)\s*km\/h/.exec(String(s || "")); return m ? Number(m[1]) : 0; }
  function mph(s) {
    return String(s || "")
      .replace(/Hurricane\/Typhoon\s*>\s*74 mph/i, "Hurricane/typhoon strength")
      .replace(/maximum wind speed of/i, "peak winds of")
      .replace(/([\d.]+)\s*km\/h/g, (m, n) => `${Math.round(Number(n) * 0.621371)} mph / ${Math.round(Number(n))} km/h`);
  }
  // "the Philippines", "the United States" read naturally; plain country names don't take "the".
  const the = (n) => (/^(Philippines|Bahamas|Maldives|Netherlands|Gambia|Comoros|Seychelles|Solomon Islands|Marshall Islands|Cayman Islands|Virgin Islands|United |Republic |Democratic Republic|Central African|Dominican Republic|Czech Republic)/.test(n) ? "the " + n : n);
  function stormName(e) {
    const n = String(e.title).replace(/^(Tropical Cyclone|Tropical Storm|Tropical Depression|Super Typhoon|Typhoon|Hurricane|Cyclone)\s+/i, "").replace(/-\d{2}$/, "")
      .toLowerCase().replace(/(^|[\s-])\S/g, (c) => c.toUpperCase());
    const d = String(e.detail || "");
    const kind = /hurricane|typhoon/i.test(d) ? (e.lat < 0 || (e.lon > 40 && e.lon <= 100) ? "Cyclone" : e.lon > 100 ? "Typhoon" : "Hurricane") : /storm/i.test(d) ? "Tropical Storm" : /depression/i.test(d) ? "Tropical Depression" : "Storm";
    return `${kind} ${n}`;
  }

  function level(s) {
    const v = String(s || "").toLowerCase();
    return v === "red" ? "red" : v === "orange" ? "orange" : "green";
  }

  // GDACS dates have no time zone; they're UTC.
  function gdacsDate(s) {
    if (!s) return null;
    const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : s + "Z");
    return isNaN(d) ? null : d;
  }

  /** Every current GDACS event except green earthquakes (USGS covers quakes, faster and in more detail).
      Green wildfires come too; the list groups them into one card so they don't crowd everything else. */
  function fromGdacs(json) {
    const out = [];
    ((json && json.features) || []).forEach((f) => {
      const p = f.properties || {};
      if (String(p.iscurrent) === "false") return;
      const type = String(p.eventtype || "");
      if (!TYPES[type]) return;
      const lv = level(p.alertlevel);
      if (lv === "green" && type === "EQ") return;
      const c = (f.geometry && f.geometry.type === "Point" && f.geometry.coordinates) || [];
      const sev = (p.severitydata && p.severitydata.severitytext) || "";
      out.push({
        src: "GDACS", type, level: lv,
        title: String(p.name || p.eventname || TYPES[type]).trim(),
        where: String(p.country || "").trim(),
        when: gdacsDate(p.fromdate), until: gdacsDate(p.todate),
        detail: /^Magnitude 0\s*$/i.test(sev.trim()) ? "" : mph(sev.trim()),
        wind: kmh(sev),
        lat: Number(c[1]), lon: Number(c[0]),
        link: safeUrl(p.url && p.url.report) || "https://www.gdacs.org",
        key: "gdacs-" + type + "-" + p.eventid,
      });
    });
    return out;
  }

  /** Ongoing eruptions from NASA EONET ("Telica Volcano, Nicaragua"). */
  function fromEonet(json) {
    return ((json && json.events) || []).filter((e) => !e.closed).map((e) => {
      const t = String(e.title || "Volcano");
      const cut = t.lastIndexOf(",");
      const geo = (e.geometry || []).filter((x) => x && x.type === "Point");
      const first = geo[0], last = geo[geo.length - 1];
      const c = (last && last.coordinates) || [];
      const src = (e.sources || [])[0];
      return {
        src: "NASA / Smithsonian", type: "VO", level: "green",
        title: (cut > 0 ? t.slice(0, cut) : t).trim(), where: cut > 0 ? t.slice(cut + 1).trim() : "",
        when: first && first.date ? new Date(first.date) : null, until: null,
        detail: last && last.date ? "Ongoing eruption; last report " + new Date(last.date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }) : "Ongoing eruption",
        lat: Number(c[1]), lon: Number(c[0]),
        link: safeUrl(src && src.url) || "https://volcano.si.edu/",
        key: "eonet-" + e.id,
      };
    });
  }

  /** U.S. volcanoes at an elevated USGS alert level. Watch/orange shows as orange, warning/red as red. */
  function fromUsgsVolcanoes(json) {
    return (Array.isArray(json) ? json : []).map((v) => {
      const color = String(v.colorCode || "").toUpperCase();
      const alert = String(v.alertLevel || "").toUpperCase();
      const lv = color === "RED" || alert === "WARNING" ? "red" : color === "ORANGE" || alert === "WATCH" ? "orange" : "green";
      const syn = String(v.noticeSynopsis || "").replace(/^.*?\b(RED|ORANGE|YELLOW|GREEN)\/(WARNING|WATCH|ADVISORY|NORMAL)\s*-\s*/i, "").replace(/https?:\S+/g, "").trim();
      return {
        src: "USGS", type: "VO", level: lv,
        title: String(v.vName || "Volcano").trim() + " volcano",
        where: OBSERVATORY[String(v.obs || "").trim().toUpperCase()] || "United States",
        when: v.sentUtc ? new Date(String(v.sentUtc).replace(" ", "T") + (/Z|[+-]\d\d:?\d\d$/.test(String(v.sentUtc)) ? "" : "Z")) : null, until: null,
        detail: `USGS alert level: ${alert.toLowerCase() || "elevated"}${syn ? ". " + syn : ""}`,
        lat: Number(v.lat), lon: Number(v.long),
        link: safeUrl(v.noticeUrl) || "https://volcanoes.usgs.gov/",
        key: "usgsv-" + (v.vnum || v.vName),
        usVolcano: true,
      };
    });
  }

  /** USGS quakes of magnitude 5.5 and up. Their color is the USGS PAGER impact rating when there is one. */
  function fromUsgs(json) {
    const out = [];
    ((json && json.features) || []).forEach((f) => {
      const p = f.properties || {};
      const mag = Number(p.mag);
      if (!(mag >= MIN_QUAKE)) return;
      const c = (f.geometry && f.geometry.coordinates) || [];
      const pager = String(p.alert || "").toLowerCase();
      const notes = [];
      if (c[2] != null && isFinite(c[2])) notes.push(`${Math.round(c[2])} km deep`);
      if (p.tsunami === 1) notes.push("offshore: check tsunami.gov for any tsunami warning");
      if (pager === "yellow") notes.push("USGS impact rating: yellow");
      out.push({
        src: "USGS", type: "EQ", level: pager === "red" ? "red" : pager === "orange" ? "orange" : "green",
        title: `Magnitude ${mag.toFixed(1)} earthquake`,
        where: String(p.place || "").trim(),
        when: p.time ? new Date(p.time) : null, until: null,
        detail: notes.join(", "),
        lat: Number(c[1]), lon: Number(c[0]),
        link: safeUrl(p.url) || "https://earthquake.usgs.gov",
        key: "usgs-" + f.id,
        mag,
      });
    });
    return out;
  }

  function sortEvents(list) {
    return list.slice().sort((a, b) => (RANK[a.level] - RANK[b.level]) || ((b.when ? b.when.getTime() : 0) - (a.when ? a.when.getTime() : 0)));
  }

  function ago(d, now) {
    if (!d) return "";
    const m = Math.round((now - d) / 60000);
    if (m < 1) return "just now";
    if (m < 60) return `${m} min ago`;
    const h = Math.round(m / 60);
    if (h < 36) return `${h} hr ago`;
    const days = Math.round(h / 24);
    return `${days} days ago`;
  }

  function when(e, now) {
    if (!e.when) return "";
    const opts = { month: "short", day: "numeric" };
    const start = e.when.toLocaleDateString("en-US", opts);
    if (e.usVolcano) return `Latest USGS notice: ${start}`;
    if (e.src === "NASA / Smithsonian") return `Erupting since ${e.when.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })}`;
    if (e.type === "EQ") return `${start}, ${e.when.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZoneName: "short" })} (${ago(e.when, now)})`;
    return `Since ${start}`;
  }

  function itemHtml(e, now) {
    const label = { red: "Red alert", orange: "Orange alert", green: "Watching" }[e.level];
    return `<article class="dw-item dw-${e.level}" data-type="${esc(e.type)}">
      <div class="dw-item-top"><span class="pill dw-${e.level}">${label}</span><span class="dw-type">${esc(TYPES[e.type])}</span></div>
      <h3>${esc(e.type === "TC" ? stormName(e) : e.title)}</h3>
      ${e.where ? `<div class="dw-where">${esc(e.where)}</div>` : ""}
      <div class="dw-when">${esc(when(e, now))}${e.detail ? " &middot; " + esc(e.detail) : ""}</div>
      <a class="dw-more" href="${esc(e.link)}" target="_blank" rel="noopener">Official ${esc(e.src)} report &#8599;</a>
      ${e.level !== "green" && e.where && !e.usVolcano ? `<a class="dw-more" style="margin-left:14px;" href="https://reliefweb.int/disasters?search=${encodeURIComponent(e.where)}" target="_blank" rel="noopener">How to help &#8599;</a>` : ""}
    </article>`;
  }

  function bannerFor(list) {
    const reds = list.filter((e) => e.level === "red");
    const oranges = list.filter((e) => e.level === "orange");
    const name = (e) => (e.type === "TC" ? stormName(e) : e.title) + (e.where ? `, ${e.where}` : "");
    if (reds.length) return { cls: "bad", icon: "!", text: `Red alert: ${name(reds[0])}${reds.length > 1 ? ` (and ${reds.length - 1} more)` : ""}` };
    if (oranges.length) return { cls: "warn", icon: "!", text: `No red alerts. ${oranges.length} orange: ${name(oranges[0])}${oranges.length > 1 ? " and more" : ""}` };
    return { cls: "ok", icon: "&#10003;", text: "No red or orange alerts anywhere right now." };
  }

  // Exposed for tests.
  window.lpwnDisasters = { fromGdacs, fromUsgs, fromEonet, fromUsgsVolcanoes, sortEvents, bannerFor, itemHtml, worldReport, stormName, mph };


  // ---------- El Niño watch and the climate cards ----------
  // The numbers live in world-watch.json in the public posts repo on GitHub, refreshed weekly
  // from NOAA, so they change without a Netlify publish. This copy shows if GitHub can't be reached.
  const WATCH_URL = "https://scoopanddude.github.io/laporteweathernow-posts/world-watch.json";
  const WATCH_FALLBACK = {"updated": "2026-09-28", "enso": {"status": "El Niño Advisory", "level": "strong", "headline": "A very strong El Niño is building, and it could be one of the strongest on record.", "reading": "+3.0°C", "readingNote": "above normal in the key Niño-3.4 zone of the Pacific, week of September 16", "points": ["NOAA gives a greater than 90% chance of a very strong El Niño this fall and winter, and a 75% chance it becomes the strongest since records began in 1950.", "Forecasters expect it to last through winter and into spring 2027.", "For La Porte and the Great Lakes: strong El Niño winters usually run warmer than normal across the northern U.S., and the Ohio Valley tends to be drier. That often means less snow here, but not every time, so keep your winter gear ready.", "Around the world, strong El Niños tend to bring heavy rain and flooding to parts of South America and East Africa, and drought to parts of Australia, Indonesia and southern Africa."], "nextUpdate": "2026-10-08", "sources": [{"label": "NOAA ENSO Diagnostic Discussion (Sept 10, 2026)", "url": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml"}, {"label": "IRI El Niño forecast (September 2026)", "url": "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/"}, {"label": "NOAA Climate.gov: El Niño impacts in the U.S.", "url": "https://www.climate.gov/news-features/blogs/enso/united-states-el-nino-impacts-0"}]}, "climate": {"headline": "The climate is warming. Here's what that means, calmly.", "points": [{"fact": "2024 was the warmest year on record so far, and the ten warmest years on record have all come in the last decade.", "doThis": "Heat is the deadliest kind of weather in the U.S. Know the signs of heat illness and check on neighbors during heat waves."}, {"fact": "A warmer atmosphere holds more moisture, so heavy downpours are getting heavier, including in the Midwest.", "doThis": "Know if your home or road floods, keep gutters and storm drains clear, and never drive through water over the road."}, {"fact": "El Niño on top of a warmer baseline makes new global heat records more likely in 2026 and 2027.", "doThis": "Expect more extremes, not just warmer days: have a basic kit ready and more than one way to get warnings."}], "sources": [{"label": "NASA: Global temperature", "url": "https://climate.nasa.gov/vital-signs/global-temperature/"}, {"label": "NOAA: Annual global climate report", "url": "https://www.ncei.noaa.gov/access/monitoring/monthly-report/global/"}, {"label": "WMO: State of the Global Climate", "url": "https://wmo.int/topics/state-of-climate"}, {"label": "Ready.gov: Make a plan", "url": "https://www.ready.gov/plan"}]}};

  function ymdText(ymd) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(ymd || ""));
    if (!m) return "";
    return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], 12)).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" });
  }
  function sourcesHtml(list) {
    const ok = (list || []).filter((s) => safeUrl(s.url));
    return ok.length ? "Sources: " + ok.map((s) => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label)}</a>`).join(" &middot; ") : "";
  }
  function drawWatch(d) {
    if (!d || !d.enso || !$("wwEnso")) return;
    const e = d.enso;
    $("wwEnsoHead").textContent = e.headline || "";
    $("wwEnsoStatus").textContent = e.status || "";
    $("wwEnsoReading").textContent = e.reading || "";
    if ($("gEnso")) $("gEnso").textContent = e.reading || "\u2013";
    $("wwEnsoNote").textContent = e.readingNote || "";
    $("wwEnsoUpdated").textContent = [d.updated ? "Updated " + ymdText(d.updated) : "", e.nextUpdate ? "Next NOAA update " + ymdText(e.nextUpdate) : ""].filter(Boolean).join(". ") + ".";
    $("wwEnsoPoints").innerHTML = (e.points || []).map((p) => `<li>${esc(p)}</li>`).join("");
    $("wwEnsoSources").innerHTML = sourcesHtml(e.sources);
    const c = d.climate || {};
    if (c.headline) $("wwClimateHead").textContent = c.headline;
    $("wwClimate").innerHTML = (c.points || []).map((p) => `<div class="ww-card"><p>${esc(p.fact)}</p>${p.doThis ? `<p class="ww-do"><strong>What you can do:</strong> ${esc(p.doThis)}</p>` : ""}</div>`).join("");
    $("wwClimateSources").innerHTML = sourcesHtml(c.sources);
  }
  window.lpwnDisasters.drawWatch = drawWatch;
  if ($("wwEnso")) {
    drawWatch(WATCH_FALLBACK);
    fetch(WATCH_URL, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).then((d) => {
      if (d && d.enso && (!WATCH_FALLBACK.updated || String(d.updated) >= String(WATCH_FALLBACK.updated))) drawWatch(d);
    }).catch(() => {});
  }

  if (!$("dwList")) return;

  let events = [];
  let filter = "all";
  let map = null;
  let layer = null;
  let mapBase = null;
  let satBase = null;
  let wantSat = false;

  // Satellite map: NASA's newest complete picture of the whole planet (yesterday, UTC). Coastlines and place names
  // appear from zoom 3 in (GIBS sends solid black tiles for them when zoomed all the way out).
  function satelliteLayer() {
    const day = new Date(Date.now() - 864e5).toISOString().slice(0, 10);
    const GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/";
    const credit = '<a href="https://earthdata.nasa.gov/gibs" target="_blank" rel="noopener">NASA GIBS</a>';
    return L.layerGroup([
      L.tileLayer(GIBS + "VIIRS_SNPP_CorrectedReflectance_TrueColor/default/" + day + "/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
        { maxNativeZoom: 9, maxZoom: 8, attribution: "Satellite: " + credit + " (VIIRS, " + day + ")" }),
      L.tileLayer(GIBS + "Reference_Features_15m/default/GoogleMapsCompatible_Level13/{z}/{y}/{x}.png", { minZoom: 3, maxNativeZoom: 13, maxZoom: 8, opacity: 0.7 }),
      L.tileLayer(GIBS + "Reference_Labels_15m/default/GoogleMapsCompatible_Level13/{z}/{y}/{x}.png", { minZoom: 3, maxNativeZoom: 13, maxZoom: 8 })
    ]);
  }
  function useSatellite() {
    wantSat = true;
    if (map && satBase && !map.hasLayer(satBase)) { map.removeLayer(mapBase); satBase.addTo(map); }
  }

  // Newest whole-Earth pictures from NOAA's GOES-East and GOES-West: reload every 10 minutes while the page is open.
  document.querySelectorAll("img[data-goes]").forEach((img) => {
    setInterval(() => { if (!document.hidden) img.src = img.getAttribute("data-goes") + "?t=" + Date.now(); }, 600000);
  });
  if ($("geSat")) $("geSat").addEventListener("click", () => {
    useSatellite();
    if ($("dwMap")) $("dwMap").scrollIntoView({ behavior: "smooth", block: "center" });
    if (typeof lpwnTrack === "function") lpwnTrack("earth-from-space", "satellite-map");
  });

  // Earth from space layers (Oct. 4, 2026): fires NASA's VIIRS cameras spotted in the last 24 hours (NASA FIRMS)
  // and weather satellites placed live from CelesTrak's orbits. Both files come from the posts repository's
  // "space" branch, refreshed every 3 hours; nothing loads until someone turns a layer on.
  const SPACE = "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/space/";
  const SAT_LIB = "https://scoopanddude.github.io/laporteweathernow-posts/preview/satellite.min.js?v=272c249d24";
  let firesLayer = null;
  let satsLayer = null;
  let wantFires = false;
  let wantSats = false;
  const notes = {};
  function setNote(key, text) {
    if (text) notes[key] = text; else delete notes[key];
    const el = $("dwLayerNote");
    if (!el) return;
    const all = ["fires", "sats"].filter((k) => notes[k]).map((k) => notes[k]);
    el.textContent = all.join(" ");
    el.hidden = !all.length;
  }
  const clock = (d) => d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  function agoText(sec) {
    if (sec < 3600) return Math.max(1, Math.round(sec / 60)) + " minutes ago";
    return sec < 5400 ? "about an hour ago" : Math.round(sec / 3600) + " hours ago";
  }
  const num = (n) => Math.round(n).toLocaleString("en-US");

  function firePopup(lat, lon, f) {
    const [frp, n, t, steady] = f;
    const seen = `${n === 1 ? "1 detection" : n + " detections"} in this square (about 7 miles across) in the last 24 hours, newest ${esc(agoText(Date.now() / 1000 - t))}.`;
    const power = `Strength: ${frp >= 10 ? num(frp) : frp.toFixed(1)} MW of fire radiative power.`;
    return (steady
      ? `<strong>Steady heat source</strong><br>This spot has shown heat on 5 or more of the last 7 days, which almost always means a steel mill, refinery, gas flare or volcano, not a wildfire.<br>${seen}<br>${power}<br>`
      : `<strong>Fire spotted from space</strong><br>Usually a wildfire or a field being burned.<br>${seen}<br>${power} Bigger means a bigger, hotter fire.<br>`) +
      `<a href="https://firms.modaps.eosdis.nasa.gov/map/#d:24hrs;@${lon.toFixed(2)},${lat.toFixed(2)},9.00z" target="_blank" rel="noopener">See it on NASA's fire map</a>`;
  }

  // Dots stay small when zoomed out, so a continent with many small fires doesn't look like one big blaze.
  function fireRadius(f, zoom) {
    const [frp, , , steady] = f;
    const r = steady ? 3 : frp > 5 ? Math.min(7, 2 + Math.log10(frp) * 1.6) : 2;
    const k = zoom <= 2 ? 0.35 : zoom <= 3 ? 0.55 : zoom <= 4 ? 0.8 : 1;
    return Math.max(1, r * k);
  }

  function makeFires() {
    const group = L.featureGroup();
    let state = "";
    const resize = () => { const z = map.getZoom(); group.eachLayer((m) => m.options.fire && m.setRadius(fireRadius(m.options.fire, z))); };
    group.on("click", (e) => {
      const f = e.layer && e.layer.options.fire;
      if (f) L.popup().setLatLng(e.latlng).setContent(firePopup(e.layer.getLatLng().lat, e.layer.getLatLng().lng, f)).openOn(map);
    });
    group.on("add", async () => {
      if (state) { if (state === "done") setNote("fires", group.note); return; }
      state = "loading";
      setNote("fires", "Loading fires seen from space…");
      try {
        const d = await getJson(SPACE + "fires.json");
        const list = Array.isArray(d && d.fires) ? d.fires : [];
        const renderer = L.canvas({ pane: "geFires", padding: 0.5 });
        let steadyCount = 0;
        const zoom = map.getZoom();
        // Steady sources first, so fires draw on top of them.
        list.slice().sort((a, b) => (b[5] ? 1 : 0) - (a[5] ? 1 : 0)).forEach((f) => {
          const [lat, lon, frp, n, t, steady] = f;
          if (!isFinite(lat) || !isFinite(lon)) return;
          if (steady) steadyCount++;
          const fire = [Number(frp) || 0, n || 1, t || 0, steady ? 1 : 0];
          L.circleMarker([lat, lon], { renderer, radius: fireRadius(fire, zoom), stroke: false, fillColor: steady ? "#a7b0bd" : "#ff5a1f",
            fillOpacity: steady ? 0.75 : 0.85, fire }).addTo(group);
        });
        const when = d && d.updated ? ", updated " + clock(new Date(d.updated)) : "";
        const fires = list.length - steadyCount;
        const plus = steadyCount ? `, plus ${num(steadyCount)} steady heat sources like steel mills and gas flares (gray)` : "";
        group.note = list.length
          ? `Fires: ${num(fires)} hot spots NASA's satellites spotted in the last 24 hours (orange)${plus}${when}. Tap one for details.`
          : `Fires: NASA's satellites didn't report any fires in the last 24 hours${when}.`;
        state = "done";
        if (map && map.hasLayer(group)) setNote("fires", group.note);
      } catch (err) {
        state = "";
        setNote("fires", "NASA's fire data didn't load just now. Turn the layer off and on to try again.");
      }
    });
    group.on("add", () => { map.on("zoomend", resize); if (state === "done") resize(); });
    group.on("remove", () => { map.off("zoomend", resize); setNote("fires", ""); });
    return group;
  }

  // Weather satellites worth a word, by NORAD catalog number: [short name, what it does, labeled on the map].
  const SAT_INFO = {
    25544: ["Space Station", "The International Space Station. People live and work on board, and it circles Earth every 92 minutes.", true],
    60133: ["GOES-East", "NOAA's weather satellite over the Americas. It took the Americas picture above and watches U.S. storms every few minutes.", true],
    51850: ["GOES-West", "NOAA's weather satellite over the Pacific. It took the Pacific picture above.", true],
    43013: ["NOAA-20", "NOAA's polar-orbiting weather satellite. Its VIIRS camera spots many of the fires on this map and passes over every place on Earth twice a day.", true],
    54234: ["NOAA-21", "NOAA's newest polar-orbiting weather satellite, NOAA-20's twin. Its VIIRS camera spots fires too.", true],
    37849: ["Suomi NPP", "NASA and NOAA's satellite whose VIIRS camera made the satellite map on this page. It spots fires too.", true],
    38771: ["Metop-B", "Europe's polar-orbiting weather satellite. Its measurements go into the computer forecast models.", false],
    43689: ["Metop-C", "Europe's polar-orbiting weather satellite. Its measurements go into the computer forecast models.", false],
    65159: ["Metop-SG A1", "Europe's newest polar-orbiting weather satellite, launched in 2025.", false],
    41836: ["Himawari-9", "Japan's weather satellite over Asia and the western Pacific.", false],
    54743: ["Meteosat-12", "Europe's newest weather satellite, over Europe and Africa.", false],
    43823: ["GK-2A", "South Korea's weather satellite over East Asia.", false],
  };
  const SAT_KIND = [
    [/^CYGFM/, "NASA CYGNSS: one of eight small satellites that measure the winds inside hurricanes."],
    [/^DMSP/, "A U.S. military weather satellite."], [/^(FENGYUN|TIANMU)/, "A Chinese weather satellite."],
    [/^(METEOR|ELEKTRO)/, "A Russian weather satellite."], [/^INSAT/, "An Indian weather satellite."],
    [/^SENTINEL-3/, "A European satellite that watches the oceans, land and fires."],
    [/^(EWS-G|GOES)/, "An older U.S. weather satellite."], [/^(METEOSAT|MTG|METOP)/, "A European weather satellite."],
    [/^HIMAWARI/, "A Japanese weather satellite."], [/^GEO-KOMPSAT/, "A South Korean weather satellite."],
  ];
  function satAbout(s) {
    const info = SAT_INFO[s.id];
    if (info) return info[1];
    const k = SAT_KIND.find(([re]) => re.test(s.name));
    return k ? k[1] : "A weather satellite.";
  }
  function loadScript(src) {
    return new Promise((ok, bad) => {
      if (window.satellite) return ok();
      const el = document.createElement("script");
      el.src = src;
      el.onload = () => ok();
      el.onerror = () => bad(new Error("couldn't load " + src));
      document.head.appendChild(el);
    });
  }
  function satNow(rec, date) {
    const sat = window.satellite;
    const pv = sat.propagate(rec, date);
    if (!pv || !pv.position || typeof pv.position !== "object") return null;
    const g = sat.eciToGeodetic(pv.position, sat.gstime(date));
    const v = pv.velocity && typeof pv.velocity === "object" ? Math.hypot(pv.velocity.x, pv.velocity.y, pv.velocity.z) : 0;
    const lat = sat.degreesLat(g.latitude), lon = sat.degreesLong(g.longitude);
    return isFinite(lat) && isFinite(lon) ? { lat, lon, km: g.height, kms: v } : null;
  }
  function satPopup(s, p) {
    const name = SAT_INFO[s.id] ? SAT_INFO[s.id][0] : s.name;
    const where = p.km > 30000
      ? `Stays over the same spot, about ${num(p.km * 0.621371)} miles above the equator.`
      : `Right now: ${num(p.km * 0.621371)} miles up, moving about ${num(p.kms * 2236.94)} mph.`;
    return `<strong>${esc(name)}</strong>${name !== s.name ? ` <span style="color:#666">(${esc(s.name)})</span>` : ""}<br>${esc(satAbout(s))}<br>${esc(where)}` +
      (p.km < 30000 ? `<br><span style="color:#666">The dashed line is where it goes in the next 100 minutes.</span>` : "");
  }
  // The next 100 minutes of a satellite's path, split where it crosses the date line.
  function satTrack(rec) {
    const segs = [[]];
    const t0 = Date.now();
    let prev = null;
    for (let m = 0; m <= 100; m += 1) {
      const p = satNow(rec, new Date(t0 + m * 60000));
      if (!p) continue;
      if (prev !== null && Math.abs(p.lon - prev) > 180) segs.push([]);
      segs[segs.length - 1].push([p.lat, p.lon]);
      prev = p.lon;
    }
    return segs.filter((s) => s.length > 1);
  }

  function makeSats() {
    const group = L.featureGroup();
    let state = "";
    let sats = [];
    let timer = null;
    let track = null;
    function place() {
      if (document.hidden) return;
      const now = new Date();
      sats.forEach((s) => {
        const p = satNow(s.rec, now);
        if (!p) return;
        s.p = p;
        s.marker.setLatLng([p.lat, p.lon]);
        if (s.marker.isPopupOpen()) s.marker.setPopupContent(satPopup(s, p));
      });
    }
    group.on("add", async () => {
      if (state === "done") { place(); timer = setInterval(place, 2000); setNote("sats", group.note); return; }
      if (state) return;
      state = "loading";
      setNote("sats", "Loading weather satellites…");
      try {
        const [d] = await Promise.all([getJson(SPACE + "satellites.json"), loadScript(SAT_LIB)]);
        const sat = window.satellite;
        const now = new Date();
        sats = (Array.isArray(d && d.sats) ? d.sats : []).map((s) => {
          try { return Object.assign({}, s, { rec: sat.twoline2satrec(s.l1, s.l2) }); } catch (e) { return null; }
        }).filter((s) => s && satNow(s.rec, now));
        sats.sort((a, b) => (SAT_INFO[a.id] ? 1 : 0) - (SAT_INFO[b.id] ? 1 : 0));   // featured ones drawn on top
        sats.forEach((s) => {
          const info = SAT_INFO[s.id];
          const iss = s.id === 25544;
          const p = satNow(s.rec, now);
          s.p = p;
          s.marker = L.circleMarker([p.lat, p.lon], {
            pane: "geSats", radius: iss ? 7 : info ? 6 : 3.5, weight: info ? 2 : 1, color: "#ffffff",
            fillColor: iss ? "#ffd54f" : info ? "#4fc3f7" : "#b9c6d6", fillOpacity: 1,
          }).bindPopup(() => satPopup(s, s.p || p));
          if (info && info[2]) s.marker.bindTooltip(info[0], { permanent: true, direction: "right", offset: [8, 0], className: "ge-sat-label" });
          else s.marker.bindTooltip(info ? info[0] : s.name, { direction: "top", className: "ge-sat-label" });
          s.marker.on("popupopen", () => {
            if (track) { group.removeLayer(track); track = null; }
            if ((s.p || p).km > 30000) return;
            track = L.layerGroup(satTrack(s.rec).map((seg) => L.polyline(seg, { pane: "geSats", color: iss ? "#ffd54f" : "#4fc3f7", weight: 2, dashArray: "6 6", opacity: 0.9, interactive: false })));
            group.addLayer(track);
          });
          s.marker.on("popupclose", () => { if (track) { group.removeLayer(track); track = null; } });
          s.marker.addTo(group);
        });
        const when = d && d.updated ? ` (orbits from CelesTrak, ${clock(new Date(d.updated))})` : "";
        const weather = sats.filter((s) => s.id !== 25544).length;
        const iss = sats.length > weather ? " and the space station" : "";
        group.note = `Satellites: ${weather} weather satellites${iss}, moving live${when}. Tap one to see what it does.`;
        state = "done";
        if (map && map.hasLayer(group)) { setNote("sats", group.note); timer = setInterval(place, 2000); }
      } catch (err) {
        state = "";
        setNote("sats", "The satellite orbits didn't load just now. Turn the layer off and on to try again.");
      }
    });
    group.on("remove", () => {
      if (timer) { clearInterval(timer); timer = null; }
      if (track) { group.removeLayer(track); track = null; }
      setNote("sats", "");
    });
    return group;
  }

  function showLayer(which) {
    useSatellite();
    if (which === "fires") wantFires = true; else wantSats = true;
    const l = which === "fires" ? firesLayer : satsLayer;
    if (map && l && !map.hasLayer(l)) l.addTo(map);
    if ($("dwMap")) $("dwMap").scrollIntoView({ behavior: "smooth", block: "center" });
    if (typeof lpwnTrack === "function") lpwnTrack("earth-from-space", which);
  }
  if ($("geFires")) $("geFires").addEventListener("click", () => showLayer("fires"));
  if ($("geSats")) $("geSats").addEventListener("click", () => showLayer("sats"));

  function drawFilters() {
    const counts = {};
    events.forEach((e) => { counts[e.type] = (counts[e.type] || 0) + 1; });
    const chips = [["all", `All (${events.length})`]].concat(Object.keys(TYPES).filter((t) => counts[t]).map((t) => [t, `${PLURAL[t]} (${counts[t]})`]));
    $("dwFilters").innerHTML = chips.map(([k, label]) => `<button type="button" class="dw-chip" data-f="${k}" aria-pressed="${k === filter}">${esc(label)}</button>`).join("");
  }

  function drawList() {
    const now = new Date();
    const matching = events.filter((e) => filter === "all" || e.type === filter);
    // In "All", the many green wildfires become one summary card; the Wildfires filter lists each one.
    const fires = matching.filter((e) => e.type === "WF" && e.level === "green");
    const cards = (filter === "all" ? matching.filter((e) => !(e.type === "WF" && e.level === "green")) : matching).slice(0, MAX_SHOWN);
    let html = cards.map((e) => itemHtml(e, now)).join("");
    if (filter === "all" && fires.length) html += fireCard(fires);
    $("dwList").innerHTML = html || `<p class="all-clear"><strong>Nothing to show.</strong> No current events of this kind.</p>`;
    drawMap(matching.slice(0, 400));
  }

  function countries(list) {
    const c = {};
    list.forEach((e) => String(e.where || "").split(/,\s*/).filter(Boolean).forEach((w) => { c[w] = (c[w] || 0) + 1; }));
    return Object.entries(c).sort((a, b) => b[1] - a[1]);
  }

  function fireCard(fires) {
    const top = countries(fires);
    return `<article class="dw-item dw-green" data-type="WF">
      <div class="dw-item-top"><span class="pill dw-green">Watching</span><span class="dw-type">Wildfires</span></div>
      <h3>${fires.length} wildfire${fires.length === 1 ? "" : "s"} in ${top.length} ${top.length === 1 ? "country" : "countries"}</h3>
      <div class="dw-when">${esc(top.slice(0, 6).map(([w, n]) => `${w} ${n}`).join(", "))}${top.length > 6 ? ", and more" : ""}</div>
      <button type="button" class="dw-more dw-linkbtn" data-f="WF">See every wildfire &rarr;</button>
    </article>`;
  }

  /** A plain-English summary written from the live data. */
  function worldReport(list, now) {
    const lines = [];
    const reds = list.filter((e) => e.level === "red"), oranges = list.filter((e) => e.level === "orange");
    const nm = (e) => (e.type === "TC" ? stormName(e) : e.title) + (e.where && e.type === "TC" ? ` (${e.where})` : "");
    lines.push(reds.length ? `<strong>${reds.length} red alert${reds.length > 1 ? "s" : ""}:</strong> ${esc(reds.map(nm).join("; "))}.` + (oranges.length ? ` Plus ${oranges.length} orange.` : "")
      : oranges.length ? `<strong>No red alerts.</strong> ${oranges.length} orange: ${esc(oranges.map(nm).join("; "))}.` : "<strong>No red or orange alerts anywhere in the world right now.</strong> Everything below is being watched.");
    const storms = list.filter((e) => e.type === "TC").sort((a, b) => (b.wind || 0) - (a.wind || 0));
    if (storms.length) {
      const top = storms.slice(0, 3).map((e) => `${stormName(e)}${e.where ? " near " + the(e.where) : ""}${e.wind ? ` (peak winds ${Math.round(e.wind * 0.621371)} mph)` : ""}`);
      lines.push(`<strong>${storms.length} tropical storm${storms.length > 1 ? "s" : ""} and hurricane${storms.length > 1 ? "s" : ""}</strong> tracked. Strongest: ${esc(top.join("; "))}.`);
    }
    const quakes = list.filter((e) => e.src === "USGS" && e.type === "EQ").sort((a, b) => (b.mag || 0) - (a.mag || 0));
    if (quakes.length) {
      const q = quakes[0];
      lines.push(`<strong>${quakes.length} earthquake${quakes.length > 1 ? "s" : ""} of magnitude 5.5+</strong> this week. Largest: magnitude ${q.mag.toFixed(1)}, ${esc(q.where)}${q.when ? ` (${q.when.toLocaleDateString("en-US", { month: "short", day: "numeric" })})` : ""}.`);
    } else lines.push("No earthquakes of magnitude 5.5 or more this week.");
    const floods = list.filter((e) => e.type === "FL");
    if (floods.length) {
      const longest = floods.filter((e) => e.when).sort((a, b) => a.when - b.when)[0];
      const days = longest ? Math.round((now - longest.when) / 86400000) : 0;
      lines.push(`<strong>${floods.length} flood${floods.length > 1 ? "s" : ""}:</strong> ${esc(floods.map((e) => e.where || e.title).join(", "))}.${longest && days > 20 ? ` ${esc(longest.where)}'s has gone on for ${days} days.` : ""}`);
    }
    const fires = list.filter((e) => e.type === "WF");
    if (fires.length) {
      const top = countries(fires);
      lines.push(`<strong>${fires.length} wildfire${fires.length > 1 ? "s" : ""}</strong> in ${top.length} ${top.length === 1 ? "country" : "countries"}, most in ${esc(top.slice(0, 3).map(([w, n]) => `${w} (${n})`).join(", "))}.`);
    }
    const vol = list.filter((e) => e.type === "VO"), dr = list.filter((e) => e.type === "DR");
    if (vol.length) {
      const us = vol.filter((e) => e.usVolcano && e.level !== "green");
      lines.push(`<strong>${vol.length} volcano${vol.length > 1 ? "es" : ""}</strong> erupting or restless worldwide.` + (us.length ? ` In the U.S., ${esc(us.map((e) => e.title.replace(/ volcano$/, "") + " (" + e.where + ")").join(" and "))} ${us.length > 1 ? "are" : "is"} at USGS watch level or higher.` : ""));
    }
    if (dr.length) lines.push(`<strong>Drought${dr.length > 1 ? "s" : ""}:</strong> ${esc(dr.map((e) => e.where || e.title).join("; "))}.`);
    return `<ul>${lines.map((l) => `<li>${l}</li>`).join("")}</ul>`;
  }

  function drawMap(shown) {
    if (typeof L === "undefined" || !$("dwMap")) return;
    if (!map) {
      map = L.map("dwMap", { worldCopyJump: true, scrollWheelZoom: false }).setView([20, 0], 2);
      mapBase = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 8, attribution: "&copy; OpenStreetMap contributors" });
      satBase = satelliteLayer();
      (wantSat ? satBase : mapBase).addTo(map);
      map.createPane("geFires").style.zIndex = 390;   // fires under the event dots
      map.createPane("geSats").style.zIndex = 620;    // satellites above them
      firesLayer = makeFires();
      satsLayer = makeSats();
      const small = window.matchMedia && window.matchMedia("(max-width: 600px)").matches;
      L.control.layers({ "Map": mapBase, "Satellite (NASA)": satBase },
        { "Fires seen from space (24 hours)": firesLayer, "Weather satellites (live)": satsLayer },
        { collapsed: small }).addTo(map);
      if (wantFires) firesLayer.addTo(map);
      if (wantSats) satsLayer.addTo(map);
    }
    if (layer) layer.remove();
    layer = L.layerGroup().addTo(map);
    shown.slice().reverse().forEach((e) => {
      if (!isFinite(e.lat) || !isFinite(e.lon)) return;
      L.circleMarker([e.lat, e.lon], { radius: e.level === "red" ? 11 : e.level === "orange" ? 9 : e.type === "WF" ? 4 : 7, color: "#fff", weight: 1.5, fillColor: COLOR[e.level], fillOpacity: 0.9 })
        .bindPopup(`<strong>${esc(e.title)}</strong><br>${esc(e.where)}<br><a href="${esc(e.link)}" target="_blank" rel="noopener">Official report</a>`)
        .addTo(layer);
    });
  }

  async function getJson(url) {
    const ctl = typeof AbortController === "function" ? new AbortController() : null;
    const t = setTimeout(() => ctl && ctl.abort(), 15000);
    try {
      const r = await fetch(url, { signal: ctl ? ctl.signal : undefined, cache: "no-store" });
      if (!r.ok) throw new Error(String(r.status));
      return await r.json();
    } finally {
      clearTimeout(t);
    }
  }

  async function load() {
    const [g, u, ev, uv] = await Promise.allSettled([getJson(GDACS), getJson(USGS), getJson(EONET_VOLCANOES), getJson(USGS_VOLCANOES)]);
    const list = [];
    const missing = [];
    if (g.status === "fulfilled") list.push(...fromGdacs(g.value)); else missing.push("GDACS");
    if (u.status === "fulfilled") list.push(...fromUsgs(u.value)); else missing.push("USGS");
    // Volcanoes: USGS first for U.S. volcanoes, then NASA's list, without listing a volcano twice.
    const volcs = [];
    if (uv.status === "fulfilled") volcs.push(...fromUsgsVolcanoes(uv.value));
    if (ev.status === "fulfilled") volcs.push(...fromEonet(ev.value));
    const vkey = (e) => e.title.toLowerCase().replace(/\s*volcano$/, "");
    const seenV = new Set(list.filter((e) => e.type === "VO").map(vkey));
    volcs.forEach((e) => { if (!seenV.has(vkey(e))) { seenV.add(vkey(e)); list.push(e); } });
    const b = $("dwBanner");
    if (missing.length === 2) {
      b.className = "alert-banner checking";
      $("dwBannerText").textContent = "The alert systems didn't answer just now. We'll try again in a minute; or check GDACS and USGS directly below.";
      if (!events.length) $("dwList").innerHTML = `<p>Couldn't load the live list. Try <a href="https://www.gdacs.org" target="_blank" rel="noopener">GDACS</a> or <a href="https://earthquake.usgs.gov/earthquakes/map/" target="_blank" rel="noopener">USGS</a> directly.</p>`;
      setTimeout(load, 60000);
      return;
    }
    events = sortEvents(list);
    const ban = bannerFor(events);
    b.className = "alert-banner " + ban.cls;
    b.querySelector(".badge-dot").innerHTML = ban.icon;
    $("dwBannerText").textContent = ban.text.replace(/&#?\w+;/g, "");
    drawFilters();
    drawList();
    if ($("dwReport")) {
      $("dwReport").innerHTML = worldReport(events, new Date());
      $("dwReportTime").textContent = "Written automatically from GDACS, USGS and NASA data, " + new Date().toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" }) + ". Updates every 10 minutes.";
    }
    const setStat = (id, v, cls) => { const el = $(id); if (el) { el.textContent = v; el.className = "dw-stat-num" + (cls ? " " + cls : ""); } };
    const reds = events.filter((e) => e.level === "red").length, oranges = events.filter((e) => e.level === "orange").length;
    setStat("gRed", g.status === "fulfilled" ? String(reds) : "?", reds ? "red" : "");
    setStat("gOrange", g.status === "fulfilled" ? String(oranges) : "?", oranges ? "orange" : "");
    setStat("gQuakes", u.status === "fulfilled" ? String(events.filter((e) => e.src === "USGS" && e.type === "EQ").length) : "?");
    $("dwUpdated").textContent = `Updated ${new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}.` +
      (missing.length ? ` ${missing[0]} didn't answer this time, so its events are missing until the next update.` : "");
    setTimeout(load, 10 * 60000);
  }

  $("dwList").addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-f]");
    if (!btn) return;
    filter = btn.dataset.f;
    drawFilters();
    drawList();
    $("dwFilters").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  $("dwFilters").addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-f]");
    if (!btn) return;
    filter = btn.dataset.f;
    drawFilters();
    drawList();
  });

  // Sign-up: the town (optional) is looked up worldwide with Open-Meteo's free place search, and only its
  // rounded spot (about 7 miles) goes along, so we can tell who's near a disaster.
  const signup = $("dwSignup");
  if (signup) signup.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const status = $("dwSignupStatus");
    const btn = signup.querySelector('button[type="submit"]');
    const town = signup.querySelector('[name="town"]').value.trim();
    signup.querySelector('[name="lat"]').value = "";
    signup.querySelector('[name="lon"]').value = "";
    btn.disabled = true;
    try {
      if (town) {
        status.textContent = "Finding " + town + "\u2026";
        const name = town.split(",")[0].trim();
        const hint = town.split(",").slice(1).join(",").trim().toLowerCase();
        const r = await fetch("https://geocoding-api.open-meteo.com/v1/search?count=10&language=en&format=json&name=" + encodeURIComponent(name));
        const j = r.ok ? await r.json() : {};
        const res = (j.results || []);
        const hit = (hint && res.find((x) => [x.country, x.admin1, x.country_code].filter(Boolean).some((v) => String(v).toLowerCase().indexOf(hint) === 0 || hint.indexOf(String(v).toLowerCase()) === 0))) || res[0];
        if (!hit) { status.textContent = `We couldn't find "${town}". Try adding the country, like "Oran, Algeria", or leave the town empty.`; return; }
        signup.querySelector('[name="lat"]').value = Number(hit.latitude).toFixed(1);
        signup.querySelector('[name="lon"]').value = Number(hit.longitude).toFixed(1);
        signup.querySelector('[name="town"]').value = [hit.name, hit.admin1 && hit.admin1 !== hit.name ? hit.admin1 : "", hit.country].filter(Boolean).join(", ");
      }
      const res = await fetch("/", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams(new FormData(signup)).toString() });
      if (!res.ok) throw new Error(String(res.status));
      const where = signup.querySelector('[name="town"]').value;
      signup.reset();
      status.textContent = where ? `You're signed up for red alerts, and alerts near ${where}. Check your email for a welcome note.` : "You're signed up for red alerts. Check your email for a welcome note.";
      if (typeof lpwnTrack === "function") lpwnTrack("world-watch-signup", where ? "with-town" : "no-town");
    } catch (e) {
      status.textContent = "Sorry, that didn't go through. Please try again in a minute.";
    } finally {
      btn.disabled = false;
    }
  });

  // Unsubscribe: the link in every email opens this page with ?stop=<code>.
  const stopForm = $("dwStopForm");
  const code = new URLSearchParams(location.search).get("stop");
  if (code && /^[A-Za-z0-9]{6,20}$/.test(code)) {
    stopForm.querySelector('[name="code"]').value = code;
    $("dwStopBox").open = true;
    $("dwStopStatus").textContent = "Press the button to stop the emails. You can leave the email box empty.";
    setTimeout(() => { const s = $("stop"); if (s) s.scrollIntoView(); }, 300);
  }
  stopForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const email = stopForm.querySelector('[name="email"]').value.trim();
    if (!email && !stopForm.querySelector('[name="code"]').value) {
      $("dwStopStatus").textContent = "Enter the email you signed up with.";
      return;
    }
    const btn = stopForm.querySelector("button");
    btn.disabled = true;
    try {
      const res = await fetch("/", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams(new FormData(stopForm)).toString() });
      if (!res.ok) throw new Error(String(res.status));
      $("dwStopStatus").textContent = "Done. You won't get any more red-alert emails.";
      stopForm.reset();
    } catch (e) {
      $("dwStopStatus").textContent = "Sorry, that didn't go through. Try again in a minute, or email laporteweathernow@gmail.com.";
    } finally {
      btn.disabled = false;
    }
  });

  load();
})();
