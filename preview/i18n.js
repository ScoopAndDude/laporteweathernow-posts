/* La Porte Weather Now: the language switch (added September 28, 2026).
 *
 * English is the site's own text. Other languages are translated in the visitor's browser
 * from a phrasebook in /lang/<code>.js: exact phrases, plus patterns for the live Weather
 * Service wording (days, times, conditions, alerts). Anything a phrasebook doesn't know
 * stays in English, so a missing phrase can never break a page or hide information.
 *
 * With English picked (the default), this script only adds the language menu.
 * A phrasebook lists the pages it covers completely by hand. With `fill` (Darja: "ar"), every
 * page is still translated in full: the phrasebook first, then Google Translate fills in
 * whatever it doesn't know, in that Google language (Sept. 30, 2026). Without `fill`, other
 * pages would get only a translated menu and footer plus a note that the page is in English.
 *
 * Links: add ?lang=ar-DZ to any address for Darja, ?lang=en for English. The choice is
 * remembered on the device. A tiny script at the top of each page hides the page for a
 * moment while a phrasebook loads, so nobody sees it flip from English (at most 3 seconds).
 *
 * Every other language (about 110) is translated automatically by Google Translate's website
 * tool, which only loads for visitors who pick one of those languages (?lang=es, ?lang=fr ...).
 * Darja has its own hand-written phrasebook because Google doesn't offer Darja.
 *
 * To add a hand-written language: add it to LANGS below, write /lang/<code>.js (copy
 * ar-dz.js), and add the phrasebook to _headers.
 */
(function () {
  "use strict";

  var LANGS = [
    { code: "en", name: "English", short: "EN", dir: "ltr" },
    { code: "ar-DZ", name: "الدارجة", short: "دارجة", note: "Algerian Arabic", dir: "rtl",
      src: "https://scoopanddude.github.io/laporteweathernow-posts/preview/lang/ar-dz.js?v=0d3fdba228", css: "https://scoopanddude.github.io/laporteweathernow-posts/preview/lang/rtl.css?v=5f824b80c9" },
  ];
  // Languages Google Translate handles: code|English name|name in the language. Suggested ones first.
  var GOOGLE = ("es|Spanish|Español;ar|Arabic|العربية;fr|French|Français;pl|Polish|Polski;zh-CN|Chinese (Simplified)|简体中文;" +
    "vi|Vietnamese|Tiếng Việt;tl|Filipino|Filipino;hi|Hindi|हिन्दी;ko|Korean|한국어;ru|Russian|Русский;de|German|Deutsch;" +
    "pt|Portuguese|Português;uk|Ukrainian|Українська;" +
    "af|Afrikaans|Afrikaans;sq|Albanian|Shqip;am|Amharic|አማርኛ;hy|Armenian|Հայերեն;as|Assamese|অসমীয়া;az|Azerbaijani|Azərbaycan;" +
    "eu|Basque|Euskara;be|Belarusian|Беларуская;bn|Bengali|বাংলা;bs|Bosnian|Bosanski;bg|Bulgarian|Български;my|Burmese|မြန်မာ;" +
    "ca|Catalan|Català;ceb|Cebuano|Cebuano;ny|Chichewa|Chichewa;zh-TW|Chinese (Traditional)|繁體中文;co|Corsican|Corsu;" +
    "hr|Croatian|Hrvatski;cs|Czech|Čeština;da|Danish|Dansk;nl|Dutch|Nederlands;eo|Esperanto|Esperanto;et|Estonian|Eesti;" +
    "fi|Finnish|Suomi;fy|Frisian|Frysk;gl|Galician|Galego;ka|Georgian|ქართული;el|Greek|Ελληνικά;gn|Guarani|Avañeʼẽ;" +
    "gu|Gujarati|ગુજરાતી;ht|Haitian Creole|Kreyòl ayisyen;ha|Hausa|Hausa;haw|Hawaiian|ʻŌlelo Hawaiʻi;iw|Hebrew|עברית;" +
    "hmn|Hmong|Hmoob;hu|Hungarian|Magyar;is|Icelandic|Íslenska;ig|Igbo|Igbo;ilo|Ilocano|Ilokano;id|Indonesian|Bahasa Indonesia;" +
    "ga|Irish|Gaeilge;it|Italian|Italiano;ja|Japanese|日本語;jw|Javanese|Basa Jawa;kn|Kannada|ಕನ್ನಡ;kk|Kazakh|Қазақ;" +
    "km|Khmer|ខ្មែរ;rw|Kinyarwanda|Kinyarwanda;ku|Kurdish (Kurmanji)|Kurdî;ckb|Kurdish (Sorani)|کوردی;ky|Kyrgyz|Кыргызча;" +
    "lo|Lao|ລາວ;la|Latin|Latina;lv|Latvian|Latviešu;lt|Lithuanian|Lietuvių;lb|Luxembourgish|Lëtzebuergesch;mk|Macedonian|Македонски;" +
    "mg|Malagasy|Malagasy;ms|Malay|Bahasa Melayu;ml|Malayalam|മലയാളം;mt|Maltese|Malti;mi|Maori|Māori;mr|Marathi|मराठी;" +
    "mn|Mongolian|Монгол;ne|Nepali|नेपाली;no|Norwegian|Norsk;or|Odia|ଓଡ଼ିଆ;ps|Pashto|پښتو;fa|Persian|فارسی;pa|Punjabi|ਪੰਜਾਬੀ;" +
    "qu|Quechua|Runasimi;ro|Romanian|Română;sm|Samoan|Gagana Samoa;gd|Scottish Gaelic|Gàidhlig;sr|Serbian|Српски;st|Sesotho|Sesotho;" +
    "sn|Shona|Shona;sd|Sindhi|سنڌي;si|Sinhala|සිංහල;sk|Slovak|Slovenčina;sl|Slovenian|Slovenščina;so|Somali|Soomaali;" +
    "su|Sundanese|Basa Sunda;sw|Swahili|Kiswahili;sv|Swedish|Svenska;tg|Tajik|Тоҷикӣ;ta|Tamil|தமிழ்;tt|Tatar|Татар;te|Telugu|తెలుగు;" +
    "th|Thai|ไทย;ti|Tigrinya|ትግርኛ;tr|Turkish|Türkçe;tk|Turkmen|Türkmen;ur|Urdu|اردو;ug|Uyghur|ئۇيغۇرچە;uz|Uzbek|Oʻzbek;" +
    "cy|Welsh|Cymraeg;xh|Xhosa|isiXhosa;yi|Yiddish|ייִדיש;yo|Yoruba|Yorùbá;zu|Zulu|isiZulu").split(";");
  var RTL = { ar: 1, iw: 1, fa: 1, ur: 1, ps: 1, sd: 1, ug: 1, ckb: 1, yi: 1 };
  GOOGLE.forEach(function (row) {
    var f = row.split("|");
    LANGS.push({ code: f[0], name: f[2], note: f[1], short: f[0].toUpperCase(), dir: RTL[f[0]] ? "rtl" : "ltr", google: true,
      css: RTL[f[0]] ? LANGS[1].css : null });
  });
  var KEY = "lpwn_lang";
  var WAIT = "lpwn-i18n-wait";
  var byCode = {};
  LANGS.forEach(function (l) { byCode[l.code.toLowerCase()] = l; });

  function langFromUrl() {
    var m = /[?&]lang=([^&#]*)/.exec(location.search);
    if (!m) return null;
    var l = byCode[decodeURIComponent(m[1]).toLowerCase()];
    return l || null;
  }
  var picked = langFromUrl();
  var lang = byCode.en;
  if (picked) {
    lang = picked;
    try { localStorage.setItem(KEY, lang.code); } catch (e) { /* private mode: this page still switches */ }
  } else {
    try { var saved = byCode[String(localStorage.getItem(KEY) || "").toLowerCase()]; if (saved) lang = saved; } catch (e) { /* ignore */ }
  }
  var root = document.documentElement;
  function reveal() { root.classList.remove(WAIT); }

  var api = window.lpwnI18n = {
    lang: lang.code,
    langs: LANGS,
    define: function (code, build) { if (code === lang.code && !book) setBook(build); },
    tr: function (s, ctx) { return tr(s, ctx); },
    norm: norm,
  };

  /* ---------------- The language menu (every language, including English) ---------------- */
  function hrefFor(code) {
    try {
      var u = new URL(location.href);
      u.searchParams.set("lang", code);
      return u.pathname + u.search + u.hash;
    } catch (e) { return "?lang=" + encodeURIComponent(code); }
  }
  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  // The menu sits at the end of the main menu on computers, and in the top bar on phones (where
  // the main menu scrolls sideways and would clip a dropdown). A line in the footer lists them too.
  function addMenu() {
    if (document.querySelector(".lang-menu")) return;
    var here = lang;
    function item(l) {
      var cur = l === here;
      return '<a href="' + esc(hrefFor(l.code)) + '" lang="' + l.code + '" hreflang="' + l.code + '" data-find="' +
        esc((l.code + " " + l.name + " " + (l.note || "")).toLowerCase()) + '"' + (cur ? ' aria-current="true" class="on"' : "") +
        '><span dir="' + l.dir + '">' + esc(l.name) + "</span>" +
        (l.note ? ' <small lang="en" dir="ltr">' + esc(l.note) + "</small>" : "") + "</a>";
    }
    var own = LANGS.filter(function (l) { return !l.google; }).map(item).join("");
    var google = LANGS.filter(function (l) { return l.google; }).map(item).join("");
    var label = here.code === "en" ? "Language" : "Language · " + here.name;
    function menu(where) {
      var m = el("details", { "class": "lang-menu notranslate lang-menu-" + where, translate: "no" },
        '<summary aria-label="' + esc(label) + '"><span aria-hidden="true">&#127760;</span> ' +
        '<span lang="' + here.code + '">' + esc(here.short || here.code.toUpperCase()) + "</span></summary>" +
        '<div class="lang-list"><input type="search" class="lang-find" placeholder="Find your language" aria-label="Find your language" autocomplete="off" />' +
        '<div class="lang-items">' + own + '<p class="lang-head">Translated by Google</p>' + google +
        '<p class="lang-none" hidden>No match. Try the name in English.</p></div></div>');
      var find = m.querySelector(".lang-find");
      find.addEventListener("input", function () {
        var q = find.value.trim().toLowerCase(), any = false;
        m.querySelectorAll(".lang-items a").forEach(function (a) {
          var hit = !q || a.getAttribute("data-find").indexOf(q) >= 0;
          a.hidden = !hit; if (hit) any = true;
        });
        m.querySelector(".lang-head").hidden = !!q;
        m.querySelector(".lang-none").hidden = any;
      });
      find.addEventListener("keydown", function (e) {
        if (e.key !== "Enter") return;
        var first = m.querySelector(".lang-items a:not([hidden])");
        if (first) { e.preventDefault(); location.href = first.href; }
      });
      m.addEventListener("toggle", function () { if (m.open && window.matchMedia("(pointer: fine)").matches) find.focus(); });
      document.addEventListener("click", function (e) { if (m.open && !m.contains(e.target)) m.open = false; });
      document.addEventListener("keydown", function (e) { if (e.key === "Escape" && m.open) { m.open = false; m.querySelector("summary").focus(); } });
      return m;
    }
    var nav = document.querySelector(".nav .navlinks");
    if (nav) nav.appendChild(menu("nav"));
    var bar = document.querySelector(".topbar-links");
    if (bar) bar.appendChild(menu("top"));
    var foot = document.querySelector("footer");
    if (foot) {
      var shown = LANGS.filter(function (l) { return !l.google || l === here || /^(es|ar|fr)$/.test(l.code); });
      foot.appendChild(el("p", { "class": "lang-foot notranslate", translate: "no" },
        '<span aria-hidden="true">&#127760;</span> ' + shown.map(function (l) {
          return l === here ? '<strong lang="' + l.code + '">' + esc(l.name) + "</strong>"
            : '<a href="' + esc(hrefFor(l.code)) + '" lang="' + l.code + '" hreflang="' + l.code + '">' + esc(l.name) + "</a>";
        }).join(" &middot; ") + ' &middot; <a href="#" class="lang-more">More languages</a>'));
      foot.querySelector(".lang-more").addEventListener("click", function (e) {
        e.preventDefault();
        var m = document.querySelector(window.matchMedia("(max-width:900px)").matches ? ".lang-menu-top" : ".lang-menu-nav");
        if (!m) return;
        window.scrollTo({ top: 0, behavior: "smooth" });
        m.open = true;
      });
    }
    var css = el("style", { id: "lpwnLangMenuCss" });
    css.textContent =
      ".lang-menu{position:relative}" +
      ".lang-menu>summary{list-style:none;cursor:pointer;white-space:nowrap}" +
      ".lang-menu>summary::-webkit-details-marker{display:none}" +
      ".lang-menu>summary::after{content:\" \\25BE\";font-size:.85em}" +
      ".lang-menu-nav>summary{opacity:.88;padding:6px 0;border-bottom:2px solid transparent;font-weight:600}" +
      ".lang-menu-nav[open]>summary,.lang-menu-nav>summary:hover{opacity:1;border-bottom-color:var(--amber,#ff8a00)}" +
      ".lang-menu-top{display:none}" +
      ".lang-menu-top>summary{color:#fff;text-decoration:underline;text-underline-offset:3px}" +
      ".lang-list{position:absolute;inset-inline-end:0;top:calc(100% + 8px);z-index:90;width:270px;max-width:calc(100vw - 24px);background:#1f2420;border:1px solid rgba(255,255,255,.14);border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,.35);padding:8px;text-transform:none;letter-spacing:normal;font-weight:400;text-align:start}" +
      ".lang-find{width:100%;box-sizing:border-box;margin:0 0 6px;padding:10px 12px;border-radius:8px;border:1px solid rgba(255,255,255,.3);background:rgba(255,255,255,.08);color:#fff;font:inherit;font-size:15px}" +
      ".lang-find::placeholder{color:rgba(255,255,255,.55)}" +
      ".lang-items{display:grid;gap:2px;max-height:min(60vh,420px);overflow-y:auto;overscroll-behavior:contain}" +
      ".lang-items a{display:block;padding:9px 12px;border-radius:8px;border-bottom:0!important;opacity:1;color:#fff;text-decoration:none;font-size:15px;font-weight:700}" +
      ".lang-items a[hidden]{display:none}" +
      ".lang-items a small{display:block;font-size:12px;font-weight:600;color:#b9c0b6}" +
      ".lang-items a:hover,.lang-items a:focus-visible,.lang-items a.on{background:rgba(255,255,255,.1);color:var(--amber-bright,#ffb400)}" +
      ".lang-head,.lang-none{margin:8px 12px 4px;font-size:12px;font-weight:700;color:#b9c0b6;text-transform:uppercase;letter-spacing:.05em}" +
      ".lang-head[hidden],.lang-none[hidden]{display:none}" +
      ".lang-foot{width:100%;text-align:center;font-size:13px;color:#9aa197;margin-top:14px}" +
      ".lang-foot a{color:#fff;text-decoration:underline;text-underline-offset:3px}" +
      ".lang-foot strong{color:var(--amber-bright,#ffb400)}" +
      "@media (max-width:900px){.lang-menu-nav{display:none}.lang-menu-top{display:block}}" +
      "@media print{.lang-menu,.lang-foot{display:none!important}}";
    document.head.appendChild(css);
  }

  /* ---------------- Google Translate, for every language without its own phrasebook ---------------- */
  // Google reads the language from its "googtrans" cookie. It's cleared whenever English or a
  // hand-written language is picked, so Google never translates on top of those.
  function googCookie(code) {
    var val = code ? "/en/" + code : "";
    var end = code ? "" : ";expires=Thu, 01 Jan 1970 00:00:00 GMT";
    var host = location.hostname;
    document.cookie = "googtrans=" + val + ";path=/" + end;
    if (host.indexOf(".") > 0) {
      document.cookie = "googtrans=" + val + ";path=/;domain=" + host + end;
      document.cookie = "googtrans=" + val + ";path=/;domain=." + host.replace(/^www\./, "") + end;
    }
  }
  function startGoogle() {
    googCookie(lang.code);
    root.setAttribute("dir", lang.dir);
    root.classList.add("lpwn-i18n-google");
    if (lang.css) document.head.appendChild(el("link", { rel: "stylesheet", href: lang.css }));
    var css = el("style", {});
    // Google's own bar across the top of the page, and its hover pop-ups, stay hidden.
    css.textContent = "iframe.skiptranslate,body>.skiptranslate,.goog-te-banner-frame,#goog-gt-tt,.goog-te-balloon-frame," +
      ".VIpgJd-ZVi9od-ORHb-OEVmcd,.VIpgJd-ZVi9od-aZ2wEe-wOHMyf,.VIpgJd-yAWNEb-L7lbkb{display:none!important}" +
      "body{top:0!important}.goog-text-highlight{background:none!important;box-shadow:none!important}" +
      "#google_translate_element{display:none}" +
      ".lpwn-i18n-note{margin:0;padding:10px 24px;background:#fff4e5;color:#3b2a12;font-size:14px;line-height:1.6;text-align:center;border-bottom:1px solid #f0d9b5}" +
      ".lpwn-i18n-note a{color:#9a4f00;font-weight:700;text-decoration:underline}";
    document.head.appendChild(css);
    whenReady(function () {
      addMenu();
      // Written in English on purpose: Google translates it along with the page.
      var note = el("div", { "class": "lpwn-i18n-note", role: "note" },
        "Translated automatically by Google, so some words may be off. Temperatures are in °C and wind in km/h. Weather alerts are official from the National Weather Service. " +
        '<a class="notranslate" translate="no" href="' + esc(hrefFor("en")) + '" lang="en">English</a>');
      var main = document.querySelector("main") || document.body;
      main.insertBefore(note, main.firstChild);
      document.body.appendChild(el("div", { id: "google_translate_element" }));
      window.lpwnGoogleInit = function () {
        try { new window.google.translate.TranslateElement({ pageLanguage: "en", autoDisplay: false }, "google_translate_element"); } catch (e) { /* page stays English */ }
      };
      var g = document.createElement("script");
      g.src = "https://translate.google.com/translate_a/element.js?cb=lpwnGoogleInit";
      g.async = true;
      document.body.appendChild(g);
      mode = "google";
      if (unitsOn) {
        walk(document.body);
        new MutationObserver(function (list) {
          for (var i = 0; i < list.length; i++) {
            var m = list[i];
            if (m.type === "characterData") doText(m.target);
            else for (var j = 0; j < m.addedNodes.length; j++) walk(m.addedNodes[j]);
          }
        }).observe(document.body, { childList: true, subtree: true, characterData: true });
      }
      reveal();
    });
  }

  function whenReady(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }


  /* ---------------- Translating ---------------- */
  var book = null;          // the phrasebook: { exact, patterns, pages, notice, chrome }
  var exact = {};
  var mode = "full";        // "full": the whole page; "partial": menu, footer and dialogs only
  var CHROME = ".topbar, nav.nav, nav.bottom-bar, footer, .newsletter, dialog.install-dialog, .to-top, .skip-link, .lpwn-i18n-note";
  var SKIP = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1, CODE: 1, PRE: 1, TEMPLATE: 1, SVG: 1 };
  var ATTRS = ["placeholder", "aria-label", "alt", "title", "label"];
  var textSeen = new WeakMap();   // text node -> the value we left it with
  var attrSeen = new WeakMap();   // element -> { attr: value we left it with }

  function norm(s) { return String(s == null ? "" : s).replace(/[\s\u00a0\u202f\u200b]+/g, " ").trim(); }

  // A pattern can carry a third item, a CSS selector: then it only applies to text inside a
  // matching element (so "Clear" is translated as the sky in a forecast card, not elsewhere).
  function tr(s, ctx) {
    if (!book) return null;
    var key = norm(s);
    if (!key || !/[A-Za-z]/.test(key)) return null;
    if (Object.prototype.hasOwnProperty.call(exact, key)) return exact[key];
    var pats = book.patterns || [];
    for (var i = 0; i < pats.length; i++) {
      if (pats[i][2] && !(ctx && ctx.closest && ctx.closest(pats[i][2]))) continue;
      var m = pats[i][0].exec(key);
      if (!m) continue;
      var rep = pats[i][1];
      var out = typeof rep === "function" ? rep(m) : rep.replace(/\$(\d)/g, function (x, n) { return m[+n] || ""; });
      if (out != null) return out;
    }
    return null;
  }

  function skipped(node) {
    for (var e = node; e && e.nodeType === 1; e = e.parentNode) {
      if (SKIP[e.tagName.toUpperCase()] || e.getAttribute("translate") === "no" || e.isContentEditable) return true;
    }
    return false;
  }
  function inScope(node) {
    if (mode === "full") return true;
    if (mode === "google") return false;
    var e = node.nodeType === 1 ? node : node.parentNode;
    return !!(e && e.closest && (e.closest(CHROME) || e.tagName === "TITLE"));
  }

  function doText(node) {
    var v = node.nodeValue;
    if (!v || textSeen.get(node) === v) return;
    textSeen.set(node, v);
    if (!node.parentNode || skipped(node.parentNode)) return;
    var out = v;
    if (inScope(node)) {
      var t = tr(v, node.parentNode);
      if (t != null) out = /^\s*/.exec(v)[0] + t + /\s*$/.exec(v)[0];
    }
    if (unitsOn) out = units(out);
    textSeen.set(node, out);
    if (out !== v) node.nodeValue = out;
    if (fillOn) guard(node, out);
  }

  /* ---------------- Google filling in what a phrasebook doesn't know ---------------- */
  // Blocks the phrasebook translated completely are marked "notranslate", so Google keeps its
  // hands off the hand-written wording. English left anywhere (a word the phrasebook doesn't know,
  // or a live update) unmarks the blocks around it, so Google translates that part.
  var fillOn = false;
  var ENGLISH = /[A-Za-z]{3,}/;
  function guard(node, text) {
    var p = node.parentNode;
    if (!p || p.nodeType !== 1 || p.tagName === "FONT") return;   // FONT: Google's own translated text
    if (!/[A-Za-z\u0600-\u06FF]/.test(text)) return;              // spaces, numbers, punctuation: nothing to decide
    if (ENGLISH.test(text)) {
      var touched = false;
      for (var e = p; e && e.nodeType === 1; e = e.parentNode) {
        if (e.hasAttribute("data-lpwn-nt")) { e.classList.remove("notranslate"); e.removeAttribute("data-lpwn-nt"); touched = true; }
      }
      // Google only notices changed text, so hand it this text again once the block is open to it.
      if (touched) { var again = node.nodeValue; node.nodeValue = again + " "; node.nodeValue = again; }
    } else if (!p.classList.contains("notranslate") && !ENGLISH.test(p.textContent || "")) {
      p.classList.add("notranslate");
      p.setAttribute("data-lpwn-nt", "1");
    }
  }
  function startFill(code) {
    googCookie(code);
    var css = el("style", {});
    // Google's own bar across the top of the page, and its hover pop-ups, stay hidden.
    css.textContent = "iframe.skiptranslate,body>.skiptranslate,.goog-te-banner-frame,#goog-gt-tt,.goog-te-balloon-frame," +
      ".VIpgJd-ZVi9od-ORHb-OEVmcd,.VIpgJd-ZVi9od-aZ2wEe-wOHMyf,.VIpgJd-yAWNEb-L7lbkb{display:none!important}" +
      "body{top:0!important}.goog-text-highlight{background:none!important;box-shadow:none!important}" +
      "#google_translate_element{display:none}";
    document.head.appendChild(css);
    // The site's name stays as it is (Google would translate "Weather Now").
    document.querySelectorAll(".brand").forEach(function (b) { b.classList.add("notranslate"); });
    document.body.appendChild(el("div", { id: "google_translate_element" }));
    window.lpwnGoogleInit = function () {
      try { new window.google.translate.TranslateElement({ pageLanguage: "en", autoDisplay: false }, "google_translate_element"); } catch (e) { /* the phrasebook's translation stays */ }
    };
    var g = document.createElement("script");
    g.src = "https://translate.google.com/translate_a/element.js?cb=lpwnGoogleInit";
    g.async = true;
    document.body.appendChild(g);
  }

  /* ---------------- Units: Celsius and km/h for every language but English ---------------- */
  // The Weather Service works in Fahrenheit and mph. Outside the U.S. people use Celsius and
  // km/h, so every other language gets those. Converted numbers always say "°C", which is also
  // how the page knows not to convert them twice. Pages that score forecasts in degrees of
  // error (the Track Record) keep Fahrenheit, where a conversion would give wrong differences.
  var NO_UNITS = ["/track-record", "/scoop-draft"];
  var unitsOn = false;
  function toC(f) { return Math.round((f - 32) * 5 / 9); }
  function toK(m) { return Math.round(m * 1.609); }
  function units(s) {
    if (!/°|mph/.test(s)) return s;
    var out = s
      .replace(/(\d+) mph, gusts (\d+)/g, function (x, a, b) { return toK(+a) + " km/h, gusts " + toK(+b); })
      .replace(/(\d+)( to | حتى )(\d+) mph/g, function (x, a, t, b) { return toK(+a) + t + toK(+b) + " km/h"; })
      .replace(/(\d+) ?mph/g, function (x, a) { return toK(+a) + " km/h"; })
      .replace(/(^|[^\d.,])(-?\d{1,3}) ?° ?F?(?![C\d])/g, function (x, pre, f) { return pre + toC(+f) + "°C"; });
    return lang.dir === "rtl" && !lang.google ? out.replace(/ km\/h/g, " كم/سا") : out;
  }
  api.units = units;

  function doAttrs(e) {
    if (!e.hasAttribute || !inScope(e)) return;
    var memo = attrSeen.get(e);
    for (var i = 0; i < ATTRS.length; i++) {
      var a = ATTRS[i];
      if (!e.hasAttribute(a)) continue;
      var v = e.getAttribute(a);
      if (memo && memo[a] === v) continue;
      if (!memo) { memo = {}; attrSeen.set(e, memo); }
      memo[a] = v;
      var t = tr(v, e);
      if (t != null && t !== v) { memo[a] = t; e.setAttribute(a, t); }
    }
    if (e.tagName === "INPUT" && /^(submit|button)$/i.test(e.type) && e.value) {
      var tv = tr(e.value, e);
      if (tv != null) e.value = tv;
    }
  }
  function marks(e) {
    // In partial mode, each translated block (menu, footer, dialog) reads right-to-left on its own.
    if (mode === "partial" && e.matches && e.matches(CHROME) && !e.hasAttribute("dir")) {
      e.setAttribute("dir", lang.dir);
      e.setAttribute("lang", lang.code);
    }
  }
  function walk(n) {
    if (n.nodeType === 3) { doText(n); return; }
    if (n.nodeType !== 1 && n.nodeType !== 11) return;
    if (n.nodeType === 1) {
      if (skipped(n)) return;
      marks(n);
      doAttrs(n);
    }
    var w = document.createTreeWalker(n, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode: function (x) {
        if (x.nodeType === 1 && (SKIP[x.tagName.toUpperCase()] || x.getAttribute("translate") === "no")) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    var x;
    while ((x = w.nextNode())) {
      if (x.nodeType === 3) doText(x);
      else { marks(x); doAttrs(x); }
    }
  }

  function pathKey() {
    var p = location.pathname.replace(/\/index(\.html)?$/, "/").replace(/\.html$/, "");
    return p.length > 1 ? p.replace(/\/$/, "") : "/";
  }

  function addNote() {
    if (!book.notice || document.querySelector(".lpwn-i18n-note")) return;
    var note = el("div", { "class": "lpwn-i18n-note", role: "note", lang: lang.code, dir: lang.dir, translate: "no" },
      book.notice(function (c) { return esc(hrefFor(c)); }));
    var main = document.querySelector("main") || document.body;
    main.insertBefore(note, main.firstChild);
  }

  function setBook(build) {
    book = build(api) || {};
    exact = {};
    var src = book.exact || {};
    for (var k in src) if (Object.prototype.hasOwnProperty.call(src, k)) exact[norm(k)] = src[k];
    start();
  }

  var started = false;
  function start() {
    if (started || !book) return;
    whenReady(function () {
      if (started) return;
      started = true;
      var byHand = (book.pages || []).indexOf(pathKey()) >= 0;
      // With `fill`, every page is translated in full: the phrasebook first, Google for the rest.
      fillOn = !!book.fill;
      mode = byHand || fillOn ? "full" : "partial";
      root.classList.add("lpwn-i18n", "lpwn-i18n-" + mode);
      if (mode === "full") { root.setAttribute("lang", lang.code); root.setAttribute("dir", lang.dir); }
      addMenu();
      if (!byHand) addNote();
      var t = tr(document.title);
      if (t) document.title = t;
      walk(document.body);
      new MutationObserver(function (list) {
        for (var i = 0; i < list.length; i++) {
          var m = list[i];
          if (m.type === "characterData") doText(m.target);
          else if (m.type === "attributes") { if (inScope(m.target) && !skipped(m.target)) doAttrs(m.target); }
          else for (var j = 0; j < m.addedNodes.length; j++) walk(m.addedNodes[j]);
        }
      }).observe(root, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
      if (fillOn) startFill(book.fill);
      reveal();
    });
  }

  unitsOn = lang.code !== "en" && NO_UNITS.indexOf(pathKey()) < 0;
  if (!lang.google) googCookie("");
  if (lang.google) { startGoogle(); if (picked && typeof window.lpwnTrack === "function") window.lpwnTrack("language", lang.code); return; }
  if (lang.code === "en") { reveal(); whenReady(addMenu); return; }

  // Load this language's styles (right-to-left layout) and phrasebook.
  if (lang.css) document.head.appendChild(el("link", { rel: "stylesheet", href: lang.css }));
  var s = document.createElement("script");
  s.src = lang.src;
  s.onerror = function () { reveal(); whenReady(addMenu); };
  document.head.appendChild(s);
  if (picked && typeof window.lpwnTrack === "function") window.lpwnTrack("language", lang.code);
})();
