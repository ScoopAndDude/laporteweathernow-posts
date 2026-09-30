/* La Porte Weather Now: the weather radio on the Alerts page (added September 30, 2026).
 *
 * Two voices:
 * - La Porte County: a recording made on GitHub's free servers whenever the broadcast changes (up to
 *   every 15 minutes), read by Kokoro, an open-source natural voice (scripts/radio_broadcast.py in
 *   ScoopAndDude/laporteweathernow-posts; the newest one lives on that repository's "radio" branch).
 *   It reads the official alerts, the La Porte airport reading, the NWS forecast and today's Scoop.
 * - Any other town, or when the recording is over 3 hours old or won't load: this device's own voice
 *   reads the official alerts and forecast this page already loaded.
 * Warnings issued after the recording are read first, in the device's voice, after a soft chime.
 * "Keep listening" reads new alerts as they come in while the page stays open (screen kept on).
 * One volume slider covers everything (recording, chime and voice) and is remembered on the device.
 *
 * The page's own script tells the radio the place, the alerts and the forecast through
 * window.lpwnRadio (a small stand-in collects those calls until this file has loaded).
 */
(function () {
  "use strict";

  const RAW = "https://raw.githubusercontent.com/ScoopAndDude/laporteweathernow-posts/radio/";
  const HOME = { lat: 41.6081, lon: -86.7189 };
  const HOME_KM = 25;              // about La Porte County
  const STALE_MINUTES = 180;       // older recordings give way to the device's voice
  const VOL_KEY = "lpwn_radio_volume";
  const KEEP_KEY = "lpwn_radio_keep";
  const $ = (id) => document.getElementById(id);

  const ui = {
    play: $("wrPlay"), status: $("wrStatus"), title: $("wrTitle"), seek: $("wrSeek"), time: $("wrTime"),
    chapters: $("wrChapters"), vol: $("wrVol"), volNum: $("wrVolNum"), mute: $("wrMute"), keep: $("wrKeep"),
    text: $("wrText"), readAlong: $("wrReadAlong"), progress: $("wrProgress"),
  };
  if (!ui.play) return;

  // ---------- What the page has told us ----------
  let place = { name: "La Porte, IN", lat: HOME.lat, lon: HOME.lon, tz: "America/Chicago" };
  let liveAlerts = null;           // NWS alert features for the place (null: not loaded or failed)
  let forecast = null;             // NWS periods (clock times already in the place's own time zone)
  const heard = new Set();         // alert ids already read (or in the recording that was played)

  // ---------- Small helpers ----------
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode: fine */ } },
  };
  function km(a, b) {
    const r = Math.PI / 180, dLat = (b.lat - a.lat) * r, dLon = (b.lon - a.lon) * r;
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2;
    return 12742 * Math.asin(Math.sqrt(h));
  }
  const atHome = () => km(place, HOME) <= HOME_KM;
  const tzOf = () => place.tz || "America/Chicago";
  function clockText(d) {
    try { return new Date(d).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: tzOf() }); }
    catch (e) { return new Date(d).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }); }
  }
  const mmss = (s) => { s = Math.max(0, Math.round(s || 0)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
  function say(msg) { ui.status.textContent = msg; }
  const props = (a) => (a && a.properties) || a || {};

  // ---------- Volume ----------
  let lastLoud = 80;
  function volume() { return Math.max(0, Math.min(100, Number(ui.vol.value) || 0)) / 100; }
  function showVolume() {
    const v = Math.round(volume() * 100);
    ui.volNum.textContent = `${v}%`;
    ui.mute.innerHTML = v === 0 ? "&#128263;" : v < 40 ? "&#128264;" : v < 75 ? "&#128265;" : "&#128266;";
    ui.mute.setAttribute("aria-label", v === 0 ? "Turn the sound back on" : "Mute");
    ui.vol.setAttribute("aria-valuetext", `${v} percent`);
  }
  function applyVolume() {
    showVolume();
    if (gain && ctx) gain.gain.setTargetAtTime(volume(), ctx.currentTime, 0.05);
    if (speaking) restartChunk();              // the device voice takes the new volume right away
    store.set(VOL_KEY, String(Math.round(volume() * 100)));
  }
  const savedVol = Number(store.get(VOL_KEY));
  if (store.get(VOL_KEY) !== null && isFinite(savedVol)) ui.vol.value = String(savedVol);
  if (volume() > 0) lastLoud = Math.round(volume() * 100);
  showVolume();
  ui.vol.addEventListener("input", () => { if (volume() > 0) lastLoud = Math.round(volume() * 100); applyVolume(); });
  ui.mute.addEventListener("click", () => {
    ui.vol.value = String(volume() > 0 ? 0 : lastLoud || 80);
    applyVolume();
  });
  if (store.get(KEEP_KEY) === "0") ui.keep.checked = false;
  ui.keep.addEventListener("change", () => {
    store.set(KEEP_KEY, ui.keep.checked ? "1" : "0");
    if (!ui.keep.checked && mode === "standby") stopAll("Stopped.");
    if (ui.keep.checked && mode === "idle" && played) standby();
  });

  // ---------- Sound: the recording and the chime ----------
  let ctx = null, gain = null, buffer = null, src = null, startedAt = 0, offset = 0, playingAudio = false;
  let rec = null;                  // radio.json of the recording in use
  function audio() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      gain = ctx.createGain();
      gain.gain.value = volume();
      gain.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }
  function decode(ab) {
    return new Promise((res, rej) => {
      const p = ctx.decodeAudioData(ab, res, rej);   // older Safari only knows the callback form
      if (p && p.then) p.then(res, rej);
    });
  }
  function stopSource() {
    if (!src) return;
    src.onended = null;
    try { src.stop(); } catch (e) { /* already stopped */ }
    try { src.disconnect(); } catch (e) { /* ignore */ }
    src = null;
  }
  function position() { return playingAudio ? Math.min(ctx.currentTime - startedAt, buffer.duration) : offset; }
  function startAt(t) {
    stopSource();
    offset = Math.max(0, Math.min(t, buffer.duration - 0.05));
    const s = ctx.createBufferSource();
    s.buffer = buffer;
    s.connect(gain);
    s.onended = () => { if (src === s) { src = null; playingAudio = false; offset = 0; recordingEnded(); } };
    src = s;
    startedAt = ctx.currentTime - offset;
    s.start(0, offset);
    playingAudio = true;
    mode = "playing";
    tick();
  }
  function pauseRecording() { if (!playingAudio) return; offset = position(); stopSource(); playingAudio = false; }
  function chime() {
    const c = audio();
    if (!c) return Promise.resolve();
    const t0 = c.currentTime + 0.05;
    [[659.25, 0], [880, 0.24]].forEach(([f, d]) => {   // two soft notes; never an emergency-alert tone
      const o = c.createOscillator(), g = c.createGain();
      o.type = "sine";
      o.frequency.value = f;
      g.gain.setValueAtTime(0.0001, t0 + d);
      g.gain.linearRampToValueAtTime(0.4, t0 + d + 0.03);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + d + 0.6);
      o.connect(g);
      g.connect(gain);
      o.start(t0 + d);
      o.stop(t0 + d + 0.65);
    });
    return new Promise((r) => setTimeout(r, 1000));
  }

  // ---------- The device's own voice ----------
  const canSpeak = "speechSynthesis" in window && typeof SpeechSynthesisUtterance === "function";
  let speaking = false, sayList = [], sayAt = 0, sayToken = 0, sayDone = null, voice = null;
  function bestVoice() {
    if (!canSpeak) return null;
    const vs = speechSynthesis.getVoices().filter((v) => /^en([-_]|$)/i.test(v.lang));
    const score = (v) => (/en[-_]US/i.test(v.lang) ? 4 : 0) +
      (/natural|neural|online|premium|enhanced/i.test(v.name) ? 6 : 0) +
      (/google us english|samantha|aria|jenny|guy|ava|evan|zoe|allison|susan|nicky/i.test(v.name) ? 3 : 0) -
      (/compact|novelty|whisper|bad news|bells|boing|bubbles|cellos|zarvox|trinoids|albert|jester|organ|superstar|wobble|grandma|grandpa|eddy|flo|reed|rocko|sandy|shelley/i.test(v.name) ? 20 : 0);
    return vs.sort((a, b) => score(b) - score(a))[0] || null;
  }
  if (canSpeak) { voice = bestVoice(); speechSynthesis.addEventListener && speechSynthesis.addEventListener("voiceschanged", () => { voice = bestVoice(); }); }
  function pieces(text) {
    const parts = String(text).match(/[^.!?]+[.!?]+["')]*\s*|[^.!?]+$/g) || [String(text)];
    const out = [];
    let cur = "";
    parts.forEach((p) => {
      if (cur && (cur + p).length > 180) { out.push(cur.trim()); cur = p; } else cur += p;
    });
    if (cur.trim()) out.push(cur.trim());
    const fine = [];
    out.forEach((c) => {   // very long sentences: break at commas (Chrome stops talking after ~15 seconds)
      if (c.length <= 240) { fine.push(c); return; }
      const bits = c.split(/,\s+/);
      bits.forEach((b, i) => fine.push(i < bits.length - 1 ? b + "," : b));
    });
    return fine.filter((x) => x.trim());
  }
  let speechBroken = false;       // this device never started talking: don't wait on it again
  function speakNext(token) {
    if (token !== sayToken) return;
    if (sayAt >= sayList.length || speechBroken) {
      speaking = false;
      const d = sayDone; sayDone = null;
      if (d) d();
      return;
    }
    const line = sayList[sayAt];
    const u = new SpeechSynthesisUtterance(line);
    if (voice) { u.voice = voice; u.lang = voice.lang; } else u.lang = "en-US";
    u.rate = 0.95;
    u.pitch = 1;
    u.volume = volume();
    let started = false, doneOnce = false;
    const move = () => { if (doneOnce || token !== sayToken) return; doneOnce = true; clearTimeout(noStart); clearTimeout(tooLong); sayAt += 1; speakNext(token); };
    // Some browsers accept speech and never say a word (no voices installed): give up after 4 seconds.
    const noStart = setTimeout(() => {
      if (started || token !== sayToken) return;
      speechBroken = true;
      try { speechSynthesis.cancel(); } catch (e) { /* ignore */ }
      move();
    }, 4000);
    // And some stop partway without saying so: move on after a generous time for the line.
    const tooLong = setTimeout(move, 6000 + line.length * 120);
    u.onstart = () => { started = true; };
    u.onend = move;
    u.onerror = (e) => {
      if (token !== sayToken || e.error === "interrupted" || e.error === "canceled") return;
      move();
    };
    speechSynthesis.speak(u);
  }
  function speak(texts, done) {
    stopSpeech();
    sayList = [].concat(...texts.map(earText).map(pieces));
    sayAt = 0;
    sayDone = done || null;
    speaking = true;
    speakNext(++sayToken);
  }
  function stopSpeech() {
    sayToken += 1;
    speaking = false;
    if (canSpeak) { try { speechSynthesis.cancel(); } catch (e) { /* ignore */ } }
  }
  function restartChunk() {
    if (!speaking || sayAt >= sayList.length) return;
    const token = ++sayToken;
    try { speechSynthesis.cancel(); } catch (e) { /* ignore */ }
    setTimeout(() => speakNext(token), 80);
  }

  /** Weather Service wording, tidied for listening (the recording does this, and more, on GitHub). */
  function earText(s) {
    let t = String(s || "").split(/\n\s*&&/)[0];
    t = t.replace(/^\s*(LAT\.\.\.LON|TIME\.\.\.MOT\.\.\.LOC|MAX HAIL SIZE|MAX WIND GUST|TORNADO\.\.\.|HAIL\.\.\.|WIND\.\.\.).*$/gm, "");
    t = t.replace(/(^|\s)\*?\s*PRECAUTIONARY\/PREPAREDNESS ACTIONS\.\.\./g, "$1");
    t = t.replace(/(^|\s)\*?\s*(HAZARD|SOURCE|IMPACTS|IMPACT|WHAT|WHERE|WHEN|ADDITIONAL DETAILS)\.\.\./g,
      (m, a, h) => `${a}${h.charAt(0)}${h.slice(1).toLowerCase()}: `);
    t = t.replace(/^\s*\*\s*/gm, "").replace(/\$\$/g, " ").replace(/\s+/g, " ").replace(/\.\.\.|…/g, ", ");
    t = t.replace(/\b(\d{1,2})(\d{2}) (AM|PM)\b/g, (m, h, mm, ap) => `${+h}:${mm} ${ap}`);
    t = t.replace(/\b(\d{1,2})(:\d\d)?\s?(am|pm)\b/gi, (m, h, mm, ap) => `${h}${mm || ""} ${ap.toUpperCase()}`);
    t = t.replace(/\b(CDT|CST|CT)\b/g, "").replace(/\b(EDT|EST|ET)\b/g, "eastern time");
    const letters = t.replace(/[^A-Za-z]/g, "");
    if (letters.length > 20 && letters.replace(/[^A-Z]/g, "").length / letters.length > 0.6) {
      t = t.toLowerCase().replace(/(^|[.!?]\s+)([a-z])/g, (m, a, b) => a + b.toUpperCase()).replace(/\b(am|pm)\b/g, (m) => m.toUpperCase());
    }
    t = t.replace(/\bLa ?Porte\b/gi, "La Port").replace(/\bNWS\b/g, "the Weather Service").replace(/\bthe the\b/gi, "the");
    t = t.replace(/\bI-(\d+)/g, "Interstate $1").replace(/\bmph\b/gi, "miles an hour").replace(/\bkts?\b/g, "knots");
    t = t.replace(/(\d)\s?%/g, "$1 percent").replace(/(\d)\s?°\s?F?\b/g, "$1 degrees").replace(/&/g, " and ");
    t = t.replace(/\s+([,.;:!?])/g, "$1").replace(/,\s*([,.;:!?])/g, "$1").replace(/\s{2,}/g, " ").trim();
    return t && !/[.!?]$/.test(t) ? t + "." : t;
  }

  // ---------- What the device voice reads ----------
  function activeAlerts() {
    return (liveAlerts || []).map(props).filter((p) => p.event && String(p.messageType || "").toLowerCase() !== "cancel");
  }
  function alertLines(list) {
    const out = [];
    list.forEach((p) => {
      let until = "";
      try { until = typeof alertUntilText === "function" ? alertUntilText(p, tzOf()) : ""; } catch (e) { /* ignore */ }
      out.push(`${p.event}${until ? ", " + until.replace(/\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b/, (d) => ({ Mon: "Monday", Tue: "Tuesday", Wed: "Wednesday", Thu: "Thursday", Fri: "Friday", Sat: "Saturday", Sun: "Sunday" })[d]) : ""}.`);
      if (p.description) out.push(p.description);
      if (p.instruction) out.push(p.instruction);
    });
    return out;
  }
  function liveProgram() {
    const lines = [`This is the La Porte Weather Now weather radio for ${place.name}, read by your device.`];
    if (liveAlerts === null) lines.push("The Weather Service's alerts couldn't be checked just now. Check again when you have a signal.");
    else {
      const list = activeAlerts();
      if (!list.length) lines.push(`There are no watches, warnings or advisories for ${place.name} right now.`);
      else {
        lines.push(`The National Weather Service has ${list.length === 1 ? "one alert" : list.length + " alerts"} for ${place.name}.`);
        lines.push(...alertLines(list));
      }
      list.forEach((p) => p.id && heard.add(p.id));
    }
    if (forecast && forecast.length) {
      lines.push("Now, the forecast from the National Weather Service.");
      forecast.slice(0, 3).forEach((p) => lines.push(`${p.name}: ${p.detailedForecast || p.shortForecast || ""}`));
    } else lines.push("The forecast isn't loaded yet.");
    lines.push(`That's the latest for ${place.name}. Stay safe.`);
    return lines;
  }

  // ---------- The recording ----------
  let recAudioUrl = null;
  async function loadRecording() {
    const r = await fetch(`${RAW}radio.json?t=${Date.now()}`, { cache: "no-store" });
    if (!r.ok) throw new Error("no recording");
    const j = await r.json();
    const age = (Date.now() - new Date(j.recorded).getTime()) / 60000;
    if (!(age < STALE_MINUTES)) throw new Error("old recording");
    if (recAudioUrl !== j.audio || !buffer) {
      const a = await fetch(RAW + j.audio);
      if (!a.ok) throw new Error("no audio");
      buffer = await decode(await a.arrayBuffer());
      recAudioUrl = j.audio;
    }
    rec = j;
    return j;
  }
  function showRecordingParts() {
    ui.progress.hidden = false;
    ui.seek.max = String(Math.round(buffer.duration * 10) / 10);
    ui.chapters.innerHTML = "";
    (rec.segments || []).filter((s) => !/^(intro|outro)$/.test(s.id)).forEach((s) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "wr-chap";
      b.textContent = s.title;
      b.dataset.start = s.start;
      b.addEventListener("click", () => { if (!buffer) return; audio(); stopSpeech(); startAt(Number(s.start)); showPlaying(); });
      ui.chapters.appendChild(b);
    });
    ui.text.innerHTML = "";
    (rec.segments || []).forEach((s) => {
      const d = document.createElement("div");
      d.className = "wr-seg";
      d.dataset.start = s.start;
      const h = document.createElement("h4");
      h.textContent = s.title;
      d.appendChild(h);
      (s.text || []).forEach((t) => { const p = document.createElement("p"); p.textContent = t; d.appendChild(p); });
      ui.text.appendChild(d);
    });
    ui.readAlong.hidden = false;
  }
  let tickTimer = null;
  function tick() {
    clearTimeout(tickTimer);
    if (!playingAudio || !buffer) return;
    const t = position();
    ui.seek.value = String(Math.round(t * 10) / 10);
    ui.time.textContent = `${mmss(t)} / ${mmss(buffer.duration)}`;
    let cur = null;
    ui.chapters.querySelectorAll(".wr-chap").forEach((b) => { if (t + 0.2 >= Number(b.dataset.start)) cur = b; });
    ui.chapters.querySelectorAll(".wr-chap").forEach((b) => b.classList.toggle("on", b === cur));
    let seg = null;
    ui.text.querySelectorAll(".wr-seg").forEach((d) => { if (t + 0.2 >= Number(d.dataset.start)) seg = d; });
    ui.text.querySelectorAll(".wr-seg").forEach((d) => d.classList.toggle("on", d === seg));
    tickTimer = setTimeout(tick, 250);
  }
  ui.seek.addEventListener("input", () => {
    if (!buffer) return;
    const t = Number(ui.seek.value);
    if (playingAudio) startAt(t); else { offset = t; ui.time.textContent = `${mmss(t)} / ${mmss(buffer.duration)}`; }
  });

  // ---------- Playing ----------
  let mode = "idle";               // idle | loading | playing | paused | speaking | standby
  let played = false;
  let resumeAfter = false;
  function showPlaying() {
    ui.play.classList.add("on");
    ui.play.innerHTML = "&#10074;&#10074;";
    ui.play.setAttribute("aria-label", "Pause the weather radio");
  }
  function showStopped() {
    ui.play.classList.remove("on");
    ui.play.innerHTML = "&#9654;";
    ui.play.setAttribute("aria-label", "Play the weather radio");
  }
  function stopAll(msg) {
    pauseRecording();
    offset = 0;
    stopSpeech();
    keepAwake(false);
    mode = "idle";
    showStopped();
    if (msg) say(msg);
  }
  function recordingEnded() {
    rec && (rec.alertIds || []).forEach((id) => heard.add(id));
    ui.seek.value = "0";
    finished();
  }
  function finished() {
    played = true;
    if (ui.keep.checked) standby();
    else { mode = "idle"; showStopped(); say("That's the latest. Tap play to hear it again."); }
  }
  function standby() {
    mode = "standby";
    showStopped();
    keepAwake(true);
    say(`Listening for new alerts for ${place.name}. New ones are read out loud while this page stays open.`);
  }
  function unlockVoice() {
    // iPhones only let a page talk after a tap; a silent word during this tap opens the way.
    if (!canSpeak) return;
    try { const u = new SpeechSynthesisUtterance(" "); u.volume = 0; speechSynthesis.speak(u); } catch (e) { /* ignore */ }
  }
  function newSinceRecording() {
    return activeAlerts().filter((p) => p.id && !heard.has(p.id) && !(rec && (rec.alertIds || []).indexOf(p.id) >= 0));
  }
  async function play() {
    if (mode === "playing") { pauseRecording(); mode = "paused"; showStopped(); say(`Paused at ${mmss(offset)}.`); return; }
    if (mode === "speaking") { stopAll("Stopped."); return; }
    if (mode === "paused" && buffer) { audio(); startAt(offset); showPlaying(); say(rec ? recordedLine() : ""); return; }
    audio();
    unlockVoice();
    if (ui.keep.checked) keepAwake(true);     // asked during the tap, when browsers allow it
    showPlaying();
    if (atHome()) {
      mode = "loading";
      say("Loading the La Porte County broadcast…");
      try {
        await loadRecording();
        if (mode !== "loading") return;          // stopped meanwhile
        showRecordingParts();
        const fresh = newSinceRecording();
        if (fresh.length) {
          fresh.forEach((p) => heard.add(p.id));
          mode = "speaking";
          say(`New since the recording: ${fresh.map((p) => p.event).join(", ")}.`);
          await chime();
          speak([`First, new since this recording at ${clockText(rec.recorded)}.`].concat(alertLines(fresh)), () => {
            if (mode !== "speaking") return;
            startAt(0);
            showPlaying();
            say(speechBroken ? `This device can't read the newer alert out loud: ${fresh.map((p) => p.event).join(", ")}. See the alerts at the top of this page.` : recordedLine());
          });
          return;
        }
        startAt(0);
        say(recordedLine());
        return;
      } catch (e) {
        if (mode !== "loading") return;
        if (!canSpeak) { stopAll("The broadcast won't load right now, and this browser can't read out loud. Try again soon."); return; }
        say("The recorded broadcast isn't available right now, so your device's voice is reading the latest.");
      }
    }
    if (!canSpeak) { stopAll("This browser can't read out loud. Try Chrome, Edge or Safari."); return; }
    ui.progress.hidden = true;
    ui.readAlong.hidden = true;
    mode = "speaking";
    if (!atHome()) say(`Reading the latest for ${place.name} in your device's voice.`);
    speak(liveProgram(), () => { if (mode === "speaking") finished(); });
  }
  function recordedLine() {
    return `Recorded at ${clockText(rec.recorded)} · ${mmss(rec.duration || (buffer && buffer.duration))} long. Read by an AI voice from official information.`;
  }
  ui.play.disabled = false;
  ui.play.addEventListener("click", play);

  // New alerts while playing or listening: chime, then read them.
  async function announceNew() {
    if (!(mode === "standby" || mode === "playing")) return;
    const fresh = newSinceRecording();
    if (!fresh.length) return;
    fresh.forEach((p) => heard.add(p.id));
    resumeAfter = mode === "playing";
    pauseRecording();
    mode = "speaking";
    showPlaying();
    say(`New alert: ${fresh.map((p) => p.event).join(", ")}.`);
    await chime();
    speak([`New alert for ${place.name}.`].concat(alertLines(fresh)), () => {
      if (mode !== "speaking") return;
      if (resumeAfter && buffer) { startAt(offset); showPlaying(); say(recordedLine()); }
      else if (ui.keep.checked) standby();
      else { mode = "idle"; showStopped(); say("That's the latest."); }
      if (speechBroken) say(`New alert: ${fresh.map((p) => p.event).join(", ")}. This device can't read it out loud; see the alerts at the top of this page.`);
    });
  }

  // ---------- Keeping the screen on while listening ----------
  let lock = null;
  async function keepAwake(on) {
    try {
      if (on && !lock && "wakeLock" in navigator) {
        lock = await navigator.wakeLock.request("screen");
        lock.addEventListener("release", () => { lock = null; });
      } else if (!on && lock) { const l = lock; lock = null; await l.release(); }
    } catch (e) { /* not allowed right now: the page still listens while the screen is on */ }
  }
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && mode === "standby") keepAwake(true);
  });

  // ---------- Talking to the page ----------
  function setPlace(loc) {
    if (!loc || !isFinite(loc.lat) || !isFinite(loc.lon)) return;
    const moved = km(place, loc) > 1;
    place = { name: loc.name || "this spot", lat: Number(loc.lat), lon: Number(loc.lon), tz: loc.tz || place.tz };
    ui.title.textContent = atHome() ? "La Porte County weather radio" : `Weather radio for ${place.name}`;
    if (moved) {
      if (mode !== "idle") stopAll();
      heard.clear();
      liveAlerts = null;
      forecast = null;
      ui.progress.hidden = true;
      ui.readAlong.hidden = true;
      say(atHome()
        ? "Tap play for the La Porte County broadcast: alerts, the airport reading, the forecast and today's Daily Scoop."
        : `Tap play and your device's voice reads the official alerts and forecast for ${place.name}.`);
    }
  }
  const api = {
    place: setPlace,
    alerts(list, loc) { if (loc) setPlace(loc); liveAlerts = Array.isArray(list) ? list : null; announceNew(); },
    forecast(periods, loc) { if (loc) setPlace(loc); forecast = Array.isArray(periods) ? periods : forecast; },
  };
  const queued = (window.lpwnRadio && window.lpwnRadio.q) || [];
  window.lpwnRadio = api;
  queued.forEach(([k, args]) => { if (api[k]) api[k].apply(null, args); });
  if (mode === "idle" && !ui.status.dataset.set) {
    ui.status.dataset.set = "1";
    setPlace(place);
    say(atHome()
      ? "Tap play for the La Porte County broadcast: alerts, the airport reading, the forecast and today's Daily Scoop."
      : `Tap play and your device's voice reads the official alerts and forecast for ${place.name}.`);
  }
})();
