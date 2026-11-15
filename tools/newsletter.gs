/**
 * La Porte Weather Now: the Thursday weekend email (added Oct. 4, 2026).
 *
 * A second file for the "Hard Hat Weather sender" Apps Script, which already holds BREVO_API_KEY
 * and receives every Netlify form through its web app. Every name here starts with "nl" or "NL_"
 * so nothing clashes with the Hard Hat code.
 *
 * What it does
 *   - Sign-ups (Netlify forms "newsletter" and "weekend-list") go onto a Brevo list called
 *     "Weekend Outlook" and a "Newsletter" tab in the Hard Hat Weather Sheet, and each new reader
 *     gets a short welcome email from alerts@laporteweathernow.com.
 *   - Every Thursday at 3 PM Central it sends the weekend outlook to the list as a Brevo campaign:
 *     the NWS forecast for Friday through Sunday night (from the site's 15-minute copy, home.json),
 *     any La Porte County alerts at send time, and that morning's Daily Scoop. Brevo adds the
 *     one-click unsubscribe and keeps unsubscribed people off every later send.
 *   - Since Nov. 15, 2026 (while the script property NL_BY_TOWN is "on"): each reader gets their own
 *     town's forecast and alerts, from the Town they gave at sign-up (see "the Thursday email" below).
 *   - It never sends the weekly email without NL_MAILING_ADDRESS (U.S. law, CAN-SPAM, requires a
 *     real postal address in every marketing email; a P.O. box is fine), and never twice in a day.
 *
 * Set up, in laporteweathernow@gmail.com (installed Oct. 4, 2026):
 *   1. Open the "Hard Hat Weather sender" project. Click + next to Files > Script, name it
 *      "newsletter", paste this whole file in place of the sample code, and save. It needs no new
 *      permissions: Code.gs already uses MailApp, UrlFetchApp, SpreadsheetApp and ScriptApp.
 *   2. The Newsletter tab goes in the Hard Hat Weather Sheet (WA_SHEET_ID in Code.gs; a
 *      NL_SHEET_ID script property overrides it). Before the weekly send, add the script property
 *      NL_MAILING_ADDRESS = the business mailing address, on one line (Project Settings > Script
 *      properties).
 *   3. Pick "nlSetUp" in the function menu and click Run. It adds the "Newsletter" tab and the
 *      Brevo list, and writes what it did in the execution log.
 *   4. In Code.gs, waSignup (the Netlify forms, called by doPost), right after the bot-field line:
 *          if (nlHandleNetlify(b)) return "newsletter";
 *      Return a plain string there: doPost wraps it in HtmlService. A ContentService reply is a
 *      redirect, which Netlify counts as a failed webhook (it turns the notification off after 6).
 *      Then Deploy > Manage deployments > edit > Version: New version > Deploy (same URL).
 *      Netlify's HTTP POST form notification (the same URL as workday-trial) has to cover the
 *      "newsletter" and "weekend-list" forms too.
 *   5. Backfill: paste the emails from Netlify (Forms > newsletter, and weekend-list) into the
 *      Newsletter tab's Email column, one per row (Town and Signed up if you like; leave Status
 *      empty). Run "nlAddPastedRows": each gets added and welcomed, and Status fills in.
 *      A row whose Status says "Problem" can be retried: clear its Status and run nlAddPastedRows.
 *   6. Run "nlPreview": the email that would go out right now arrives in laporteweathernow@gmail.com
 *      only. When it looks right, run "nlInstallWeekly" (Thursdays, 3 PM Central).
 *      "nlStopWeekly" turns the weekly send off again.
 */

var NL_TAB = "Newsletter";
var NL_HEADERS = ["Signed up", "Email", "Town", "Source", "Status", "Note"];
var NL_LIST_NAME = "Weekend Outlook";
var NL_SENDER = { name: "La Porte Weather Now", email: "alerts@laporteweathernow.com" };
var NL_OWNER = "laporteweathernow@gmail.com";
var NL_FORMS = ["newsletter", "weekend-list"];
var NL_TZ = "America/Chicago";
var NL_SITE = "https://laporteweathernow.com";
var NL_HOME_JSON = "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/live/home.json";
var NL_POSTS_JSON = "https://scoopanddude.github.io/laporteweathernow-posts/scoop-posts.json";

// ---------- set up ----------

function nlSetUp() {
  var tab = nlTab_();
  var props = PropertiesService.getScriptProperties();
  var listId = props.getProperty("NL_LIST_ID");
  if (!listId) {
    var folders = nlBrevo_("get", "/contacts/folders?limit=50&offset=0").folders || [];
    var folderId = folders.length ? folders[0].id
      : nlBrevo_("post", "/contacts/folders", { name: "La Porte Weather Now" }).id;
    var lists = nlBrevo_("get", "/contacts/lists?limit=50&offset=0").lists || [];
    var found = lists.filter(function (l) { return l.name === NL_LIST_NAME; })[0];
    listId = found ? found.id : nlBrevo_("post", "/contacts/lists", { name: NL_LIST_NAME, folderId: folderId }).id;
    props.setProperty("NL_LIST_ID", String(listId));
  }
  Logger.log("Newsletter tab: " + tab.getName() + ". Brevo list \"" + NL_LIST_NAME + "\" id " + listId + ".");
  if (!props.getProperty("NL_MAILING_ADDRESS")) {
    Logger.log("Still needed before the weekly send: script property NL_MAILING_ADDRESS.");
  }
}

function nlInstallWeekly() {
  nlStopWeekly();
  ScriptApp.newTrigger("nlSendWeekly").timeBased().onWeekDay(ScriptApp.WeekDay.THURSDAY)
    .atHour(15).nearMinute(0).inTimezone(NL_TZ).create();
  Logger.log("The weekend email will go out Thursdays around 3 PM Central.");
}

function nlStopWeekly() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "nlSendWeekly") ScriptApp.deleteTrigger(t);
  });
}

// ---------- sign-ups ----------

/** Call from doPost with the parsed Netlify body. Returns true when it was a newsletter form. */
function nlHandleNetlify(body) {
  if (!body) return false;
  var form = body.form_name || (body.payload && body.payload.form_name) || "";
  if (NL_FORMS.indexOf(form) < 0) return false;
  var data = body.data || (body.payload && body.payload.data) || {};
  nlAddReader_(data.email, data.town || "", data.source ? form + " (" + data.source + ")" : form);
  return true;
}

/** Backfill: adds and welcomes every row of the Newsletter tab with an email and no Status. */
function nlAddPastedRows() {
  var tab = nlTab_();
  var rows = tab.getDataRange().getValues();
  var done = 0;
  for (var i = 1; i < rows.length; i++) {
    var email = String(rows[i][1] || "").trim();
    if (!email || String(rows[i][4] || "").trim()) continue;
    var r = nlSubscribe_(email);
    if (!rows[i][0]) tab.getRange(i + 1, 1).setValue(new Date());
    tab.getRange(i + 1, 5, 1, 2).setValues([[r.status, r.note]]);
    done++;
  }
  Logger.log(done + " row(s) handled.");
}

// No lock of its own: doPost already holds the script lock while waSignup runs, the same way
// the World Watch sign-ups work.
function nlAddReader_(email, town, source) {
  email = String(email || "").trim();
  var tab = nlTab_();
  var known = tab.getRange(1, 2, Math.max(tab.getLastRow(), 1), 1).getValues()
    .some(function (r) { return String(r[0]).trim().toLowerCase() === email.toLowerCase(); });
  if (known) return;
  var r = nlSubscribe_(email);
  tab.appendRow([new Date(), email, town, source, r.status, r.note]);
}

function nlSubscribe_(email) {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { status: "Skipped", note: "not an email address" };
  try {
    var listId = Number(PropertiesService.getScriptProperties().getProperty("NL_LIST_ID"));
    if (!listId) throw new Error("run nlSetUp first");
    nlBrevo_("post", "/contacts", { email: email, listIds: [listId], updateEnabled: true });
    nlBrevo_("post", "/smtp/email", {
      sender: NL_SENDER,
      replyTo: { email: NL_OWNER, name: "La Porte Weather Now" },
      to: [{ email: email }],
      subject: "You're on the La Porte weekend email (and here's your free planner)",
      htmlContent: nlWelcomeHtml_(),
    });
    return { status: "Added + welcomed", note: "" };
  } catch (e) {
    return { status: "Problem", note: String(e.message || e).slice(0, 300) };
  }
}

function nlWelcomeHtml_() {
  return nlFrame_(
    "<h1 style=\"font-size:22px;margin:0 0 12px\">Thanks for signing up</h1>" +
    "<p>Every Thursday afternoon you'll get the weekend outlook for La Porte: the National Weather " +
    "Service forecast for Friday through Sunday, any watches or warnings for La Porte County, and that " +
    "morning's Daily Scoop.</p>" +
    // The free planner the sign-up boxes promise (added Oct. 12, 2026).
    "<p><strong>Your free planner:</strong> the <a href=\"" + NL_SITE + "/la-porte-county-winter-storm-planner.pdf\">La Porte " +
    "County Winter Storm Prep Planner</a> (a PDF to print and keep on the fridge), also <a href=\"" + NL_SITE +
    "/la-porte-county-winter-storm-planner-es.pdf\">en español</a>. The <a href=\"" + NL_SITE +
    "/winter-planner?utm_source=welcome-email&amp;utm_campaign=winter-planner\">planner page</a> has a Winter Ready checklist, " +
    "and when a winter weather alert is out for La Porte County, it moves the part you need to the top.</p>" +
    "<p>Between emails, the forecast and official alerts are always at " +
    "<a href=\"" + NL_SITE + "\">laporteweathernow.com</a>, and the Daily Scoop is posted every morning at " +
    "<a href=\"" + NL_SITE + "/daily-scoop\">laporteweathernow.com/daily-scoop</a>.</p>" +
    "<p>Every weekend email has a one-click unsubscribe link at the bottom, or just reply \"stop\" to this one.</p>" +
    "<p>Scoop<br>La Porte Weather Now</p>",
    "You're getting this because this address was signed up for the weekend email at laporteweathernow.com. " +
    "If that wasn't you, reply \"stop\" and we'll take it off."
  );
}

// ---------- the Thursday email ----------
//
// Each reader's own town (Nov. 15, 2026; Scoop said yes to the weekend email using each reader's town).
// The Newsletter tab's Town column (what the sign-up box got: a town, "Town, ST" or a ZIP code) is looked
// up once on Zippopotam.us (free; GeoNames ZIP data) and saved in the Script properties. Readers in
// LaPorte, and anyone whose town can't be placed (left blank, outside the U.S., not found), get LaPorte's
// weekend from the site's own copy (home.json), as before; the second group's email asks for a ZIP code.
// Everyone else gets the Weather Service forecast and alerts for their own spot. Each town gets its own
// Brevo campaign, sent to a short-lived list of just its readers ("Weekend Outlook · <town> · <date>",
// deleted the next week), so Brevo's one-click unsubscribe works as before.
//
// The town-by-town send runs only while the script property NL_BY_TOWN is "on" (nlByTownOn / nlByTownOff);
// otherwise nlSendWeekly sends one LaPorte email to the whole list, as before. nlPreview always sends the
// owner every town's version. A reader who replies with a new town or ZIP code: change their Town cell.

var NL_LAPORTE = { key: "laporte, in", label: "LaPorte, IN", name: "LaPorte", lat: 41.6106, lon: -86.7225, tz: NL_TZ };
var NL_UA = "LaPorteWeatherNow-weekend-email/2.0 (+https://laporteweathernow.com; laporteweathernow@gmail.com)";
var NL_STATES = ("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND " +
  "OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR").split(" ");

function nlByTownOn() {
  PropertiesService.getScriptProperties().setProperty("NL_BY_TOWN", "on");
  Logger.log("Weekend email: each reader's own town (on).");
}

function nlByTownOff() {
  PropertiesService.getScriptProperties().deleteProperty("NL_BY_TOWN");
  Logger.log("Weekend email: one LaPorte email for everyone (town-by-town off).");
}

function nlPreview() {
  var groups = nlGroups_();
  if (!groups.length) groups = [{ key: NL_LAPORTE.key, place: NL_LAPORTE, fallback: false, emails: [] }];
  groups.forEach(function (g) {
    var issue = nlBuildIssue_(g);
    var n = g.emails.length;
    nlBrevo_("post", "/smtp/email", {
      sender: NL_SENDER,
      to: [{ email: NL_OWNER }],
      subject: "[Preview: " + (g.fallback ? "town not found" : g.place.label) + ", " + n + " reader" + (n === 1 ? "" : "s") + "] " + issue.subject,
      htmlContent: issue.html.replace(/\{\{\s*unsubscribe\s*\}\}/g, NL_SITE),
    });
    Logger.log("Preview sent to " + NL_OWNER + " (" + (g.fallback ? "town not found" : g.place.label) + ", " + n + "): " + issue.subject);
  });
}

function nlSendWeekly() {
  var props = PropertiesService.getScriptProperties();
  var today = Utilities.formatDate(new Date(), NL_TZ, "yyyy-MM-dd");
  if (props.getProperty("NL_LAST_SENT") === today) return;
  try {
    if (!props.getProperty("NL_MAILING_ADDRESS")) throw new Error("add the NL_MAILING_ADDRESS script property");
    var listId = Number(props.getProperty("NL_LIST_ID"));
    if (!listId) throw new Error("run nlSetUp first");
    if (props.getProperty("NL_BY_TOWN") === "on") nlSendByTown_(today);
    else nlSendOne_(listId, today);
  } catch (e) {
    MailApp.sendEmail(NL_OWNER, "Weekend email didn't go out (" + today + ")",
      "The Thursday weekend email failed: " + (e.message || e) +
      "\n\nFix it, then run nlSendWeekly in the Hard Hat Weather sender script to send it today" +
      " (towns that already got theirs today are skipped).");
    throw e;
  }
}

// One LaPorte email for the whole list (the way it worked until Nov. 15, 2026).
function nlSendOne_(listId, today) {
  var props = PropertiesService.getScriptProperties();
  var list = nlBrevo_("get", "/contacts/lists/" + listId);
  if (!(list.uniqueSubscribers || list.totalSubscribers)) {
    Logger.log("Nobody on the list yet; nothing sent.");
    return;
  }
  var issue = nlBuildIssue_();
  var campaign = nlBrevo_("post", "/emailCampaigns", {
    name: "Weekend outlook " + today,
    subject: issue.subject,
    previewText: issue.preview,
    sender: NL_SENDER,
    replyTo: NL_OWNER,
    htmlContent: issue.html,
    recipients: { listIds: [listId] },
  });
  nlBrevo_("post", "/emailCampaigns/" + campaign.id + "/sendNow");
  props.setProperty("NL_LAST_SENT", today);
  Logger.log("Sent: " + issue.subject);
}

function nlSendByTown_(today) {
  var props = PropertiesService.getScriptProperties();
  nlCleanUpLists_(today);
  var groups = nlGroups_();
  if (!groups.length) {
    Logger.log("Nobody on the list yet; nothing sent.");
    return;
  }
  var sentKey = "NL_SENT_" + today;   // towns already sent today, so a rerun after a problem skips them
  var sent = JSON.parse(props.getProperty(sentKey) || "[]");
  var folderId = nlFolderId_();
  var problems = [];
  groups.forEach(function (g) {
    var key = g.fallback ? "town not found" : g.key;
    if (sent.indexOf(key) >= 0) return;
    var name = g.fallback ? "LaPorte (town not found)" : g.place.label;
    try {
      var issue = nlBuildIssue_(g);
      var list = nlBrevo_("post", "/contacts/lists", { name: "Weekend Outlook · " + name + " · " + today, folderId: folderId });
      for (var i = 0; i < g.emails.length; i += 150) {
        nlBrevo_("post", "/contacts/lists/" + list.id + "/contacts/add", { emails: g.emails.slice(i, i + 150) });
      }
      var campaign = nlBrevo_("post", "/emailCampaigns", {
        name: "Weekend outlook " + today + " · " + name,
        subject: issue.subject,
        previewText: issue.preview,
        sender: NL_SENDER,
        replyTo: NL_OWNER,
        htmlContent: issue.html,
        recipients: { listIds: [list.id] },
      });
      nlBrevo_("post", "/emailCampaigns/" + campaign.id + "/sendNow");
      sent.push(key);
      props.setProperty(sentKey, JSON.stringify(sent));
      Logger.log("Sent to " + g.emails.length + " (" + name + "): " + issue.subject);
    } catch (e) {
      problems.push(name + ": " + (e.message || e));
    }
  });
  if (problems.length) throw new Error(problems.join("; "));
  props.setProperty("NL_LAST_SENT", today);
  props.deleteProperty(sentKey);
}

// The readers still subscribed (Brevo), grouped by their town (the Newsletter tab).
// -> [{key, place, fallback, emails}]; "fallback" readers couldn't be placed and get LaPorte's weekend.
function nlGroups_() {
  var listId = Number(PropertiesService.getScriptProperties().getProperty("NL_LIST_ID"));
  if (!listId) throw new Error("run nlSetUp first");
  var towns = {};
  nlTab_().getDataRange().getValues().slice(1).forEach(function (r) {
    var email = String(r[1] || "").trim().toLowerCase();
    if (email && !(email in towns)) towns[email] = String(r[2] || "").trim();
  });
  var readers = [];
  for (var offset = 0; ; offset += 500) {
    var cs = nlBrevo_("get", "/contacts/lists/" + listId + "/contacts?limit=500&offset=" + offset).contacts || [];
    cs.forEach(function (c) {
      var off = c.emailBlacklisted || (c.listUnsubscribed || []).indexOf(listId) >= 0;
      var email = String(c.email || "").trim().toLowerCase();
      if (email && !off && readers.indexOf(email) < 0) readers.push(email);
    });
    if (cs.length < 500) break;
  }
  var groups = {}, order = [];
  readers.forEach(function (email) {
    var place = nlPlace_(towns[email] || "");
    var key = place ? place.key : "town not found";
    if (!groups[key]) {
      groups[key] = { key: key, place: place || NL_LAPORTE, fallback: !place, emails: [] };
      order.push(key);
    }
    groups[key].emails.push(email);
  });
  return order.map(function (k) { return groups[k]; });
}

// A reader's town -> {key, label, name, lat, lon}, or null when it can't be placed. Each town is looked
// up once and kept in the Script properties (a town that isn't found is tried again after a week).
function nlPlace_(town) {
  var t = String(town || "").replace(/\s+/g, " ").trim();
  if (!t) return null;
  if (/^la ?porte(\s*,?\s*(in|indiana))?\.?$/i.test(t)) return NL_LAPORTE;
  var props = PropertiesService.getScriptProperties();
  var ck = "NL_PLACE_" + Utilities.base64EncodeWebSafe(
    Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, t.toLowerCase(), Utilities.Charset.UTF_8)).replace(/=+$/, "");
  var hit = props.getProperty(ck);
  if (hit) {
    var c = JSON.parse(hit);
    if (c.place) return c.place;
    if (Date.now() - c.at < 7 * 864e5) return null;
  }
  var place;
  try {
    place = nlLookUp_(t);
  } catch (e) {
    Logger.log("Town lookup didn't work for \"" + t + "\" (" + (e.message || e) + "); LaPorte's weekend this time.");
    return null;   // not saved, so it's tried again next time
  }
  props.setProperty(ck, JSON.stringify(place ? { town: t, place: place } : { town: t, at: Date.now() }));
  return place;
}

function nlLookUp_(t) {
  var m = /^(\d{5})(-\d{4})?$/.exec(t);
  if (m) return nlZippo_("/us/" + m[1]);
  m = /^(.+?)[,\s]+([A-Za-z]{2})\.?$/.exec(t);   // "Michigan City, IN", "Canton GA"
  if (m && NL_STATES.indexOf(m[2].toUpperCase()) >= 0) {
    return nlZippo_("/us/" + m[2].toLowerCase() + "/" + encodeURIComponent(m[1].replace(/,$/, "").trim().toLowerCase()));
  }
  if (!/^[A-Za-z .'-]{2,40}$/.test(t)) return null;
  return nlZippo_("/us/in/" + encodeURIComponent(t.toLowerCase()));   // just a town name: Indiana first
}

function nlZippo_(path) {
  var res = UrlFetchApp.fetch("https://api.zippopotam.us" + path, { muteHttpExceptions: true, headers: { "User-Agent": NL_UA } });
  if (res.getResponseCode() === 404) return null;
  if (res.getResponseCode() !== 200) throw new Error("Zippopotam.us answered " + res.getResponseCode());
  var d = JSON.parse(res.getContentText()), ps = d.places || [];
  if (!ps.length) return null;
  var lat = 0, lon = 0;
  ps.forEach(function (p) { lat += Number(p.latitude); lon += Number(p.longitude); });
  var name = String(ps[0]["place name"] || "").replace(/\b\w/g, function (ch) { return ch.toUpperCase(); });
  var st = ps[0]["state abbreviation"] || d["state abbreviation"] || "";
  var label = name + ", " + st;
  if (/^la ?porte, in$/i.test(label)) return NL_LAPORTE;
  return { key: label.toLowerCase(), label: label, name: name,
    lat: Math.round(lat / ps.length * 1e4) / 1e4, lon: Math.round(lon / ps.length * 1e4) / 1e4 };
}

// The weekend for a place: {periods, alerts (null when the alert check didn't work), fetched, alertsChecked,
// tz, area}. LaPorte comes from the site's own 15-minute copy (home.json), as before; other towns come
// straight from the Weather Service.
function nlWeekend_(place) {
  if (place.key === NL_LAPORTE.key) {
    var home = nlJson_(NL_HOME_JSON);
    var ageHours = (Date.now() - new Date(home.fetched).getTime()) / 36e5;
    if (!(ageHours < 3)) throw new Error("the site's weather copy (home.json) is " + Math.round(ageHours) + " hours old");
    return { periods: home.daily || [], alerts: Array.isArray(home.alerts) ? home.alerts : null,
      fetched: new Date(home.fetched), alertsChecked: new Date(home.alertsChecked || home.fetched), tz: NL_TZ, area: "La Porte County" };
  }
  var pt = nlNws_("https://api.weather.gov/points/" + place.lat + "," + place.lon);
  var fc = nlNws_(pt.properties.forecast);
  var alerts = null;
  try {
    alerts = (nlNws_("https://api.weather.gov/alerts/active?point=" + place.lat + "," + place.lon).features || [])
      .map(function (f) { return f.properties || {}; });
  } catch (e) {
    Logger.log("Alert check didn't work for " + place.label + ": " + (e.message || e));
  }
  return { periods: fc.properties.periods || [], alerts: alerts, fetched: new Date(), alertsChecked: new Date(),
    tz: pt.properties.timeZone || NL_TZ, area: place.label };
}

function nlNws_(url) {
  var res = UrlFetchApp.fetch(url, { muteHttpExceptions: true, headers: { "User-Agent": NL_UA, Accept: "application/geo+json" } });
  if (res.getResponseCode() !== 200) throw new Error(url.replace("https://api.weather.gov", "Weather Service ") + " answered " + res.getResponseCode());
  return JSON.parse(res.getContentText());
}

function nlBuildIssue_(g) {
  g = g || { key: NL_LAPORTE.key, place: NL_LAPORTE, fallback: false, emails: [] };
  var place = g.place, wx, missed = false;
  try {
    wx = nlWeekend_(place);
  } catch (e) {
    if (place.key === NL_LAPORTE.key) throw e;
    Logger.log("Weather for " + place.label + " didn't come (" + (e.message || e) + "); sending LaPorte's.");
    place = NL_LAPORTE;
    wx = nlWeekend_(place);
    missed = true;
  }
  var local = place.key === NL_LAPORTE.key;
  var posts = (nlJson_(NL_POSTS_JSON).posts) || [];
  var today = Utilities.formatDate(new Date(), NL_TZ, "yyyy-MM-dd");
  var zone = function (d) { return local ? "Central" : Utilities.formatDate(d, wx.tz, "z"); };
  // The first Friday, Saturday and Sunday periods (day and night) in the 7-day forecast.
  var periods = [], seen = {};
  wx.periods.forEach(function (p) {
    var m = /^(Friday|Saturday|Sunday)( Night)?$/.exec(p.name || "");
    if (!m || seen[p.name]) return;
    if (m[1] === "Sunday" && !seen.Saturday && !seen["Saturday Night"]) return;
    seen[p.name] = true;
    periods.push(p);
  });
  if (!periods.length) throw new Error("no weekend periods in the forecast for " + place.label);

  var rows = periods.map(function (p) {
    var pop = p.probabilityOfPrecipitation && p.probabilityOfPrecipitation.value;
    var rain = pop >= 20 ? ", " + pop + "% chance of rain" : "";
    var temp = (p.isDaytime ? "high near " : "low around ") + p.temperature;
    return "<tr><td style=\"padding:6px 10px 6px 0;font-weight:bold;white-space:nowrap;vertical-align:top\">" +
      nlEsc_(p.name) + "</td><td style=\"padding:6px 0\">" + nlEsc_(nlCap_(p.shortForecast)) + ", " + temp +
      nlEsc_(rain) + ". Wind " + nlEsc_(/^0 mph$/i.test(p.windSpeed) ? "calm" : p.windSpeed) + ".</td></tr>";
  }).join("");

  var sat = periods.filter(function (p) { return p.name === "Saturday"; })[0] || periods[0];
  var subject = place.name + " weekend: " + nlCap_(sat.shortForecast) + " " + sat.name + ", " +
    (sat.isDaytime ? "high near " : "low around ") + sat.temperature;

  var townPage = local ? NL_SITE + "/emergency"
    : NL_SITE + "/emergency?lat=" + place.lat + "&lon=" + place.lon + "&name=" + encodeURIComponent(place.label);
  var alerts = wx.alerts;
  var alertHtml = !Array.isArray(alerts)
    ? "<p style=\"margin:0\">The Weather Service didn't answer our alert check just now, so for watches and warnings " +
      "see <a href=\"" + nlEsc_(townPage) + "\">" + (local ? "laporteweathernow.com/emergency" : "the alerts for " + nlEsc_(place.label)) + "</a>.</p>"
    : alerts.length
    ? "<ul style=\"margin:0;padding-left:20px\">" + alerts.map(function (a) {
        var ends = a.ends || a.expires;
        return "<li><b>" + nlEsc_(a.event || a.headline || "Alert") + "</b>" +
          (ends ? " until " + nlEsc_(Utilities.formatDate(new Date(ends), wx.tz, "EEE h:mm a")) + " " + nlEsc_(zone(new Date(ends))) : "") +
          "</li>";
      }).join("") + "</ul><p style=\"margin:8px 0 0\">Details and what to do: " +
      "<a href=\"" + nlEsc_(townPage) + "\">" + (local ? "laporteweathernow.com/emergency" : "alerts for " + nlEsc_(place.label)) + "</a></p>"
    : "<p style=\"margin:0\">No watches, warnings or advisories for " + nlEsc_(wx.area) + " as of " +
      nlEsc_(Utilities.formatDate(wx.alertsChecked, wx.tz, "h:mm a")) + " " + nlEsc_(zone(wx.alertsChecked)) +
      ". If that changes, the latest is always at " +
      "<a href=\"" + nlEsc_(townPage) + "\">" + (local ? "laporteweathernow.com/emergency" : "laporteweathernow.com") + "</a>.</p>";

  var post = posts.filter(function (p) { return p.type === "daily" && p.date === today; })[0];
  var scoopHtml = "";
  if (post && !post.auto) {
    scoopHtml = "<h2 style=\"font-size:18px;margin:24px 0 8px\">" + (local ? "This morning's Daily Scoop" : "From LaPorte: this morning's Daily Scoop") + "</h2>" +
      "<p style=\"margin:0 0 8px\"><b>" + nlEsc_(post.title) + "</b></p>" +
      "<p style=\"margin:0 0 8px\">" + nlEsc_((post.body || []).filter(function (t) { return !/^(Automatic update|Update),/.test(t); })[1] || post.summary || "") + "</p>" +
      "<p style=\"margin:0\"><a href=\"" + NL_SITE + "/daily-scoop\">Read the whole Scoop</a></p>";
  }

  // A line for readers whose town we used, couldn't find, or couldn't get the weather for.
  var townNote = g.fallback
    ? "This is LaPorte's weekend. Want your own town's? Reply with your ZIP code and next week's email will be for your town."
    : missed
    ? "The Weather Service didn't answer for " + g.place.label + " just now, so this is LaPorte's weekend. Yours should be back next week."
    : local ? "" : "Your town on file is " + place.label + ". Moved? Reply with your ZIP code.";

  var address = PropertiesService.getScriptProperties().getProperty("NL_MAILING_ADDRESS") ||
    "(mailing address goes here)";
  var html = nlFrame_(
    "<h1 style=\"font-size:22px;margin:0 0 4px\">Your " + nlEsc_(place.name) + " weekend</h1>" +
    "<p style=\"margin:0 0 16px;color:#555\">" +
    nlEsc_(Utilities.formatDate(new Date(), NL_TZ, "EEEE, MMMM d")) + "</p>" +
    (townNote && (g.fallback || missed) ? "<p style=\"margin:0 0 16px;padding:10px 12px;background:#f1f5f9;border-radius:8px\">" + nlEsc_(townNote) + "</p>" : "") +
    "<h2 style=\"font-size:18px;margin:0 0 8px\">Forecast</h2>" +
    "<table style=\"border-collapse:collapse;font-size:15px\">" + rows + "</table>" +
    "<p style=\"margin:8px 0 0;font-size:13px;color:#555\">From the National Weather Service forecast for " + nlEsc_(local ? "La Porte" : place.label) + ", " +
    nlEsc_(Utilities.formatDate(wx.fetched, wx.tz, "h:mm a")) + " " + nlEsc_(zone(wx.fetched)) + ". " +
    (local ? "The latest: <a href=\"" + NL_SITE + "/weekend\">laporteweathernow.com/weekend</a>"
      : "The latest: <a href=\"" + nlEsc_(townPage) + "\">laporteweathernow.com</a>") + "</p>" +
    (townNote && !g.fallback && !missed ? "<p style=\"margin:8px 0 0;font-size:13px;color:#555\">" + nlEsc_(townNote) + "</p>" : "") +
    "<h2 style=\"font-size:18px;margin:24px 0 8px\">Alerts</h2>" + alertHtml + scoopHtml,
    "We pass along official alerts; we never issue our own warnings. Forecasts from the National Weather Service. " +
    "You're getting this because you signed up for the weekend email at laporteweathernow.com. " +
    "<a href=\"{{ unsubscribe }}\">Unsubscribe</a>.<br>La Porte Weather Now LLC, " + nlEsc_(address)
  );
  var preview = periods.slice(0, 3).map(function (p) { return p.name + ": " + nlCap_(p.shortForecast).toLowerCase(); }).join(". ");
  return { subject: subject, preview: preview, html: html };
}

// This script's own short-lived town lists from earlier days ("Weekend Outlook · <town> · <date>").
function nlCleanUpLists_(today) {
  try {
    (nlBrevo_("get", "/contacts/lists?limit=50&offset=0").lists || []).forEach(function (l) {
      var m = /^Weekend Outlook · .+ · (\d{4}-\d{2}-\d{2})$/.exec(l.name || "");
      if (m && m[1] < today) nlBrevo_("delete", "/contacts/lists/" + l.id);
    });
  } catch (e) {
    Logger.log("Last week's town lists weren't cleaned up: " + (e.message || e));
  }
}

function nlFolderId_() {
  var folders = nlBrevo_("get", "/contacts/folders?limit=50&offset=0").folders || [];
  return folders.length ? folders[0].id : nlBrevo_("post", "/contacts/folders", { name: "La Porte Weather Now" }).id;
}

// ---------- helpers ----------

function nlFrame_(inner, footer) {
  return "<!doctype html><html><body style=\"margin:0;background:#f4f6f8\">" +
    "<div style=\"max-width:560px;margin:0 auto;padding:20px 16px;font-family:Arial,Helvetica,sans-serif;" +
    "font-size:15px;line-height:1.5;color:#1d2731;background:#ffffff\">" +
    "<p style=\"margin:0 0 16px;font-weight:bold;color:#1f5f8b\">La Porte Weather Now</p>" + inner +
    "<hr style=\"border:0;border-top:1px solid #dde3e8;margin:24px 0 12px\">" +
    "<p style=\"margin:0;font-size:12px;color:#666\">" + footer + "</p>" +
    "<p style=\"margin:8px 0 0;font-size:12px;color:#666\">Love God. Love people. Tell the truth. Be prepared. Care for all that lives.</p>" +
    "</div></body></html>";
}

function nlTab_() {
  // The Hard Hat Weather Sheet: the NL_SHEET_ID script property if set, otherwise the Sheet the
  // Hard Hat code uses (WA_SHEET_ID in Code.gs), otherwise the script's own Sheet.
  var id = PropertiesService.getScriptProperties().getProperty("NL_SHEET_ID") ||
    (typeof WA_SHEET_ID !== "undefined" ? WA_SHEET_ID : "");
  var ss = id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) throw new Error("add the NL_SHEET_ID script property (the Hard Hat Weather Sheet's ID)");
  var tab = ss.getSheetByName(NL_TAB);
  if (!tab) {
    tab = ss.insertSheet(NL_TAB);
    tab.appendRow(NL_HEADERS);
    tab.setFrozenRows(1);
  }
  return tab;
}

function nlBrevo_(method, path, body) {
  var key = PropertiesService.getScriptProperties().getProperty("BREVO_API_KEY");
  if (!key) throw new Error("BREVO_API_KEY is missing from Script properties");
  var opts = { method: method, headers: { "api-key": key, accept: "application/json" }, muteHttpExceptions: true };
  if (body) {
    opts.contentType = "application/json";
    opts.payload = JSON.stringify(body);
  }
  var res = UrlFetchApp.fetch("https://api.brevo.com/v3" + path, opts);
  var code = res.getResponseCode();
  var text = res.getContentText();
  if (code >= 300) throw new Error("Brevo " + method.toUpperCase() + " " + path + " answered " + code + ": " + text.slice(0, 300));
  return text ? JSON.parse(text) : {};
}

function nlJson_(url) {
  var res = UrlFetchApp.fetch(url + "?t=" + Date.now(), { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) throw new Error(url + " answered " + res.getResponseCode());
  return JSON.parse(res.getContentText());
}

/** "Mostly Sunny" -> "Mostly sunny" (NWS capitalizes every word). */
function nlCap_(s) {
  s = String(s || "").toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function nlEsc_(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
