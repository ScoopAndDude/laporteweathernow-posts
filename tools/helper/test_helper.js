// Tests for the "Ask us" helper's backend (helper/backend.gs), in Node with stand-ins for Google's services and the
// Claude API (no network). Also checks sites.json's shape.
// Run: node tools/helper/test_helper.js
const fs = require("fs"), vm = require("vm"), path = require("path");
const REPO = path.resolve(__dirname, "..", "..");
const SITES = JSON.parse(fs.readFileSync(path.join(REPO, "helper", "sites.json"), "utf8"));
const ctx = { console: { log() {}, error() {} }, JSON };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(REPO, "helper", "backend.gs"), "utf8"), ctx, { filename: "backend.gs" });
ctx.SITES_TEXT = JSON.stringify(SITES);
vm.runInContext(`
var PROPS = {}, CACHE = {}, CALLS = [], CLAUDE = [], SITES_CODE = 200, SITES_FETCHES = 0;
var NOW = new Date("2026-10-19T23:00:00Z");
Utilities = { formatDate: (d, tz, p) => { const s = new Date(NOW.getTime() - 5 * 3600000).toISOString(); return p === "yyyy-MM-dd" ? s.slice(0, 10) : s; } };
PropertiesService = { getScriptProperties: () => ({ getProperty: (k) => (k in PROPS ? PROPS[k] : null), setProperty: (k, v) => { PROPS[k] = String(v); } }) };
CacheService = { getScriptCache: () => ({ get: (k) => (k in CACHE ? CACHE[k] : null), put: (k, v, s) => { if (s > 21600) throw new Error("too long"); CACHE[k] = v; } }) };
LockService = { getScriptLock: () => ({ tryLock: () => true, releaseLock: () => {} }) };
ContentService = { MimeType: { JSON: "json" }, createTextOutput: (s) => ({ s, setMimeType() { return this; } }) };
UrlFetchApp = { fetch: (u, o) => {
  if (u === ASK_SITES_URL) { SITES_FETCHES++; return { getResponseCode: () => SITES_CODE, getContentText: () => SITES_TEXT }; }
  if (u !== ASK_API) throw new Error("no network: " + u);
  CALLS.push({ headers: o.headers, body: JSON.parse(o.payload) });
  const r = CLAUDE.length ? CLAUDE.shift() : { code: 200, body: reply("We plow driveways in Michigan City, yes. Call or text for a free quote.", true) };
  return { getResponseCode: () => r.code, getContentText: () => (typeof r.body === "string" ? r.body : JSON.stringify(r.body)) };
} };
function reply(answer, contact) { return { content: [{ type: "tool_use", name: "reply", input: { answer, contact } }], usage: { input_tokens: 900, output_tokens: 40 } }; }
var fails = 0, passes = 0;
var check = (name, ok, got) => { if (ok) { passes++; return; } fails++; console.error("FAIL " + name + "\\n  got: " + JSON.stringify(got).slice(0, 800)); };
function setup() { PROPS = { ANTHROPIC_API_KEY: "sk-ant-test" }; CACHE = {}; CALLS = []; CLAUDE = []; SITES_CODE = 200; SITES_FETCHES = 0; }
var ask = (o) => askAnswer(Object.assign({ site: "demo-lawn", q: "Do you plow driveways in Michigan City?", sid: "abcdefgh12345678" }, o || {}));
`, ctx);
ctx.console = console;
const T = (src) => { try { vm.runInContext("{\n" + src + "\n}", ctx); } catch (e) { vm.runInContext("fails++", ctx); console.error("FAIL (section stopped) " + e.message); } };

T(`
setup();
let r = ask();
check("a question gets an answer", r.ok === true && /plow driveways in Michigan City/.test(r.answer) && r.contact === true, r);
const c = CALLS[0];
check("Claude Haiku 5.5 with the key, a strict reply tool, forced", c.headers["x-api-key"] === "sk-ant-test" && c.headers["anthropic-version"] === "2023-06-01" &&
  c.body.model === "claude-haiku-5-5" && c.body.tools[0].strict === true && c.body.tool_choice.name === "reply" && c.body.max_tokens <= 400, c.body);
check("the fact sheet is in the system prompt", /website helper for Lakeside Lawn & Snow/.test(c.body.system) && /Snow plowing and salting/.test(c.body.system) &&
  /Area served: La Porte, Michigan City/.test(c.body.system) && /Q: Are you insured\\?/.test(c.body.system) && /Never make up prices/.test(c.body.system), c.body.system.slice(0, 400));
check("the question is the last message", c.body.messages[c.body.messages.length - 1].content === "Do you plow driveways in Michigan City?", c.body.messages);
check("sites.json was fetched once and kept", SITES_FETCHES === 1 && CACHE["ask:sites"], SITES_FETCHES);
ask(); check("the second question uses the kept copy", SITES_FETCHES === 1, SITES_FETCHES);
const counts = JSON.parse(PROPS.ASK_COUNTS);
check("counted per business and per day", counts.s["demo-lawn"] === 2 && counts.n === 2 && counts.ms["demo-lawn"] === 2 && counts.d === "2026-10-19", counts);
`);

T(`
setup();
CALLS = [];
ask({ q: "And on Saturday?", history: [{ q: "Are you open weekends?", a: "Our office is open Saturday 8 AM to noon." }, { q: "x", a: "" }, "junk"] });
const m = CALLS[0].body.messages;
check("earlier questions go along (bad ones skipped)", m.length === 3 && m[0].role === "user" && m[1].role === "assistant" && /Saturday 8 AM/.test(m[1].content) && m[2].content === "And on Saturday?", m);
setup();
ask({ history: Array.from({ length: 9 }, (_, i) => ({ q: "q" + i, a: "a" + i })) });
check("at most 3 earlier turns", CALLS[0].body.messages.length === 7, CALLS[0].body.messages.length);
`);

T(`
const bad = [["no site", { site: "" }], ["a bad site id", { site: "../etc" }], ["an unknown business", { site: "nobody-here" }], ["the about note isn't a business", { site: "_about" }]];
bad.forEach(([name, o]) => { setup(); const r = ask(o); check(name + ": refused, no Claude", r.ok === false && CALLS.length === 0, r); });
setup(); let r = ask({ q: "   " });
check("an empty question", r.ok === false && CALLS.length === 0, r);
setup(); r = ask({ q: "x".repeat(501) });
check("a question over 500 characters", r.ok === false && /500/.test(r.answer) && CALLS.length === 0, r);
setup(); delete PROPS.ANTHROPIC_API_KEY; r = ask();
check("no key: a polite note to contact them", r.ok === false && r.contact === true && CALLS.length === 0, r);
setup(); SITES_CODE = 404; r = ask();
check("sites.json can't be read: a polite note", r.ok === false && r.contact === true && CALLS.length === 0, r);
setup(); SITES_TEXT = JSON.stringify(Object.assign(JSON.parse(SITES_TEXT), { "demo-lawn": Object.assign({}, JSON.parse(SITES_TEXT)["demo-lawn"], { active: false }) })); r = ask();
check("a business switched off", r.ok === false && CALLS.length === 0, r);
`);
ctx.SITES_TEXT = JSON.stringify(SITES);

T(`
setup();
for (let i = 0; i < 25; i++) ask();
let r = ask();
check("25 questions per visitor, then a note to contact them", r.ok === false && /a lot of questions/.test(r.answer) && CALLS.length === 25, [r, CALLS.length]);
r = ask({ sid: "anothervisitor001" });
check("another visitor still gets answers", r.ok === true, r);
setup();
PROPS.ASK_COUNTS = JSON.stringify({ d: "2026-10-19", n: 5, s: { "demo-lawn": 200 }, m: "2026-10", mn: 5, ms: {} });
r = ask();
check("200 a day for one business", r.ok === false && CALLS.length === 0, r);
setup();
PROPS.ASK_COUNTS = JSON.stringify({ d: "2026-10-19", n: 1000, s: {}, m: "2026-10", mn: 1000, ms: {} });
check("1,000 a day in all", ask().ok === false && CALLS.length === 0, CALLS.length);
setup();
PROPS.ASK_COUNTS = JSON.stringify({ d: "2026-10-18", n: 1000, s: { "demo-lawn": 200 }, m: "2026-10", mn: 1200, ms: { "demo-lawn": 1200 } });
r = ask();
const c = JSON.parse(PROPS.ASK_COUNTS);
check("a new day starts over, the month keeps counting", r.ok === true && c.n === 1 && c.mn === 1201 && c.ms["demo-lawn"] === 1201, c);
`);

T(`
setup();
CLAUDE = [{ code: 200, body: reply("<b>Yes!</b> See https://example.com/x or www.example.com for **more**.", false) }];
let r = ask();
check("tags, links and markdown come out", r.ok && r.answer === "Yes! See or for more.", r.answer);
setup();
CLAUDE = [{ code: 200, body: reply("Yes. ".repeat(200), false) }];
r = ask();
check("a long answer is cut to 600 characters", r.ok && r.answer.length <= 600, r.answer.length);
setup();
CLAUDE = [{ code: 400, body: { error: { message: "Schema is too complex for compilation" } } }, { code: 200, body: reply("Yes, we do.", false) }];
r = ask();
check("a strict schema refused: once more without strict", r.ok && CALLS.length === 2 && CALLS[1].body.tools[0].strict === undefined, CALLS.map((x) => x.body.tools[0]));
setup();
CLAUDE = [{ code: 529, body: { error: { message: "Overloaded" } } }];
r = ask();
check("Claude busy: a polite note to contact them", r.ok === false && r.contact === true, r);
setup();
CLAUDE = [{ code: 200, body: { content: [{ type: "text", text: "hi" }] } }];
r = ask();
check("no reply tool: a polite note", r.ok === false && r.contact === true, r);
setup();
CLAUDE = [{ code: 200, body: "not json" }];
r = ask();
check("not JSON: a polite note", r.ok === false, r);
setup();
const out = doPost({ postData: { contents: "{not json" } });
check("doPost never throws: bad JSON gets a polite JSON answer", /"ok":false/.test(out.s) && /call, text or email/.test(out.s), out);
const ok = doPost({ postData: { contents: JSON.stringify({ site: "demo-lawn", q: "Are you insured?", sid: "abcdefgh12345678" }) } });
check("doPost answers as JSON", JSON.parse(ok.s).ok === true, ok);
check("doGet says it's up", JSON.parse(doGet().s).ok === true, "");
`);

vm.runInContext(`console.log(passes + " passed, " + fails + " failed"); if (!fails) console.log("ALL PASSED");`, ctx);

// sites.json's own shape.
let bad = 0;
Object.entries(SITES).forEach(([id, s]) => {
  if (id.startsWith("_")) return;
  const problems = [];
  if (!/^[a-z0-9-]{2,40}$/.test(id)) problems.push("id");
  ["name", "greeting"].forEach((k) => { if (!s[k] || typeof s[k] !== "string") problems.push(k); });
  ["services", "hours"].forEach((k) => { if (!Array.isArray(s[k]) || !s[k].length) problems.push(k); });
  if (s.color && !/^#[0-9a-fA-F]{6}$/.test(s.color)) problems.push("color");
  if (s.quoteUrl && !/^https:\/\//.test(s.quoteUrl)) problems.push("quoteUrl");
  if (!s.phone && !s.text && !s.email && !s.quoteUrl) problems.push("no way to reach them");
  (s.faqs || []).forEach((f, i) => { if (!f.q || !f.a) problems.push("faq " + i); });
  const all = JSON.stringify(s);
  if (/<|>|javascript:/i.test(all)) problems.push("HTML or scripts in the facts");
  if (problems.length) { bad++; console.error(`FAIL sites.json ${id}: ${problems.join(", ")}`); }
});
if (bad) process.exit(1);
console.log("sites.json: " + Object.keys(SITES).filter((k) => !k.startsWith("_")).length + " business(es) OK");
process.exit(vm.runInContext("fails", ctx) ? 1 : 0);
