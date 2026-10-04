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
 *   - It never sends the weekly email without NL_MAILING_ADDRESS (U.S. law, CAN-SPAM, requires a
 *     real postal address in every marketing email; a P.O. box is fine), and never twice in a day.
 *
 * Set up (about 10 minutes), in laporteweathernow@gmail.com:
 *   1. Open the "Hard Hat Weather sender" project. Click + next to Files > Script, name it
 *      "newsletter", paste this whole file in place of the sample code, and save.
 *   2. Project Settings > Script properties > Add script property:
 *      NL_MAILING_ADDRESS = the business mailing address, on one line.
 *      If the script isn't attached to the Hard Hat Weather Sheet, also NL_SHEET_ID = that Sheet's ID
 *      (the long part of its web address between /d/ and /edit).
 *   3. Pick "nlSetUp" in the function menu and click Run (allow the permissions). It adds the
 *      "Newsletter" tab and the Brevo list, and writes what it did in the execution log.
 *   4. Backfill: paste the emails from Netlify (Forms > newsletter, and weekend-list) into the
 *      Newsletter tab's Email column, one per row (Town and Signed up if you like; leave Status
 *      empty). Run "nlAddPastedRows": each gets added and welcomed, and Status fills in.
 *   5. In the existing doPost, where it handles the other Netlify forms ("disaster-watch" and so on),
 *      add this one line before them, using whatever name doPost gives the parsed Netlify body:
 *          if (nlHandleNetlify(body)) return ContentService.createTextOutput("ok");
 *      Then Deploy > Manage deployments > edit > Version: New version > Deploy (same URL).
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

function nlAddReader_(email, town, source) {
  email = String(email || "").trim();
  var tab = nlTab_();
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var known = tab.getRange(1, 2, Math.max(tab.getLastRow(), 1), 1).getValues()
      .some(function (r) { return String(r[0]).trim().toLowerCase() === email.toLowerCase(); });
    if (known) return;
    var r = nlSubscribe_(email);
    tab.appendRow([new Date(), email, town, source, r.status, r.note]);
  } finally {
    lock.releaseLock();
  }
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
      subject: "You're on the La Porte weekend email",
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

function nlPreview() {
  var issue = nlBuildIssue_();
  nlBrevo_("post", "/smtp/email", {
    sender: NL_SENDER,
    to: [{ email: NL_OWNER }],
    subject: "[Preview] " + issue.subject,
    htmlContent: issue.html.replace(/\{\{\s*unsubscribe\s*\}\}/g, NL_SITE),
  });
  Logger.log("Preview sent to " + NL_OWNER + ": " + issue.subject);
}

function nlSendWeekly() {
  var props = PropertiesService.getScriptProperties();
  var today = Utilities.formatDate(new Date(), NL_TZ, "yyyy-MM-dd");
  if (props.getProperty("NL_LAST_SENT") === today) return;
  try {
    if (!props.getProperty("NL_MAILING_ADDRESS")) throw new Error("add the NL_MAILING_ADDRESS script property");
    var listId = Number(props.getProperty("NL_LIST_ID"));
    if (!listId) throw new Error("run nlSetUp first");
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
  } catch (e) {
    MailApp.sendEmail(NL_OWNER, "Weekend email didn't go out (" + today + ")",
      "The Thursday weekend email failed: " + (e.message || e) +
      "\n\nFix it, then run nlSendWeekly in the Hard Hat Weather sender script to send it today.");
    throw e;
  }
}

function nlBuildIssue_() {
  var home = nlJson_(NL_HOME_JSON);
  var posts = (nlJson_(NL_POSTS_JSON).posts) || [];
  var today = Utilities.formatDate(new Date(), NL_TZ, "yyyy-MM-dd");
  // The first Friday, Saturday and Sunday periods (day and night) in the 7-day forecast.
  var periods = [], seen = {};
  (home.daily || []).forEach(function (p) {
    var m = /^(Friday|Saturday|Sunday)( Night)?$/.exec(p.name || "");
    if (!m || seen[p.name]) return;
    if (m[1] === "Sunday" && !seen.Saturday && !seen["Saturday Night"]) return;
    seen[p.name] = true;
    periods.push(p);
  });
  if (!periods.length) throw new Error("no weekend periods in home.json (fetched " + home.fetched + ")");

  var rows = periods.map(function (p) {
    var pop = p.probabilityOfPrecipitation && p.probabilityOfPrecipitation.value;
    var rain = pop >= 20 ? ", " + pop + "% chance of rain" : "";
    var temp = (p.isDaytime ? "high near " : "low around ") + p.temperature;
    return "<tr><td style=\"padding:6px 10px 6px 0;font-weight:bold;white-space:nowrap;vertical-align:top\">" +
      nlEsc_(p.name) + "</td><td style=\"padding:6px 0\">" + nlEsc_(nlCap_(p.shortForecast)) + ", " + temp +
      nlEsc_(rain) + ". Wind " + nlEsc_(p.windSpeed) + ".</td></tr>";
  }).join("");

  var sat = periods.filter(function (p) { return p.name === "Saturday"; })[0] || periods[0];
  var subject = "La Porte weekend: " + nlCap_(sat.shortForecast) + " " + sat.name + ", " +
    (sat.isDaytime ? "high near " : "low around ") + sat.temperature;

  var ageHours = (Date.now() - new Date(home.fetched).getTime()) / 36e5;
  if (!(ageHours < 3)) throw new Error("the site's weather copy (home.json) is " + Math.round(ageHours) + " hours old");
  var alerts = home.alerts;
  var alertHtml = !Array.isArray(alerts)
    ? "<p style=\"margin:0\">The Weather Service didn't answer our alert check just now, so for watches and warnings " +
      "see <a href=\"" + NL_SITE + "/emergency\">laporteweathernow.com/emergency</a>.</p>"
    : alerts.length
    ? "<ul style=\"margin:0;padding-left:20px\">" + alerts.map(function (a) {
        var ends = a.ends || a.expires;
        return "<li><b>" + nlEsc_(a.event || a.headline || "Alert") + "</b>" +
          (ends ? " until " + nlEsc_(Utilities.formatDate(new Date(ends), NL_TZ, "EEE h:mm a")) + " Central" : "") +
          "</li>";
      }).join("") + "</ul><p style=\"margin:8px 0 0\">Details and what to do: " +
      "<a href=\"" + NL_SITE + "/emergency\">laporteweathernow.com/emergency</a></p>"
    : "<p style=\"margin:0\">No watches, warnings or advisories for La Porte County as of " +
      nlEsc_(Utilities.formatDate(new Date(home.alertsChecked || home.fetched), NL_TZ, "h:mm a")) +
      " Central. If that changes, the latest is always at " +
      "<a href=\"" + NL_SITE + "/emergency\">laporteweathernow.com/emergency</a>.</p>";

  var post = posts.filter(function (p) { return p.type === "daily" && p.date === today; })[0];
  var scoopHtml = "";
  if (post && !post.auto) {
    scoopHtml = "<h2 style=\"font-size:18px;margin:24px 0 8px\">This morning's Daily Scoop</h2>" +
      "<p style=\"margin:0 0 8px\"><b>" + nlEsc_(post.title) + "</b></p>" +
      "<p style=\"margin:0 0 8px\">" + nlEsc_((post.body || []).filter(function (t) { return !/^(Automatic update|Update),/.test(t); })[1] || post.summary || "") + "</p>" +
      "<p style=\"margin:0\"><a href=\"" + NL_SITE + "/daily-scoop\">Read the whole Scoop</a></p>";
  }

  var address = PropertiesService.getScriptProperties().getProperty("NL_MAILING_ADDRESS") ||
    "(mailing address goes here)";
  var html = nlFrame_(
    "<h1 style=\"font-size:22px;margin:0 0 4px\">Your La Porte weekend</h1>" +
    "<p style=\"margin:0 0 16px;color:#555\">" +
    nlEsc_(Utilities.formatDate(new Date(), NL_TZ, "EEEE, MMMM d")) + "</p>" +
    "<h2 style=\"font-size:18px;margin:0 0 8px\">Forecast</h2>" +
    "<table style=\"border-collapse:collapse;font-size:15px\">" + rows + "</table>" +
    "<p style=\"margin:8px 0 0;font-size:13px;color:#555\">From the National Weather Service forecast for La Porte, " +
    nlEsc_(Utilities.formatDate(new Date(home.fetched || new Date()), NL_TZ, "h:mm a")) + " Central. " +
    "The latest: <a href=\"" + NL_SITE + "/weekend\">laporteweathernow.com/weekend</a></p>" +
    "<h2 style=\"font-size:18px;margin:24px 0 8px\">Alerts</h2>" + alertHtml + scoopHtml,
    "We pass along official alerts; we never issue our own warnings. Forecasts from the National Weather Service. " +
    "You're getting this because you signed up for the weekend email at laporteweathernow.com. " +
    "<a href=\"{{ unsubscribe }}\">Unsubscribe</a>.<br>La Porte Weather Now LLC, " + nlEsc_(address)
  );
  var preview = periods.slice(0, 3).map(function (p) { return p.name + ": " + nlCap_(p.shortForecast).toLowerCase(); }).join(". ");
  return { subject: subject, preview: preview, html: html };
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
  // The Hard Hat Weather Sheet: the script's own Sheet, or the NL_SHEET_ID script property.
  var id = PropertiesService.getScriptProperties().getProperty("NL_SHEET_ID");
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
