/**
 * LPWN timer: a Google Apps Script for laporteweathernow.com (added Sept. 30, 2026).
 *
 * 1. Every 15 minutes it sends a "tick" to GitHub, which starts the website's jobs that are due
 *    (the homepage weather copy, the weather radio, the morning backups, the daily site check).
 *    GitHub's own clock for the repository has been hours late or missing, so this replaces it.
 * 2. Once a day, just after 9 AM Central, it checks that those jobs really ran, and emails this
 *    Google account if one is stuck (at most one email a day). That check works even when GitHub
 *    is having a bad day.
 *
 * Set up (about 5 minutes), in the business Google account:
 *   a. script.google.com > New project, name it "LPWN timer", paste this whole file in place of
 *      the sample code, and save.
 *   b. Project Settings (gear icon) > Script properties > Add script property:
 *      name GITHUB_TOKEN, value = the fine-grained GitHub key for ScoopAndDude/laporteweathernow-posts
 *      with "Contents: Read and write". Paste the key there yourself; never share it anywhere else.
 *   c. Back in the editor, pick "setUp" in the function menu and click Run. Allow the permissions
 *      it asks for (reaching GitHub, sending you email, running on a timer).
 *   d. Optional: Triggers (clock icon) > the "tick" trigger > Failure notification settings >
 *      "Notify me immediately", so an expired key is noticed the same day.
 * When the GitHub key expires, make a new one and replace GITHUB_TOKEN. Nothing else changes.
 */
var REPO = "ScoopAndDude/laporteweathernow-posts";
var RAW = "https://raw.githubusercontent.com/" + REPO + "/";

function tick() {
  var token = PropertiesService.getScriptProperties().getProperty("GITHUB_TOKEN");
  if (!token) throw new Error("Add GITHUB_TOKEN under Project Settings > Script properties.");
  var res = UrlFetchApp.fetch("https://api.github.com/repos/" + REPO + "/dispatches", {
    method: "post",
    contentType: "application/json",
    headers: { Authorization: "Bearer " + token, Accept: "application/vnd.github+json" },
    payload: JSON.stringify({ event_type: "tick" }),
    muteHttpExceptions: true,
  });
  var code = res.getResponseCode();
  if (code !== 204) {
    throw new Error("GitHub answered " + code + ": " + res.getContentText().slice(0, 300) +
      " (the key may have expired: make a new one and replace GITHUB_TOKEN).");
  }
  if (Number(Utilities.formatDate(new Date(), "America/Chicago", "H")) === 9) watchdog();
}

function hoursOld(url, field) {
  try {
    var res = UrlFetchApp.fetch(url + "?t=" + Date.now(), { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) return null;
    var when = JSON.parse(res.getContentText())[field];
    return when ? (Date.now() - new Date(when).getTime()) / 36e5 : null;
  } catch (e) {
    return null;
  }
}

function watchdog() {
  var props = PropertiesService.getScriptProperties();
  var today = Utilities.formatDate(new Date(), "America/Chicago", "yyyy-MM-dd");
  if (props.getProperty("LAST_WATCHDOG") === today) return;
  props.setProperty("LAST_WATCHDOG", today);
  var stuck = [];
  var checks = [
    ["Homepage weather copy", RAW + "live/home.json", "fetched", 3],
    ["Weather radio recording", RAW + "radio/radio.json", "recorded", 4],
    ["Daily site check", RAW + "main/health.json", "checked", 26],
  ];
  checks.forEach(function (c) {
    var h = hoursOld(c[1], c[2]);
    if (h === null) stuck.push(c[0] + ": couldn't read it");
    else if (h > c[3]) stuck.push(c[0] + ": " + h.toFixed(1) + " hours old");
  });
  if (!stuck.length) return;
  MailApp.sendEmail(Session.getEffectiveUser().getEmail(), "La Porte Weather Now: a website job is stuck",
    "The timer is ticking, but these haven't updated:\n\n- " + stuck.join("\n- ") +
    "\n\nSee github.com/" + REPO + "/actions for what happened, or ask Claude to look.\n\n" +
    "(Sent by the LPWN timer Apps Script, at most once a day.)");
}

function setUp() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "tick") ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger("tick").timeBased().everyMinutes(15).create();
  tick();
}
