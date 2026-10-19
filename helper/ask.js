/*! The "Ask us" website helper by La Porte Weather Now (helper/ask.js, added Oct. 19, 2026).
 *
 * One line on a client's website adds a small "Ask us" button that answers visitors' questions about the business
 * (hours, services, area, how to get a quote) from its own fact sheet in helper/sites.json:
 *
 *   <script src="https://scoopanddude.github.io/laporteweathernow-posts/helper/ask.js" data-site="demo-lawn" defer></script>
 *
 * Options on the same tag: data-color="#1f7a4d" (the button's color; the business's color otherwise),
 * data-open="true" (starts open), data-credit="off" (hides the small "Helper by La Porte Weather Now" line).
 * The answers come from helper/backend.gs (a Google Apps Script web app that holds the Claude key), so no key is
 * ever on the client's site. Everything here is drawn inside its own shadow root, so the site's styles can't bend it,
 * and answers are shown as plain text, never as HTML.
 */
(function () {
  "use strict";
  var ENDPOINT = "https://script.google.com/macros/s/AKfycbyM3iLkhrRaB1G2i_GlfGrJRyrxMwAv6RGtjx5oXuTjBgaSgzCGtD81HtzqaKXM4y5QtA/exec";
  var me = document.currentScript;
  if (!me || window.__lpwnAskHelper) return;
  window.__lpwnAskHelper = true;
  var siteId = String(me.getAttribute("data-site") || "").toLowerCase();
  if (!/^[a-z0-9-]{2,40}$/.test(siteId)) return;
  var base = new URL(".", me.src).href;
  var MAX_Q = 500, HISTORY = 3;

  function onReady(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }

  fetch(base + "sites.json").then(function (r) { return r.json(); }).then(function (sites) {
    var s = sites && Object.prototype.hasOwnProperty.call(sites, siteId) ? sites[siteId] : null;
    if (!s || s.active === false) return;
    onReady(function () { build(s); });
  }).catch(function () { /* no helper today; the page works without it */ });

  function sid() {
    var k = "lpwnAskSid", v = "";
    try { v = sessionStorage.getItem(k) || ""; } catch (e) { v = ""; }
    if (!/^[A-Za-z0-9_-]{8,64}$/.test(v)) {
      var a = new Uint8Array(12);
      (window.crypto || window.msCrypto).getRandomValues(a);
      v = Array.prototype.map.call(a, function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
      try { sessionStorage.setItem(k, v); } catch (e) { /* fine: a new id each page */ }
    }
    return v;
  }

  function safeColor(c) {
    return /^#[0-9a-fA-F]{6}$/.test(String(c || "")) ? c : "";
  }

  function el(tag, attrs, text) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text != null) n.textContent = text;
    return n;
  }

  function digits(p) { return String(p || "").replace(/[^0-9+]/g, ""); }

  function build(s) {
    var color = safeColor(me.getAttribute("data-color")) || safeColor(s.color) || "#1b5fa8";
    var name = String(s.name || "us");
    var host = el("div", { "data-lpwn-ask": "" });
    host.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:2147483000;";
    var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;
    var style = el("style");
    style.textContent = [
      ":host{all:initial}",
      "*{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}",
      ".launch{display:flex;align-items:center;gap:8px;border:0;border-radius:999px;padding:12px 18px 12px 14px;background:var(--c);color:#fff;",
      "font-size:15px;font-weight:700;letter-spacing:.01em;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.22);margin-left:auto}",
      ".launch:hover{filter:brightness(1.08)}.launch:focus-visible,.x:focus-visible,.send:focus-visible,.chip:focus-visible{outline:3px solid #ffbf47;outline-offset:2px}",
      ".launch svg{width:20px;height:20px;flex:none}",
      ".panel{position:absolute;right:0;bottom:62px;width:min(380px,calc(100vw - 32px));height:min(540px,calc(100vh - 100px));display:none;",
      "flex-direction:column;background:#fff;color:#1d2024;border-radius:16px;overflow:hidden;box-shadow:0 18px 50px rgba(0,0,0,.28);border:1px solid #e3e6ea}",
      ".panel.open{display:flex}",
      ".head{background:var(--c);color:#fff;padding:14px 14px 12px 16px;display:flex;align-items:flex-start;gap:10px}",
      ".head b{display:block;font-size:16px;line-height:1.25}.head small{display:block;font-size:12.5px;opacity:.92;margin-top:2px}",
      ".x{margin-left:auto;background:transparent;border:0;color:#fff;font-size:24px;line-height:1;cursor:pointer;padding:0 4px;border-radius:6px}",
      ".sample{background:#fff7e0;color:#6b4b00;font-size:12px;padding:6px 16px;border-bottom:1px solid #f2e2b0}",
      ".log{flex:1;overflow-y:auto;padding:14px 14px 4px;display:flex;flex-direction:column;gap:10px;background:#f6f7f9}",
      ".msg{max-width:86%;padding:9px 12px;border-radius:14px;font-size:14.5px;line-height:1.42;white-space:pre-wrap;word-wrap:break-word}",
      ".bot{background:#fff;border:1px solid #e3e6ea;border-bottom-left-radius:4px;align-self:flex-start}",
      ".you{background:var(--c);color:#fff;border-bottom-right-radius:4px;align-self:flex-end}",
      ".dots{display:inline-flex;gap:4px;align-items:center}.dots i{width:6px;height:6px;border-radius:50%;background:#9aa1a9;animation:b 1s infinite ease-in-out}",
      ".dots i:nth-child(2){animation-delay:.15s}.dots i:nth-child(3){animation-delay:.3s}",
      "@keyframes b{0%,80%,100%{transform:translateY(0);opacity:.5}40%{transform:translateY(-4px);opacity:1}}",
      "@media (prefers-reduced-motion:reduce){.dots i{animation:none}}",
      ".chips{display:flex;flex-wrap:wrap;gap:6px;align-self:flex-start}",
      ".chip{display:inline-block;text-decoration:none;font-size:13px;font-weight:600;color:var(--c);background:#fff;border:1.5px solid var(--c);border-radius:999px;padding:5px 11px}",
      ".chip:hover{background:var(--c);color:#fff}",
      "form{display:flex;gap:8px;padding:10px 12px;border-top:1px solid #e3e6ea;background:#fff}",
      "label.v{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}",
      "input{flex:1;min-width:0;font-size:16px;padding:10px 12px;border:1.5px solid #cfd4da;border-radius:10px;color:#1d2024;background:#fff}",
      "input:focus{outline:none;border-color:var(--c);box-shadow:0 0 0 3px rgba(0,0,0,.06)}",
      ".send{border:0;border-radius:10px;padding:0 14px;background:var(--c);color:#fff;font-weight:700;font-size:14.5px;cursor:pointer}",
      ".send[disabled]{opacity:.55;cursor:default}",
      ".foot{font-size:11.5px;color:#5c636b;padding:0 14px 10px;background:#fff;line-height:1.35}",
      ".foot a{color:#5c636b}",
      "@media (prefers-color-scheme:dark){.panel{background:#1c1e21;color:#eef0f2;border-color:#33373c}.log{background:#141618}",
      ".bot{background:#24272b;border-color:#33373c;color:#eef0f2}form,.foot{background:#1c1e21;border-color:#33373c}",
      "input{background:#141618;color:#eef0f2;border-color:#3b4046}.chip{background:transparent;color:#eef0f2;border-color:#8a9199}.foot,.foot a{color:#a9b0b7}",
      ".sample{background:#3a3220;color:#f3e1b0;border-color:#4a4028}}",
    ].join("");
    root.appendChild(style);
    var wrap = el("div");
    wrap.style.setProperty("--c", color);
    root.appendChild(wrap);

    var panelId = "lpwn-ask-panel";
    var panel = el("div", { "class": "panel", role: "dialog", "aria-label": "Ask " + name, id: panelId });
    var head = el("div", { "class": "head" });
    var title = el("div");
    title.appendChild(el("b", null, "Ask " + name));
    title.appendChild(el("small", null, "Quick answers about our services and hours"));
    var close = el("button", { "class": "x", type: "button", "aria-label": "Close" }, "×");
    head.appendChild(title);
    head.appendChild(close);
    panel.appendChild(head);
    if (s.sample) panel.appendChild(el("div", { "class": "sample" }, "Sample business, made up for this demo."));
    var log = el("div", { "class": "log", role: "log", "aria-live": "polite" });
    panel.appendChild(log);
    var form = el("form");
    var lab = el("label", { "class": "v", "for": "lpwn-ask-q" }, "Your question");
    var input = el("input", { id: "lpwn-ask-q", type: "text", maxlength: String(MAX_Q), autocomplete: "off", placeholder: "Type a question..." });
    var send = el("button", { "class": "send", type: "submit" }, "Send");
    form.appendChild(lab);
    form.appendChild(input);
    form.appendChild(send);
    panel.appendChild(form);
    var foot = el("div", { "class": "foot" });
    foot.appendChild(document.createTextNode("Answers are written by AI from " + name + "'s own info. For anything important, contact them directly."));
    if (me.getAttribute("data-credit") !== "off") {
      foot.appendChild(document.createTextNode(" "));
      var credit = el("a", { href: "https://laporteweathernow.com/", target: "_blank", rel: "noopener" }, "Helper by La Porte Weather Now");
      foot.appendChild(credit);
    }
    panel.appendChild(foot);
    wrap.appendChild(panel);

    var launch = el("button", { "class": "launch", type: "button", "aria-expanded": "false", "aria-controls": panelId });
    launch.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg>';
    launch.appendChild(el("span", null, "Ask us"));
    wrap.appendChild(launch);

    function chips() {
      var box = el("div", { "class": "chips" });
      if (s.phone) box.appendChild(el("a", { "class": "chip", href: "tel:" + digits(s.phone) }, "Call " + s.phone));
      if (s.text) box.appendChild(el("a", { "class": "chip", href: "sms:" + digits(s.text) }, "Text us"));
      if (s.email) box.appendChild(el("a", { "class": "chip", href: "mailto:" + String(s.email) }, "Email"));
      if (/^https:\/\//.test(String(s.quoteUrl || ""))) box.appendChild(el("a", { "class": "chip", href: s.quoteUrl, target: "_blank", rel: "noopener" }, "Get a quote"));
      return box.childNodes.length ? box : null;
    }
    function say(text, who) {
      var m = el("div", { "class": "msg " + (who === "you" ? "you" : "bot") }, text);
      log.appendChild(m);
      log.scrollTop = log.scrollHeight;
      return m;
    }
    function addChips() {
      var c = chips();
      if (c) { log.appendChild(c); log.scrollTop = log.scrollHeight; }
    }
    say(String(s.greeting || ("Hi! Ask me about " + name + ".")), "bot");
    addChips();

    var history = [], busy = false, last = 0;
    function open(yes) {
      panel.classList.toggle("open", yes);
      launch.setAttribute("aria-expanded", yes ? "true" : "false");
      if (yes) setTimeout(function () { input.focus(); }, 30);
      else launch.focus();
    }
    launch.addEventListener("click", function () { open(!panel.classList.contains("open")); });
    close.addEventListener("click", function () { open(false); });
    panel.addEventListener("keydown", function (e) { if (e.key === "Escape") open(false); });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var q = input.value.replace(/\s+/g, " ").trim();
      if (!q || busy) return;
      if (Date.now() - last < 1500) return;
      last = Date.now();
      busy = true;
      send.disabled = true;
      input.value = "";
      say(q, "you");
      var wait = el("div", { "class": "msg bot", "aria-label": "Writing an answer" });
      var dots = el("span", { "class": "dots" });
      dots.appendChild(el("i")); dots.appendChild(el("i")); dots.appendChild(el("i"));
      wait.appendChild(dots);
      log.appendChild(wait);
      log.scrollTop = log.scrollHeight;
      var ctl = window.AbortController ? new AbortController() : null;
      var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 25000);
      fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "text/plain;charset=utf-8" },
        body: JSON.stringify({ site: siteId, q: q.slice(0, MAX_Q), sid: sid(), history: history.slice(-HISTORY) }),
        signal: ctl ? ctl.signal : undefined,
      }).then(function (r) { return r.json(); }).then(function (res) {
        wait.remove();
        var a = String((res && res.answer) || "Sorry, I couldn't answer that. Please contact the business directly.");
        say(a, "bot");
        if (res && res.ok) history.push({ q: q, a: a });
        if (!res || !res.ok || res.contact) addChips();
      }).catch(function () {
        wait.remove();
        say("Sorry, I can't answer right now. Please call, text or email instead.", "bot");
        addChips();
      }).then(function () {
        clearTimeout(timer);
        busy = false;
        send.disabled = false;
        input.focus();
      });
    });

    document.body.appendChild(host);
    if (me.getAttribute("data-open") === "true") open(true);
  }
})();
