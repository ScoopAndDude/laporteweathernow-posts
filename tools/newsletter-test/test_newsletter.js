// Local test of tools/newsletter.gs (the Thursday weekend email) with Apps Script stand-ins.
//   node tools/newsletter-test/test_newsletter.js tools/newsletter.gs   (from the repo root; 41 checks, nothing real is called)
const fs = require("fs");
const crypto = require("crypto");
const vm = require("vm");

const SRC = fs.readFileSync(process.argv[2], "utf8");
let fails = 0;
const check = (ok, what) => { console.log(ok ? "PASS" : "FAIL", what); if (!ok) fails++; };

function makeWorld(opts = {}) {
  const props = Object.assign({ NL_LIST_ID: "6", NL_MAILING_ADDRESS: "703 A St., La Porte, IN 46350", BREVO_API_KEY: "x" }, opts.props || {});
  const calls = [], mails = [], logs = [];
  let nextList = 100, nextCampaign = 500;
  const now = new Date();
  const iso = (d) => d.toISOString();
  const rows = opts.rows || [
    ["Signed up", "Email", "Town", "Source", "Status", "Note"],
    ["9/26/2026", "a@example.com", "La Porte", "newsletter (/travel-guides)", "Added + welcomed", ""],
    ["9/28/2026", "b@example.com", "Algeria", "newsletter (/daily-scoop)", "Added + welcomed", ""],
    ["10/4/2026", "c@example.com", "La Porte", "newsletter (/)", "Added + welcomed", ""],
    ["10/5/2026", "d@example.com", "", "newsletter (/daily-scoop#in-scoop)", "Added + welcomed", ""],
    ["11/15/2026", "e@example.com", "30114", "newsletter (/#signup-card)", "Added + welcomed", ""],
  ];
  const contacts = opts.contacts || ["a", "b", "c", "d", "e"].map((x) => ({ email: x + "@example.com", emailBlacklisted: false, listUnsubscribed: [] }));
  const lists = opts.lists || [
    { id: 6, name: "Weekend Outlook" },
    { id: 90, name: "Weekend Outlook · Canton, GA · 2026-11-12" },
    { id: 91, name: "Morning Forecast" },
  ];
  const period = (name, day, t, sf, pop) => ({ name, isDaytime: day, temperature: t, shortForecast: sf, windSpeed: name === "Friday" ? "0 mph" : "5 to 10 mph", probabilityOfPrecipitation: { value: pop } });
  const weekend = (hi) => [period("Tonight", false, hi - 20, "Clear", 0), period("Friday", true, hi, "Mostly Sunny", 0), period("Friday Night", false, hi - 18, "Partly Cloudy", 10),
    period("Saturday", true, hi + 2, "Chance Rain Showers", 40), period("Saturday Night", false, hi - 15, "Rain Showers Likely", 60), period("Sunday", true, hi - 1, "Sunny", 0), period("Sunday Night", false, hi - 19, "Clear", 0)];
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Chicago" }).format(now);
  const fail = opts.fail || {};
  const zippoHits = {};

  function route(url, o) {
    const method = (o && o.method || "get").toLowerCase();
    const body = o && o.payload ? JSON.parse(o.payload) : null;
    calls.push({ method, url, body });
    const ok = (obj, code = 200) => ({ getResponseCode: () => code, getContentText: () => (obj === "" ? "" : JSON.stringify(obj)) });
    if (url.startsWith("https://api.brevo.com/v3")) {
      const path = url.slice("https://api.brevo.com/v3".length);
      if (fail.brevo && fail.brevo(method, path, body)) return ok({ message: "boom" }, 500);
      let m;
      if (method === "get" && (m = /^\/contacts\/lists\/(\d+)\/contacts\?limit=500&offset=(\d+)$/.exec(path))) return ok({ contacts: +m[2] === 0 ? contacts : [] });
      if (method === "get" && /^\/contacts\/lists\/\d+$/.test(path)) return ok({ uniqueSubscribers: contacts.length });
      if (method === "get" && path.startsWith("/contacts/lists?")) return ok({ lists });
      if (method === "get" && path.startsWith("/contacts/folders")) return ok({ folders: [{ id: 1 }] });
      if (method === "post" && path === "/contacts/lists") { const id = nextList++; lists.push({ id, name: body.name }); return ok({ id }, 201); }
      if (method === "post" && /^\/contacts\/lists\/\d+\/contacts\/add$/.test(path)) return ok({ contacts: { success: body.emails } }, 201);
      if (method === "delete" && /^\/contacts\/lists\/\d+$/.test(path)) return ok("", 204);
      if (method === "post" && path === "/emailCampaigns") return ok({ id: nextCampaign++ }, 201);
      if (method === "post" && /^\/emailCampaigns\/\d+\/sendNow$/.test(path)) return ok("", 204);
      if (method === "post" && path === "/smtp/email") return ok({ messageId: "x" }, 201);
      return ok({ message: "unexpected " + method + " " + path }, 400);
    }
    if (url.startsWith("https://api.zippopotam.us")) {
      const path = url.slice("https://api.zippopotam.us".length);
      zippoHits[path] = (zippoHits[path] || 0) + 1;
      if (fail.zippo) return ok({}, 503);
      if (path === "/us/30114") return ok({ "post code": "30114", places: [{ "place name": "Canton", longitude: "-84.4909", latitude: "34.2505", state: "Georgia", "state abbreviation": "GA" }] });
      if (path === "/us/46350") return ok({ "post code": "46350", places: [{ "place name": "La Porte", longitude: "-86.72", latitude: "41.61", state: "Indiana", "state abbreviation": "IN" }] });
      if (path === "/us/in/michigan%20city") return ok({ "state abbreviation": "IN", "place name": "Michigan City", places: [{ "place name": "Michigan City", longitude: "-86.8699", latitude: "41.698", "post code": "46360" }, { "place name": "Michigan City", longitude: "-86.88", latitude: "41.70", "post code": "46361" }] });
      if (path === "/us/ga/canton") return ok({ "state abbreviation": "GA", places: [{ "place name": "Canton", longitude: "-84.49", latitude: "34.24", "post code": "30114" }] });
      return ok({}, 404);
    }
    if (url.startsWith("https://api.weather.gov")) {
      if (fail.nws) return ok({ title: "busy" }, 503);
      if (/\/points\/34\.2505,-84\.4909$/.test(url)) return ok({ properties: { forecast: "https://api.weather.gov/gridpoints/FFC/45,109/forecast", timeZone: "America/New_York" } });
      if (/\/points\/41\.6995,-86\.8749$/.test(url)) return ok({ properties: { forecast: "https://api.weather.gov/gridpoints/IWX/10,60/forecast", timeZone: "America/Chicago" } });
      if (url.endsWith("/gridpoints/FFC/45,109/forecast")) return ok({ properties: { periods: weekend(64) } });
      if (url.endsWith("/gridpoints/IWX/10,60/forecast")) return ok({ properties: { periods: weekend(44) } });
      if (url.includes("/alerts/active?point=34.2505,-84.4909")) return ok({ features: opts.gaAlert ? [{ properties: { event: "Wind Advisory", ends: new Date(now.getTime() + 6 * 36e5).toISOString() } }] : [] });
      if (url.includes("/alerts/active?point=")) return ok({ features: [] });
      return ok({}, 404);
    }
    if (url.startsWith("https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/live/home.json")) {
      return ok({ fetched: iso(new Date(now.getTime() - 10 * 60e3)), alertsChecked: iso(new Date(now.getTime() - 10 * 60e3)), alerts: [], daily: weekend(42) });
    }
    if (url.startsWith("https://scoopanddude.github.io/laporteweathernow-posts/scoop-posts.json")) {
      return ok({ posts: [{ type: "daily", date: today, title: "Cold start, nice finish", summary: "Frost early, then sun.", body: ["Para 1.", "Frost early, then sunny and 42."] }] });
    }
    return ok({}, 404);
  }

  const fmt = (d, tz, pattern) => {
    const p = (o) => new Intl.DateTimeFormat("en-US", Object.assign({ timeZone: tz }, o)).formatToParts(d).reduce((a, x) => (a[x.type] = x.value, a), {});
    if (pattern === "yyyy-MM-dd") return new Intl.DateTimeFormat("en-CA", { timeZone: tz }).format(d);
    if (pattern === "z") return p({ timeZoneName: "short" }).timeZoneName;
    if (pattern === "h:mm a") { const x = p({ hour: "numeric", minute: "2-digit", hour12: true }); return `${x.hour}:${x.minute} ${x.dayPeriod}`; }
    if (pattern === "EEE h:mm a") { const x = p({ weekday: "short", hour: "numeric", minute: "2-digit", hour12: true }); return `${x.weekday} ${x.hour}:${x.minute} ${x.dayPeriod}`; }
    if (pattern === "EEEE, MMMM d") { const x = p({ weekday: "long", month: "long", day: "numeric" }); return `${x.weekday}, ${x.month} ${x.day}`; }
    throw new Error("pattern " + pattern);
  };
  const sandbox = {
    console,
    WA_SHEET_ID: "sheet1",
    Logger: { log: (s) => logs.push(String(s)) },
    PropertiesService: { getScriptProperties: () => ({
      getProperty: (k) => (k in props ? props[k] : null),
      setProperty: (k, v) => { props[k] = String(v); },
      deleteProperty: (k) => { delete props[k]; },
    }) },
    SpreadsheetApp: { openById: () => ({ getSheetByName: () => ({ getDataRange: () => ({ getValues: () => rows }) }) }), getActiveSpreadsheet: () => null },
    UrlFetchApp: { fetch: route },
    MailApp: { sendEmail: (to, subject, body) => mails.push({ to, subject, body }) },
    Utilities: {
      formatDate: fmt,
      DigestAlgorithm: { MD5: "md5" }, Charset: { UTF_8: "utf8" },
      computeDigest: (alg, s) => Array.from(crypto.createHash(alg).update(s, "utf8").digest()).map((b) => (b > 127 ? b - 256 : b)),
      base64EncodeWebSafe: (bytes) => Buffer.from(bytes.map((b) => (b + 256) % 256)).toString("base64").replace(/\+/g, "-").replace(/\//g, "_"),
    },
    ScriptApp: { getProjectTriggers: () => [], newTrigger: () => ({}) },
  };
  vm.createContext(sandbox);
  vm.runInContext(SRC, sandbox);
  return { sb: sandbox, props, calls, mails, logs, lists, zippoHits, today };
}

const brevo = (w, method, re) => w.calls.filter((c) => c.method === method && c.url.startsWith("https://api.brevo.com/v3") && re.test(c.url.slice("https://api.brevo.com/v3".length)));

// 1. Off (as before): one LaPorte campaign to the whole list.
{
  const w = makeWorld();
  w.sb.nlSendWeekly();
  const camps = brevo(w, "post", /^\/emailCampaigns$/);
  check(camps.length === 1 && camps[0].body.recipients.listIds[0] === 6 && /^LaPorte weekend: Chance rain showers Saturday, high near 44$/.test(camps[0].body.subject),
    "off: one campaign to the whole list, \"" + (camps[0] && camps[0].body.subject) + "\"");
  check(w.props.NL_LAST_SENT === w.today && brevo(w, "post", /^\/contacts\/lists$/).length === 0 && !w.calls.some((c) => c.url.includes("zippopotam")), "off: no town lists, no town lookups, marked sent");
  const before = w.calls.length; w.sb.nlSendWeekly();
  check(w.calls.length === before, "off: never twice in a day");
}

// 2. Preview: every town's version to the owner only.
{
  const w = makeWorld();
  w.sb.nlPreview();
  const pv = brevo(w, "post", /^\/smtp\/email$/);
  const subj = pv.map((c) => c.body.subject);
  check(pv.length === 3 && pv.every((c) => c.body.to[0].email === "laporteweathernow@gmail.com"), "preview: 3 versions, all to laporteweathernow@gmail.com only");
  check(subj[0] === "[Preview: LaPorte, IN, 2 readers] LaPorte weekend: Chance rain showers Saturday, high near 44", subj[0]);
  check(subj[1] === "[Preview: town not found, 2 readers] LaPorte weekend: Chance rain showers Saturday, high near 44", subj[1]);
  check(subj[2] === "[Preview: Canton, GA, 1 reader] Canton weekend: Chance rain showers Saturday, high near 66", subj[2]);
  const ga = pv[2].body.htmlContent, unk = pv[1].body.htmlContent, lp = pv[0].body.htmlContent;
  check(/Your Canton weekend/.test(ga) && /forecast for Canton, GA, \d{1,2}:\d\d [AP]M E[SD]T/.test(ga) && /No watches, warnings or advisories for Canton, GA as of \d{1,2}:\d\d [AP]M E[SD]T/.test(ga),
    "Canton: its own forecast, alerts and Eastern times");
  check(/Your town on file is Canton, GA\. Moved\? Reply with your ZIP code\./.test(ga) && /From LaPorte: this morning&#39;s Daily Scoop|From LaPorte: this morning's Daily Scoop/.test(ga) && /emergency\?lat=34\.2505&amp;lon=-84\.4909&amp;name=Canton%2C%20GA/.test(ga),
    "Canton: town-on-file line, LaPorte's Scoop labeled, link to its own alerts page");
  check(/Want your own town&#39;s\? Reply with your ZIP code|Want your own town's\? Reply with your ZIP code/.test(unk) && /Your LaPorte weekend/.test(unk), "town not found: LaPorte's weekend plus the ZIP-code ask");
  check(!/Reply with your ZIP/.test(lp) && /No watches, warnings or advisories for La Porte County as of \d{1,2}:\d\d [AP]M Central/.test(lp) && /This morning's Daily Scoop/.test(lp), "LaPorte readers: as before (Central, La Porte County, the Scoop)");
  check(pv.every((c) => !/\{\{\s*unsubscribe/.test(c.body.htmlContent)), "previews have no live unsubscribe tag");
  check(w.zippoHits["/us/30114"] === 1 && w.zippoHits["/us/in/algeria"] === 1, "looked up 30114 and \"Algeria\" once each");
  w.sb.nlPreview();
  check(w.zippoHits["/us/30114"] === 1 && w.zippoHits["/us/in/algeria"] === 1, "second time: from the saved lookups, no new requests");
}

// 3. On: one campaign per town, each to a short-lived list of just its readers; old lists cleaned up.
{
  const w = makeWorld({ props: { NL_BY_TOWN: "on" } });
  w.sb.nlSendWeekly();
  const made = brevo(w, "post", /^\/contacts\/lists$/).map((c) => c.body.name);
  const adds = brevo(w, "post", /^\/contacts\/lists\/\d+\/contacts\/add$/).map((c) => c.body.emails.join(","));
  const camps = brevo(w, "post", /^\/emailCampaigns$/);
  const sends = brevo(w, "post", /^\/emailCampaigns\/\d+\/sendNow$/);
  check(JSON.stringify(made) === JSON.stringify([
    "Weekend Outlook · LaPorte, IN · " + w.today, "Weekend Outlook · LaPorte (town not found) · " + w.today, "Weekend Outlook · Canton, GA · " + w.today]), "on: 3 town lists " + JSON.stringify(made));
  check(JSON.stringify(adds) === JSON.stringify(["a@example.com,c@example.com", "b@example.com,d@example.com", "e@example.com"]), "on: each list gets just its readers");
  check(camps.length === 3 && sends.length === 3 && camps.every((c, i) => c.body.recipients.listIds[0] === 100 + i) && camps.every((c) => /\{\{ unsubscribe \}\}/.test(c.body.htmlContent)), "on: 3 campaigns sent, each to its own list, Brevo unsubscribe kept");
  const dels = brevo(w, "delete", /^\/contacts\/lists\/\d+$/).map((c) => c.url.split("/").pop());
  check(JSON.stringify(dels) === "[\"90\"]", "on: last week's town list deleted, the real lists left alone");
  check(w.props.NL_LAST_SENT === w.today && !("NL_SENT_" + w.today in w.props) && w.mails.length === 0, "on: marked sent, no problem email");
  const before = w.calls.length; w.sb.nlSendWeekly();
  check(w.calls.length === before, "on: never twice in a day");
}

// 4. Unsubscribed readers are left out.
{
  const w = makeWorld({ props: { NL_BY_TOWN: "on" }, contacts: [
    { email: "a@example.com", emailBlacklisted: false, listUnsubscribed: [] },
    { email: "e@example.com", emailBlacklisted: true, listUnsubscribed: [] },
    { email: "c@example.com", emailBlacklisted: false, listUnsubscribed: [6] },
    { email: "new@example.com", emailBlacklisted: false, listUnsubscribed: [] } ] });
  w.sb.nlSendWeekly();
  const adds = brevo(w, "post", /^\/contacts\/lists\/\d+\/contacts\/add$/).map((c) => c.body.emails.join(","));
  check(JSON.stringify(adds) === JSON.stringify(["a@example.com", "new@example.com"]), "unsubscribed left out; a list member missing from the tab gets the town-not-found version " + JSON.stringify(adds));
}

// 5. A Brevo problem for one town: problem email, the others still go, and a rerun sends only the missed town.
{
  let broken = true;
  const w = makeWorld({ props: { NL_BY_TOWN: "on" }, fail: { brevo: (m, p, b) => broken && m === "post" && p === "/emailCampaigns" && /Canton/.test(b.name) } });
  let threw = false;
  try { w.sb.nlSendWeekly(); } catch (e) { threw = /Canton, GA: Brevo POST \/emailCampaigns answered 500/.test(e.message); }
  check(threw && w.mails.length === 1 && /Weekend email didn't go out/.test(w.mails[0].subject), "one town fails: problem email to the owner");
  check(brevo(w, "post", /^\/emailCampaigns\/\d+\/sendNow$/).length === 2 && !w.props.NL_LAST_SENT, "the other two towns went; not marked sent");
  broken = false;
  const n = brevo(w, "post", /^\/emailCampaigns$/).length;
  w.sb.nlSendWeekly();
  const again = brevo(w, "post", /^\/emailCampaigns$/).slice(n).map((c) => c.body.name);
  check(again.length === 1 && /Canton, GA$/.test(again[0]) && w.props.NL_LAST_SENT === w.today, "rerun: only Canton sent, then marked sent");
}

// 6. Weather Service down for a town: that town gets LaPorte's weekend with a note, not nothing.
{
  const w = makeWorld({ fail: { nws: true } });
  w.sb.nlPreview();
  const ga = brevo(w, "post", /^\/smtp\/email$/)[2].body;
  check(/LaPorte weekend/.test(ga.subject) && /didn&#39;t answer for Canton, GA|didn't answer for Canton, GA/.test(ga.htmlContent), "NWS down: Canton readers get LaPorte's weekend and a note");
}

// 7. Lookup service down: not saved, LaPorte's weekend this time, tried again next time.
{
  const w = makeWorld({ fail: { zippo: true } });
  const g = w.sb.nlGroups_();
  check(g.length === 2 && g[1].fallback && g[1].emails.length === 3 && !Object.keys(w.props).some((k) => k.startsWith("NL_PLACE_")), "lookup down: those readers get LaPorte's weekend; nothing saved, so it's tried again");
}

// 8. Town spellings.
{
  const w = makeWorld();
  const label = (t) => { const p = w.sb.nlPlace_(t); return p ? p.label : null; };
  const cases = [["La Porte", "LaPorte, IN"], ["LaPorte, IN", "LaPorte, IN"], ["la porte indiana", "LaPorte, IN"], ["46350", "LaPorte, IN"],
    ["30114", "Canton, GA"], ["30114-1234", "Canton, GA"], ["Canton GA", "Canton, GA"], ["Michigan City, IN", "Michigan City, IN"], ["michigan city", "Michigan City, IN"],
    ["Algeria", null], ["", null], ["<script>", null]];
  cases.forEach(([t, want]) => check(label(t) === want, `town "${t}" -> ${want}`));
  const mc = w.sb.nlPlace_("Michigan City, IN");
  check(mc.lat === 41.699 && mc.lon === -86.8749, "a town with several ZIPs: their middle point (" + mc.lat + ", " + mc.lon + ")");
}

// 9b. "0 mph" reads as calm.
{
  const w = makeWorld();
  w.sb.nlPreview();
  const lp = brevo(w, "post", /^\/smtp\/email$/)[0].body.htmlContent;
  check(!/Wind 0 mph/.test(lp) && /Wind 5 to 10 mph/.test(lp), "wind: \"0 mph\" never shows as such; real speeds kept");
}

// 9. An alert at a reader's spot shows in their own time zone.
{
  const w = makeWorld({ gaAlert: true });
  w.sb.nlPreview();
  const ga = brevo(w, "post", /^\/smtp\/email$/)[2].body.htmlContent;
  check(/<b>Wind Advisory<\/b> until \w{3} \d{1,2}:\d\d [AP]M E[SD]T/.test(ga), "Canton alert listed with its Eastern end time");
}

console.log(fails ? fails + " FAILED" : "ALL PASS");
process.exit(fails ? 1 : 0);
