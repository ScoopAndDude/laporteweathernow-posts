/* Darja (Algerian Arabic) phrasebook for laporteweathernow.com, used by /i18n.js.
 * Written September 28, 2026. Darja is written here in Arabic letters, in everyday Algerian
 * wording (not Moroccan, Egyptian or formal Arabic). Weather Service place names, station
 * codes, and brand names stay in English letters.
 *
 * - exact:    English text exactly as it shows on the page -> Darja.
 * - patterns: live wording from the Weather Service and the page's scripts (times, days,
 *             conditions, alert names). A pattern gives up (returns null) rather than guess,
 *             so anything unknown simply stays in English.
 * - pages:    paths this phrasebook covers completely by hand.
 * - fill:     "ar": on every page, whatever this phrasebook doesn't know is filled in by
 *             Google Translate in Arabic (Google has no Darja), so whole pages are translated.
 */
lpwnI18n.define("ar-DZ", function (api) {
  "use strict";
  var tr = api.tr;

  /* ---------- Days, months, clock times ---------- */
  var DAYS = {
    Sun: "الحد", Mon: "الاثنين", Tue: "الثلاثا", Wed: "الاربعا", Thu: "الخميس", Fri: "الجمعة", Sat: "السبت",
    Sunday: "الحد", Monday: "الاثنين", Tuesday: "الثلاثا", Wednesday: "الاربعا", Thursday: "الخميس", Friday: "الجمعة", Saturday: "السبت",
  };
  // Algeria uses the French-style month names.
  var MONTHS = {
    Jan: "جانفي", Feb: "فيفري", Mar: "مارس", Apr: "أفريل", May: "ماي", Jun: "جوان", Jul: "جويلية", Aug: "أوت",
    Sep: "سبتمبر", Sept: "سبتمبر", Oct: "أكتوبر", Nov: "نوفمبر", Dec: "ديسمبر",
    January: "جانفي", February: "فيفري", March: "مارس", April: "أفريل", June: "جوان", July: "جويلية",
    August: "أوت", September: "سبتمبر", October: "أكتوبر", November: "نوفمبر", December: "ديسمبر",
  };
  /** "7:45 AM" -> "7:45 تاع الصباح"; "3 PM" -> "3 تاع العشية". */
  function clock(s) {
    var m = /^(\d{1,2})(?::(\d{2}))?\s?([AaPp])\.?[Mm]\.?$/.exec(String(s).trim());
    if (!m) {
      if (/^noon$/i.test(s)) return "12 تاع النهار";
      if (/^midnight$/i.test(s)) return "نص الليل";
      return null;
    }
    var h = (+m[1] % 12) + (/p/i.test(m[3]) ? 12 : 0);
    if (h === 0 && !m[2]) return "نص الليل";
    if (h === 12 && !m[2]) return "12 تاع النهار";
    var part = h < 5 ? "تاع الليل" : h < 12 ? "تاع الصباح" : h < 14 ? "تاع النهار" : h < 19 ? "تاع العشية" : "تاع الليل";
    return m[1] + (m[2] ? ":" + m[2] : "") + " " + part;
  }
  /** "7:45 AM CDT" -> clock plus the zone letters, which stay as they are. */
  function clockZ(s) {
    var m = /^(\d{1,2}(?::\d{2})?\s?[AaPp]\.?[Mm]\.?)(?: ([A-Z]{2,5}|GMT[+-]\d{1,2}(?::\d{2})?))?$/.exec(String(s).trim());
    if (!m) return null;
    return clock(m[1]) + (m[2] ? " " + m[2] : "");
  }
  function monthDay(mon, day) { return MONTHS[mon] ? day + " " + MONTHS[mon] : null; }

  /* ---------- Places and stations ---------- */
  var PLACES = {
    "La Porte, IN": "لابورت، إنديانا", "La Porte": "لابورت", "La Porte area": "نواحي لابورت",
    "La Porte County, IN": "مقاطعة لابورت، إنديانا", "La Porte County": "مقاطعة لابورت", "LaPorte County": "مقاطعة لابورت",
    "Michigan City": "ميشيغان سيتي", "Michigan City, IN": "ميشيغان سيتي، إنديانا", "Indiana": "إنديانا",
  };
  function place(p) { return PLACES[p] || p; }
  var ARABIC = /^[\u0600-\u06ff]/;
  /** "for X": ل joins an Arabic word ("لمقاطعة", "للمقاطعة"); names in English letters or starting with لا get "لـ ". */
  function li(x) { return !ARABIC.test(x) || /^لا/.test(x) ? "لـ " + x : /^ال/.test(x) ? "ل" + x.slice(1) : "ل" + x; }
  /** "in X": ف joins an Arabic word ("فلابورت"); English letters get "فـ ". */
  function fi(x) { return ARABIC.test(x) ? "ف" + x : "فـ " + x; }
  var STATIONS = { "La Porte Municipal Airport": "مطار لابورت البلدي", "Michigan City Municipal Airport": "مطار ميشيغان سيتي البلدي", "Nearest NWS station": "أقرب محطة تاع الأرصاد" };
  var OFFICES = { "Northern Indiana": "شمال إنديانا", "Chicago IL": "شيكاغو", "Grand Rapids MI": "غراند رابيدز" };

  /* ---------- Weather wording (NWS forecasts and airport readings) ---------- */
  // Keys are lowercase; lookups are case-blind because the NWS mixes "Light Rain" and "light rain".
  var SKY = {
    "sunny": "شمس", "mostly sunny": "شمس مع شوية سحاب", "partly sunny": "شمس وسحاب",
    "partly cloudy": "شوية سحاب", "mostly cloudy": "سحاب بزاف", "cloudy": "مغيّمة", "overcast": "مغيّمة كاملة",
    "clear": "صافية", "mostly clear": "صافية تقريباً", "fair": "صافية", "a few clouds": "شوية سحاب",
    "increasing clouds": "السحاب راهو يزيد", "decreasing clouds": "السحاب راهو ينقص",
    "becoming sunny": "تولّي شمس", "becoming cloudy": "تولّي مغيّمة", "clearing": "تصفى", "gradual clearing": "تصفى شوية بشوية",
    "hot": "سخانة", "very hot": "سخانة بزاف", "cold": "برد", "very cold": "برد بزاف",
    "windy": "ريح قوية", "breezy": "شوية ريح", "blustery": "ريح قوية",
  };
  var CORE = {
    "showers and thunderstorms": "شتا ورعد", "thunderstorms": "عواصف رعدية", "thunderstorm": "عاصفة رعدية",
    "severe thunderstorms": "عواصف رعدية قوية", "light thunderstorms and rain": "رعد خفيف وشتا",
    "rain showers": "شتا متقطعة", "showers": "شتا متقطعة", "rain": "شتا", "light rain": "شتا خفيفة", "heavy rain": "شتا قوية",
    "drizzle": "رذاذ", "light drizzle": "رذاذ خفيف", "freezing drizzle": "رذاذ يتجمّد",
    "snow": "تلج", "light snow": "تلج خفيف", "heavy snow": "تلج بزاف", "snow showers": "تلج متقطع",
    "flurries": "شوية تلج", "blowing snow": "تلج مع الريح", "snow squalls": "عواصف تلج قصيرة",
    "rain and snow": "شتا وتلج", "rain and snow showers": "شتا وتلج متقطع", "wintry mix": "خليط تاع شتا وتلج",
    "sleet": "شتا فيها الجليد", "freezing rain": "شتا تتجمّد", "light freezing rain": "شتا خفيفة تتجمّد", "ice pellets": "حبات الجليد",
    "fog": "ضباب", "dense fog": "ضباب كثيف", "freezing fog": "ضباب يتجمّد", "fog/mist": "ضباب", "mist": "ضباب خفيف",
    "shallow fog": "ضباب خفيف", "partial fog": "ضباب فبعض البلايص", "patches of fog": "ضباب فبعض البلايص",
    "haze": "غبرة فالجو", "smoke": "دخان", "dust": "غبرة", "blowing dust": "غبرة مع الريح",
    "frost": "جليد", "hail": "التبروري", "squalls": "ريح قوية فجأة", "funnel cloud": "سحابة تاع تورنادو", "tornado": "تورنادو",
    "blizzard": "عاصفة تلج", "unknown precipitation": "حاجة تطيح من السما (شتا ولا تلج)",
  };
  var QUAL = {
    "slight chance": function (x) { return "احتمال صغير تاع " + x; },
    "chance": function (x) { return "يمكن " + x; },
    "isolated": function (x) { return x + " فبلايص قليلة"; },
    "scattered": function (x) { return x + " هنا وهنايا"; },
    "numerous": function (x) { return x + " فبلايص بزاف"; },
    "areas of": function (x) { return x + " فبلايص بزاف"; },
    "patchy": function (x) { return x + " فبعض البلايص"; },
    "widespread": function (x) { return x + " فكل بلاصة"; },
    "periods of": function (x) { return x + " على فترات"; },
    "occasional": function (x) { return x + " من وقت لوقت"; },
  };
  function core(x) {
    var k = String(x).toLowerCase().trim();
    if (CORE[k] != null) return CORE[k];
    if (SKY[k] != null) return SKY[k];
    var v = /^(.+) in vicinity$/.exec(k);
    if (v) { var c = core(v[1]); return c == null ? null : c + " فالنواحي"; }
    var bits = k.split(/\s+and\s+/);
    if (bits.length < 2) return null;
    var out = [];
    for (var i = 0; i < bits.length; i++) { var t = core(bits[i]); if (t == null) return null; out.push(t); }
    return out.join(" و");
  }
  function condPart(p) {
    var k = String(p).toLowerCase().trim();
    if (SKY[k] != null) return SKY[k];
    var m = /^(slight chance|chance|isolated|scattered|numerous|areas of|patchy|widespread|periods of|occasional)\s+(.+?)(\s+likely)?$/.exec(k) ||
      /^()(.+?)(\s+likely)$/.exec(k);
    if (m) {
      var c = core(m[2]);
      if (c == null) return null;
      var q = m[1] ? QUAL[m[1]](c) : c;
      return m[3] ? q + " على الأغلب" : q;
    }
    return core(k);
  }
  /** An NWS forecast phrase ("Patchy Fog then Mostly Sunny") or airport reading ("Fog/Mist"). */
  function cond(s) {
    if (!s) return null;
    var parts = String(s).split(/\s+then\s+/i);
    var out = [];
    for (var i = 0; i < parts.length; i++) { var t = condPart(parts[i]); if (t == null) return null; out.push(t); }
    return out.join("، ومن بعد ");
  }
  /** "5 mph" / "5 to 10 mph" */
  function wind(s) {
    var m = /^(\d+)(?: to (\d+))? mph$/.exec(String(s).trim());
    if (!m) return null;
    return (m[2] ? m[1] + " حتى " + m[2] : m[1]) + " mph";
  }
  var PRECIP = { "rain": "شتا", "snow": "تلج", "rain/snow": "شتا/تلج" };

  /* ---------- Official NWS alert names ---------- */
  var EVENTS = {
    "Special Weather Statement": "بيان خاص على الطقس",
    "Hazardous Weather Outlook": "نظرة على الطقس الخطير",
    "Severe Weather Statement": "بيان على الطقس القوي",
    "Flood Statement": "بيان على الفيضان", "Flash Flood Statement": "بيان على الفيضان المفاجئ",
    "Beach Hazards Statement": "بيان خطر فالبحيرة (الشط)",
    "Child Abduction Emergency": "طوارئ: اختطاف طفل", "Civil Emergency Message": "رسالة طوارئ مدنية",
    "Shelter In Place Warning": "إنذار: ابقاو داخل الدار", "Evacuation Immediate": "إخلاء: خرجو دروك",
    "Air Quality Alert": "تنبيه جودة الهوا",
  };
  // "Dense Fog Advisory" -> type word + hazard: "تنبيه ضباب كثيف", like a headline.
  var TYPES = { Warning: "إنذار", Watch: "مراقبة", Advisory: "تنبيه", Statement: "بيان", Emergency: "طوارئ", Outlook: "نظرة", Alert: "تنبيه" };
  var HAZARDS = {
    "Tornado": "تورنادو", "Severe Thunderstorm": "عواصف رعدية قوية", "Flash Flood": "فيضان مفاجئ", "Flood": "فيضان",
    "Coastal Flood": "فيضان فالساحل", "Lakeshore Flood": "فيضان على حاشية البحيرة", "Areal Flood": "فيضان",
    "Winter Storm": "عاصفة شتوية", "Winter Weather": "طقس شتوي (تلج ولا جليد)", "Blizzard": "عاصفة تلج", "Ice Storm": "عاصفة جليد",
    "Lake Effect Snow": "تلج البحيرة", "Snow Squall": "عاصفة تلج قصيرة", "Heavy Snow": "تلج بزاف",
    "Wind": "ريح قوية", "High Wind": "ريح قوية بزاف", "Extreme Wind": "ريح خطيرة", "Lake Wind": "ريح على البحيرة",
    "Wind Chill": "برد قوي مع الريح", "Extreme Cold": "برد خطير", "Cold Weather": "برد", "Hard Freeze": "تجمّد قوي",
    "Freeze": "تجمّد", "Frost": "جليد (فروست)", "Dense Fog": "ضباب كثيف", "Freezing Fog": "ضباب يتجمّد", "Dense Smoke": "دخان كثيف",
    "Heat": "سخانة", "Excessive Heat": "سخانة خطيرة", "Extreme Heat": "سخانة خطيرة",
    "Red Flag": "خطر الحرايق", "Fire Weather": "طقس الحرايق", "Rip Current": "تيارات خطيرة فالما", "Beach Hazards": "خطر فالبحيرة (الشط)",
    "Small Craft": "للبابورات الصغار", "Gale": "ريح قوية فالبحيرة", "Storm": "عاصفة", "Hurricane Force Wind": "ريح قوية كيما الإعصار",
    "Hurricane": "إعصار (هوريكان)", "Tropical Storm": "عاصفة استوائية", "Dust Storm": "عاصفة غبرة", "Blowing Dust": "غبرة مع الريح",
    "Freezing Spray": "رذاذ يتجمّد فالبحيرة", "Hydrologic": "الما والفيضانات", "Avalanche": "انهيار التلج",
  };
  function event(s) {
    if (EVENTS[s]) return EVENTS[s];
    var m = /^(.+) (Warning|Watch|Advisory|Statement|Emergency|Outlook|Alert)$/.exec(s);
    if (m && HAZARDS[m[1]]) return TYPES[m[2]] + " " + HAZARDS[m[1]];
    return null;
  }
  function alertCount(n) {
    n = +n;
    return n === 1 ? "كاين تنبيه رسمي" : n === 2 ? "كاين جوج تنبيهات رسمية" : "كاين " + n + " تنبيهات رسمية";
  }

  /* ---------- Exact phrases ---------- */
  var exact = {
    // Sept. 30, 2026 menu
    "WEEKEND": "الويكاند", "Weekend": "الويكاند", "FAITH": "الإيمان", "Tools": "الأدوات", "Learn": "تعلّم",
    "From Scoop": "من عند Scoop", "Amazon Watch": "مراقبة الأمازون", "World Art": "فنون العالم", "About": "علينا",
    // Header, menus, bottom bar
    "Skip to main content": "روح للمحتوى الرئيسي",
    "LA PORTE COUNTY'S LOCAL WEATHER · FREE FOR EVERYONE": "الطقس المحلي تاع مقاطعة لابورت · بلاش للناس الكل",
    "⚠️ Emergency": "⚠️ الطوارئ",
    "Our mission →": "الهدف تاعنا ←",
    "📲 Download App": "📲 نزّل التطبيق",
    "♥ Donate": "♥ تبرّع",
    "Main": "القائمة الرئيسية",
    "WEATHER": "الطقس", "ALERTS": "التنبيهات", "DAILY SCOOP": "النشرة اليومية", "LOCAL": "محلي",
    "GOLF": "الغولف", "HARD HAT": "الشانطي", "MORE": "المزيد",
    "This Weekend": "هاد الويكاند", "Storm Patterns": "أنواع العواصف", "Track Record": "سجل التوقعات",
    "Trip Planner": "نظّم سفريتك", "Camp Map": "خريطة الكامبينغ", "Travel Guides": "دلائل السفر",
    "Markets & Economy": "الأسواق والاقتصاد", "AI's Survival Guide": "دليل النجاة من الذكاء الاصطناعي", "AI Guide": "دليل الذكاء الاصطناعي", "Instagram": "إنستغرام", "Facebook": "فيسبوك", "Facebook group": "مجموعة فيسبوك", "Markets": "الأسواق", "World Disaster Watch": "مراقبة الكوارث فالعالم", "Disaster Watch": "مراقبة الكوارث", "World Disaster Watch": "مراقبة الكوارث فالعالم", "Disaster Watch": "مراقبة الكوارث", "Global weather": "الطقس فالعالم", "Global Weather": "الطقس فالعالم", "La Porte history": "تاريخ لابورت",
    "La Porte History": "تاريخ لابورت", "Our mission": "الهدف تاعنا", "Our Mission": "الهدف تاعنا", "Contact": "اتصل بينا",
    "Quick links": "روابط سريعة",
    "Weather": "الطقس", "Alerts": "التنبيهات", "Scoop": "النشرة", "Golf": "الغولف", "More": "المزيد",
    "Local": "محلي", "Hard Hat": "الشانطي",

    // Footer
    "Storm-smart weather for the Midwest, built on free public data. Not a replacement for official NWS warnings.":
      "طقس يفهم فالعواصف، للغرب الأوسط الأمريكي، مبني على معلومات عمومية بلاش. ما يعوّضش الإنذارات الرسمية تاع الأرصاد الجوية.",
    "Serve God. Serve people. Tell the truth. Be prepared. · Psalm 91": "اخدم ربي. اخدم الناس. قول الحق. كون واجد. · المزمور 91", "Love God. Love people. Tell the truth. Be prepared. Care for all that lives. · Matthew 22:37–39": "حب ربي. حب الناس. قول الحق. كون واجد. حافظ على كل ما فيه الروح. · متّى 22:37–39", "Faith & Ministry": "الإيمان والخدمة", "Our sources": "المصادر تاعنا", "World Disaster Watch & El Niño": "مراقبة الكوارث فالعالم و النينيو", "Faith": "الإيمان",
    "Right Now": "الطقس دروك", "Emergency view": "صفحة الطوارئ", "Daily Scoop": "النشرة اليومية",
    "Golf Weather": "طقس الغولف", "Global": "العالم", "World's Oldest Art": "أقدم فن فالعالم",
    "Hard Hat Weather for crews": "طقس الشانطي للخدامين", "Travel": "السفر", "La Porte": "لابورت",
    "Community": "المجتمع المحلي", "History": "التاريخ", "Privacy": "الخصوصية", "Follow": "تابعونا",
    "YouTube: live music with Scoop": "يوتيوب: موسيقى لايف مع سكوب", "Etsy Shop": "الحانوت تاعنا فـ Etsy",
    "Verify with NWS ↗": "تأكد من الأرصاد الجوية ↗",
    "Courthouse photo by MrHarman,": "تصويرة المحكمة من عند MrHarman،",
    ", via Wikimedia Commons": "، عبر Wikimedia Commons",
    "♥ Support This Site — Donate": "♥ عاونو هاد الموقع — تبرّعو",
    "🚐 Help Keep Us on the Road": "🚐 عاونونا نبقاو فالطريق",

    // Page titles (the part before " | La Porte Weather Now")
    "Free & Dog-Friendly Camp Map": "خريطة الكامبينغ (بلاش ويقبلو الكلاب)",
    "La Porte Community": "المجتمع المحلي فلابورت", "The Daily Scoop": "النشرة اليومية",
    "Emergency View": "الطوارئ", "Global Weather & News": "الطقس والأخبار فالعالم",
    "La Porte Golf Weather": "طقس الغولف فلابورت", "La Porte Local History": "تاريخ لابورت",
    "Travel & Survival Guides": "دلائل السفر والبقاء", "This Weekend in La Porte": "هاد الويكاند فلابورت",
    "The World's Oldest Art": "أقدم فن فالعالم",
    "La Porte Weather Now | LaPorte County Weather. Free. NWS.": "La Porte Weather Now | طقس مقاطعة لابورت. بلاش. من الأرصاد الجوية.",

    // Homepage: the first screen
    "LaPorte County Weather. Free. NWS.": "طقس مقاطعة لابورت. بلاش. من الأرصاد الجوية.",
    "Getting the temperature from the Weather Service": "قاعدين نجيبو الحرارة من الأرصاد الجوية",
    "Every Daily Scoop forecast is checked against the La Porte airport's weather station (KPPO), and the results are public.":
      "كل توقع فالنشرة اليومية نقارنوه مع محطة الطقس تاع مطار لابورت (KPPO)، والنتائج قدام الناس الكل.",
    "See how we've done →": "شوف كيفاش خدمنا ←",
    "Checking official NWS alerts": "قاعدين نشوفو التنبيهات الرسمية تاع الأرصاد",
    "🔔 Get free watch & warning alerts": "🔔 خذ تنبيهات المراقبة والإنذار بلاش",
    "7-day forecast": "التوقعات تاع 7 أيام",
    "National Weather Service": "الأرصاد الجوية الأمريكية (NWS)",
    "Official NWS forecast for La Porte, IN, in La Porte's local time.":
      "التوقعات الرسمية تاع الأرصاد لـ لابورت، إنديانا، بالتوقيت المحلي تاع لابورت. الحرارة بالسيلسيوس (°C) والريح بالكيلومتر فالساعة.",
    "Live from the National Weather Service, refreshed every 5 minutes.": "مباشرة من الأرصاد الجوية، تتجدد كل 5 دقايق.",
    "↻ Refresh now": "↻ جدّد دروك",
    "Refreshing…": "قاعد يتجدد…",
    "Not in La Porte? Check another town ↓": "ماكش فلابورت؟ شوف مدينة أخرى ↓",
    "Pause the loop": "وقّف الحركة", "Play the loop": "شغّل الحركة",
    "Latest NWS radar image from station KIWX, which covers La Porte County":
      "آخر تصويرة رادار من محطة KIWX تاع الأرصاد، اللي تغطي مقاطعة لابورت",
    "Source:": "المصدر:",
    ", the National Weather Service radar nearest the town you're viewing. The latest image shows first, then the animated loop once it has downloaded. If the loop looks frozen, the station may be between updates.":
      "، الرادار تاع الأرصاد الجوية الأقرب للمدينة اللي راك تشوف فيها. تبان آخر تصويرة هي الأولى، ومن بعد الرادار المتحرك كي يكمل التحميل. إذا بان الرادار واقف، يمكن المحطة بين تحديث وتحديث.",
    "Wind calm": "ماكانش ريح",
    "No current reading right now": "ماكانش قراءة دروك",
    "Today": "اليوم", "Tomorrow": "غدوة", "Tonight": "الليلة",
    "High": "الكبرى", ", low": "، الصغرى",
    "The 7-day forecast is unavailable right now.": "التوقعات تاع 7 أيام ماراهيش متوفرة دروك.",
    "The hourly forecast is unavailable right now.": "التوقعات ساعة بساعة ماراهيش متوفرة دروك.",
    "Check weather.gov ↗": "شوف weather.gov ↗",
    "Open the Emergency view →": "حل صفحة الطوارئ ←",
    "That doesn't mean there aren't any. Check your phone's emergency alerts or weather.gov.":
      "هادا ما يعنيش بلي ماكانش. شوف تنبيهات الطوارئ فالتيليفون تاعك ولا weather.gov.",
    "That doesn't mean there are no alerts. Check your phone's emergency alerts or weather.gov.":
      "هادا ما يعنيش بلي ماكانش تنبيهات. شوف تنبيهات الطوارئ فالتيليفون تاعك ولا weather.gov.",
    "Couldn't reach the Weather Service just now": "ما قدرناش نوصلو للأرصاد الجوية دروك",
    "Change town": "بدّل المدينة", "Back to La Porte": "ارجع لـ لابورت",

    // Around La Porte
    "AROUND LA PORTE": "فلابورت ونواحيها",
    "Your weather, your town, your day.": "الجو تاعك، مدينتك، نهارك.",
    "Every morning": "كل صباح",
    "La Porte's weather briefing in plain English: what's coming, how sure the forecast is, and what it means for your plans. Every forecast is scored in public.":
      "نشرة الطقس تاع لابورت، بالإنجليزية الساهلة: واش جاي، قدّاش التوقعات أكيدة، وواش تعني للبرامج تاعك. كل توقع نعطوه نقطة قدام الناس.",
    "Read today's Daily Scoop →": "اقرا نشرة اليوم ←",
    "Golfers": "لاعبين الغولف",
    "Today's best window to play in La Porte and Michigan City, the last tee time before dark, and wind hour by hour.":
      "أحسن وقت اليوم باش تلعب فلابورت وميشيغان سيتي، آخر وقت تبدا فيه قبل ما يطيح الليل، والريح ساعة بساعة.",
    "Check tee-time weather →": "شوف الطقس قبل ما تلعب ←",
    "Outdoor crews": "الخدامين برّا",
    "Hard Hat Weather": "طقس الشانطي",
    "Job-site weather calls for roofers, landscapers, concrete and other outdoor crews: start, shut down, protect, or all clear.":
      "قرارات الطقس للشانطي، للي يخدمو السقف، الجنانات، البيطون، وكل الخدامين برّا: ابداو، حبسو، احميو الخدمة، ولا كلش لاباس.",
    "See how it works →": "شوف كيفاش يخدم ←",
    "Local help & events": "مساعدة وأحداث محلية",
    "Help lines, city and county offices, the library and things to do around La Porte. Power out or storm damage? The":
      "أرقام المساعدة، مكاتب البلدية والمقاطعة، المكتبة، وواش تدير فلابورت ونواحيها. الضو مقطوع ولا العاصفة خسّرت حاجة؟",
    "has NIPSCO, sheriff and emergency management numbers.": "فيها أرقام NIPSCO (الضو)، الشريف، ومصلحة الطوارئ.",
    "Local resources →": "المساعدة المحلية ←",

    // Hour by hour
    "HOUR BY HOUR": "ساعة بساعة",
    "What today's weather means for your plans.": "واش يعني طقس اليوم للبرامج تاعك.",
    "Automated guidance built from the current NWS forecast — not an emergency warning. Always confirm with official alerts before you commit to a route or campsite.":
      "نصائح أوتوماتيكية مبنية على توقعات الأرصاد تاع دروك — ماشي إنذار طوارئ. ديما تأكد من التنبيهات الرسمية قبل ما تختار طريق ولا بلاصة كامبينغ.",
    "Plan a whole route in the Trip Planner →": "نظّم طريق كامل فمخطط السفرية ←",
    "Best of next 8 hours": "الأحسن فـ 8 ساعات الجاية",
    "Driving Window": "أحسن وقت للسياقة",
    "Next 12 hours": "12 ساعة الجاية",
    "Highest Storm Risk": "أكبر خطر تاع عاصفة",
    "GOOD": "مليح", "CAUTION": "رد بالك", "POOR": "ماشي مليح",
    "Overnight / Boondocking Comfort": "الراحة فالليل / الكامبينغ الحر",
    "Official": "رسمي",
    "Alert Status": "حالة التنبيهات",
    "No active NWS alerts returned": "ماكانش حتى تنبيه رسمي",
    "Active NWS alert(s) —": "كاين تنبيهات رسمية —",
    "open the Emergency view": "حل صفحة الطوارئ",
    "Couldn't check NWS alerts —": "ما قدرناش نشوفو التنبيهات —",
    "try the Emergency view": "جرّب صفحة الطوارئ",
    "Couldn't reach the Weather Service": "ما قدرناش نوصلو للأرصاد الجوية",
    "Tap Refresh now in a minute": "اضغط «جدّد دروك» من بعد دقيقة",
    "Or read": "ولا اقرا",
    "today's Daily Scoop": "نشرة اليوم",
    ", our written forecast.": "، التوقعات المكتوبة تاعنا.",

    // Heading out of town
    "HEADING OUT OF TOWN? · STORM & TRAVEL WEATHER": "خارج من المدينة؟ · طقس العواصف والسفر",
    "Know the weather before the road does.": "اعرف الجو قبل ما تلقاه فالطريق.",
    "Driving, camping or visiting family? Check the official NWS forecast for any US town, plan a route stop by stop, and find free camping, so you can plan around storms instead of getting caught by them.":
      "راك سايق، رايح للكامبينغ، ولا تزور العايلة؟ شوف التوقعات الرسمية تاع الأرصاد لأي مدينة فأمريكا، نظّم طريقك وقفة بوقفة، ولقى كامبينغ بلاش، باش تهرب من العواصف بلاصة ما تحكمك.",
    "Where do you want to start?": "منين تحب تبدا؟",
    "🏠 La Porte local": "🏠 لابورت",
    "Weather at home": "الطقس فالدار",
    "Current conditions, official alerts, radar, and the 7-day for La Porte, plus local resources and history.":
      "الجو دروك، التنبيهات الرسمية، الرادار، والتوقعات تاع 7 أيام لـ لابورت، مع المساعدة المحلية والتاريخ.",
    "🚐 Planning a trip": "🚐 راك تحضّر لسفرية",
    "Weather along your route": "الطقس على طول طريقك",
    "See the forecast at each stop for the hour you'll be there, find free camping, and get a go / caution call.":
      "شوف التوقعات فكل وقفة على الساعة اللي تكون فيها تما، لقى كامبينغ بلاش، وخذ القرار: روح ولا رد بالك.",
    "Check any US town or city": "شوف أي مدينة فأمريكا",
    "e.g. Traverse City, MI": "مثلاً: Traverse City, MI",
    "Or pick a hub": "ولا اختار مدينة كبيرة",
    "Midwest (Home)": "الغرب الأوسط (الدار)", "Midwest": "الغرب الأوسط", "Northeast": "الشمال الشرقي",
    "Southeast": "الجنوب الشرقي", "South": "الجنوب", "Mountain West": "الغرب الجبلي", "Southwest": "الجنوب الغربي",
    "Pacific Northwest": "الشمال الغربي", "West Coast": "الساحل الغربي", "Other": "أخرى",
    "Search failed — try again": "التلواج ما خدمش — عاود جرّب",
    "Read today's Daily Scoop": "اقرا نشرة اليوم",
    "⚠️ Emergency view": "⚠️ صفحة الطوارئ",
    "Find free camping nearby": "لقى كامبينغ بلاش قريب منك",

    // Camping, storm patterns, guides
    "Live from OpenStreetMap": "مباشرة من OpenStreetMap",
    "Free camping & dog-friendly spots near you.": "كامبينغ بلاش وبلايص يقبلو الكلاب قريب منك.",
    "An interactive map of free public camping areas, plus a curated list of driveway and private-yard hosts for the nights a campground isn't nearby.":
      "خريطة تفاعلية فيها بلايص الكامبينغ العمومية بلاش، ومعاها قائمة مختارة تاع ناس يستقبلوك قدام الدار ولا فالحوش، فالليالي اللي ما يكونش فيها كامبينغ قريب.",
    "Open the camp map →": "حل خريطة الكامبينغ ←",
    "STORM PATTERNS": "أنواع العواصف",
    "Understand the Midwest's biggest weather risks.": "افهم أكبر مخاطر الطقس فالغرب الأوسط الأمريكي.",
    "Browse the Storm Patterns library →": "شوف المكتبة تاع أنواع العواصف ←",
    "Tornado Season": "موسم التورنادو",
    "Why Tornado Alley keeps creeping east": "علاش «ممر التورنادو» راهو يزحف للشرق",
    "What a 2018 study found about tornado activity shifting toward the Midwest and Southeast — and how to build a watch-vs-warning habit before you're on the road.":
      "واش لقات دراسة تاع 2018 على التورنادو اللي راهو يتحوّل للغرب الأوسط والجنوب الشرقي — وكيفاش تتعوّد تفرّق بين «المراقبة» و«الإنذار» قبل ما تكون فالطريق.",
    "Read the explainer →": "اقرا الشرح ←",
    "Lake Effect": "أثر البحيرة",
    "Lake-effect snow, explained for travelers": "تلج البحيرة، مشروح للمسافرين",
    "How the Great Lakes turn a clear forecast into a whiteout in miles — and why the lakeshore snow belts get hit hardest.":
      "كيفاش البحيرات الكبار يقلبو توقعات صافية لتلج ما تشوف فيه والو فبضعة أميال — وعلاش المناطق اللي على حاشية البحيرة هي اللي تاكلها أكثر.",
    "Derecho Risk": "خطر الديريتشو",
    "Derechos: fast-moving storms that can bring hurricane-force winds": "الديريتشو: عواصف تمشي بالزربة وتقدر تجيب ريح قوية كيما الإعصار",
    "Derechos move fast and hit hard. Here's how to watch for the setup hours ahead in free Storm Prediction Center outlooks.":
      "الديريتشو يمشي بالزربة ويضرب قوي. هاكا كيفاش تشوفو جاي ساعات قبل، فالتوقعات المجانية تاع مركز توقع العواصف (SPC).",
    "Already on the road? Be ready before the storm is.": "راك فالطريق؟ كون واجد قبل ما تكون العاصفة واجدة.",
    "Our printable survival and storm-prep planners go deeper than any app — region-specific disaster protocols and grid-down checklists. (The van build guide is still in the works.)":
      "الكراريس تاعنا اللي تتطبع، على البقاء والتحضير للعواصف، يروحو أبعد من أي تطبيق — خطوات للكوارث حسب كل منطقة، وقوائم لوقت ما تنقطع الضو. (الدليل تاع تجهيز الفان مازال ما كملش.)",
    "See the guides →": "شوف الدلائل ←",

    // Newsletter (several pages)
    "La Porte County weather, in your inbox.": "طقس مقاطعة لابورت، فالإيمايل تاعك.",
    "Storm-season updates, the week's pattern ahead, and new storm-prep guides. Add your town (optional) so we can include it as town-by-town outlooks roll out. Free, unsubscribe anytime.":
      "أخبار موسم العواصف، واش جاي فالسيمانة، ودلائل جديدة للتحضير للعواصف. زيد المدينة تاعك (كون حبيت) باش ندخلوها كي نبداو التوقعات مدينة بمدينة. بلاش، وتقدر تحبس وقتاش ما حبيت.",
    "Don't fill this out:": "ما تعمّرش هادي:",
    "Email address": "الإيمايل",
    "Your town (optional)": "المدينة تاعك (كون حبيت)",
    "Join the list": "سجّل روحك",
    "We only use your email for this newsletter.": "الإيمايل تاعك نستعملوه غير لهاد النشرة.",
    "Thanks, you're on the list! Watch your inbox for the next update.": "صحّيت، راك فالقائمة! شوف الإيمايل تاعك فالتحديث الجاي.",
    "Sorry, that didn't go through. Please try again in a minute.": "سمحلي، ما تبعثتش. عاود جرّب من بعد دقيقة.",

    // "Download App" window (pwa.js)
    "📲 Get the La Porte Weather Now app": "📲 خذ التطبيق تاع La Porte Weather Now",
    "Free, no app store needed. It opens full-screen from your home screen and always shows the latest forecast.":
      "بلاش، ما تحتاجش ستور. يتحل فالشاشة كاملة من الشاشة الرئيسية، ويوريك ديما آخر التوقعات.",
    "Open this site in": "حل هاد الموقع فـ",
    "Tap the": "اضغط على",
    "Share": "مشاركة",
    "button (square with an up arrow)": "(الزر اللي فيه مربع وسهم لفوق)",
    "Tap": "اضغط على",
    "Add to Home Screen": "إضافة إلى الشاشة الرئيسية",
    ", then": "، ومن بعد",
    "Add": "إضافة",
    "Android & computers (Chrome or Edge)": "أندرويد والكمبيوتر (Chrome ولا Edge)",
    "Open the browser menu (": "حل القائمة تاع المتصفح (",
    "Install app": "تثبيت التطبيق",
    "or": "ولا",
    "Add to Home screen": "الإضافة إلى الشاشة الرئيسية",
    "iPhone / iPad": "آيفون / آيباد",
    "Got it": "فهمت",
    "Back to the top of the page": "ارجع لفوق الصفحة",
    "Top": "لفوق",

    // Free watch & warning alerts window (alerts.js)
    "🔔 Free watch & warning alerts": "🔔 تنبيهات المراقبة والإنذار، بلاش",
    "On iPhone or iPad:": "فالآيفون ولا الآيباد:",
    "alerts only work from the Home Screen app. Tap": "التنبيهات تخدم غير من التطبيق اللي فالشاشة الرئيسية. اضغط على",
    "Download App": "نزّل التطبيق",
    "at the top of the page, add it to your Home Screen, open it from there, and turn alerts on.":
      "لفوق فالصفحة، زيدو للشاشة الرئيسية، حلّو من تما، وشعّل التنبيهات.",
    "This browser can't show notifications. Try Chrome, Edge, Firefox or Safari.":
      "هاد المتصفح ما يقدرش يوري الإشعارات. جرّب Chrome، Edge، Firefox ولا Safari.",
    "Your counties": "المقاطعات تاعك",
    "Add another county: type a town": "زيد مقاطعة أخرى: اكتب اسم مدينة",
    "e.g. Canton, GA": "مثلاً: Canton, GA",
    "Turn off all alerts": "طفّي التنبيهات الكل",
    "Alerts usually arrive within about 5 minutes of the NWS. Your phone's own emergency alerts are faster, so keep those on too. Notifications come through OneSignal; see our":
      "التنبيهات توصل عادة فحوالي 5 دقايق من بعد الأرصاد. تنبيهات الطوارئ تاع التيليفون تاعك أسرع، خليهم شاعلين تاني. الإشعارات يجيو عبر OneSignal؛ شوف",
    "privacy page": "صفحة الخصوصية",
    "Close": "سكّر",
    "Remove": "نحّي",
    "None yet. Add your county below.": "مازال والو. زيد المقاطعة تاعك لتحت.",
    "Asking your browser for permission…": "راني نطلب الإذن من المتصفح…",
    "Notifications are blocked for this site. Allow them in your browser or phone settings for laporteweathernow.com, then try again.":
      "الإشعارات مبلوكيين لهاد الموقع. سمح بيهم فالإعدادات تاع المتصفح ولا التيليفون لـ laporteweathernow.com، ومن بعد عاود جرّب.",
    "That didn't work. Check your connection and try again.": "ما خدمتش. شوف الكونيكسيون وعاود جرّب.",
    "Turning alerts off…": "راني نطفّي التنبيهات…",
    "Alerts are off. You won't get any more notifications from us.": "التنبيهات طافية. ما يوصلك حتى إشعار من عندنا.",
    "The alert service didn't load.": "خدمة التنبيهات ما تحمّلتش.",

    // Seasonal lines (seasonal.js)
    "🎃 Storm season meets spooky season — same free, reliable forecast, just a little creepier out there.":
      "🎃 موسم العواصف جا مع موسم الهالوين — نفس التوقعات، بلاش ومضمونة، غير الجو برّا يخوّف شوية.",
    "Throwing a Halloween party? Get our Haunted Happy Hour kit →": "عندك حفلة هالوين؟ شوف الكيت تاعنا فـ Etsy ←",
    "🦃 Giving thanks for reliable weather data, free public sources, and safe travels this season.":
      "🦃 نحمدو ربي على معلومات الطقس المضمونة، المصادر العمومية البلاش، والسفر بالسلامة فهاد الموسم.",
    "❄️ Winter storm season is here — check road and travel conditions before you head out.":
      "❄️ جا موسم العواصف تاع الشتا — شوف حالة الطريق والسفر قبل ما تخرج.",
  };
  var SEASON = { "🎃 SPOOKY SEASON": "🎃 موسم الهالوين", "🦃 HARVEST SEASON": "🦃 موسم الحصاد", "❄️ WINTER WATCH": "❄️ رد بالك من الشتا" };

  /* ---------- Patterns (checked in order; the first that answers wins) ---------- */
  var patterns = [
    // Page titles
    [/^(.+) \| La Porte Weather Now$/, function (m) { var t = tr(m[1]); return t ? t + " | La Porte Weather Now" : null; }],
    // Seasonal prefix on the top bar (the rest may already be translated)
    [/^(🎃 SPOOKY SEASON|🦃 HARVEST SEASON|❄️ WINTER WATCH) · (.+)$/, function (m) { return SEASON[m[1]] + " · " + (tr(m[2]) || m[2]); }],

    // Alerts button and banner
    [/^🔔 Alerts on: (.+?)(?: \+ (\d+) more)?$/, function (m) { return "🔔 التنبيهات شاعلة: " + place(m[1]) + (m[2] ? " + " + m[2] + " أخرين" : ""); }],
    [/^No active NWS alerts for (.+)$/, function (m) { return "ماكانش حتى تنبيه رسمي دروك " + fi(place(m[1])); }],
    [/^Checked (.+?) for the (.+) forecast point\.$/, function (m) { var c = clockZ(m[1]); return c ? "شفنا على " + c + " فنقطة التوقعات تاع " + place(m[2]) + "." : null; }],
    [/^Couldn't check NWS alerts for (.+) just now$/, function (m) { return "ما قدرناش نشوفو تنبيهات الأرصاد " + li(place(m[1])) + " دروك"; }],
    [/^(\d+) active NWS alerts?: (.+)$/, function (m) { return alertCount(m[1]) + ": " + (event(m[2]) || m[2]); }],
    [/^(.+?) issued (\w+) (\d{1,2}) at (\d{1,2}:\d{2}\s?[AP]M) (\w{3}) until (\w+) (\d{1,2}) at (\d{1,2}:\d{2}\s?[AP]M) (\w{3}) by NWS (.+)$/, function (m) {
      var e = event(m[1]), d1 = monthDay(m[2], m[3]), d2 = monthDay(m[6], m[7]), c1 = clock(m[4]), c2 = clock(m[8]);
      if (!e || !d1 || !d2 || !c1 || !c2) return null;
      return e + ": خرج " + d1 + " على " + c1 + " " + m[5] + "، ويدوم حتى " + d2 + " على " + c2 + " " + m[9] + ". من الأرصاد الجوية (" + (OFFICES[m[10]] || m[10]) + ").";
    }],
    [/^(.+?) issued (\w+) (\d{1,2}) at (\d{1,2}:\d{2}\s?[AP]M) (\w{3}) by NWS (.+)$/, function (m) {
      var e = event(m[1]), d1 = monthDay(m[2], m[3]), c1 = clock(m[4]);
      if (!e || !d1 || !c1) return null;
      return e + ": خرج " + d1 + " على " + c1 + " " + m[5] + ". من الأرصاد الجوية (" + (OFFICES[m[6]] || m[6]) + ").";
    }],
    [/^[A-Z][A-Za-z ]+ (?:Warning|Watch|Advisory|Statement|Emergency|Outlook|Alert|Message)$/, function (m) { return event(m[0]); }],

    // The big number: wind and humidity, and which station it came from
    [/^(?:Wind calm|Wind \d+ mph(?:, gusts \d+)?|Humidity \d+%)(?: · (?:Wind calm|Wind \d+ mph(?:, gusts \d+)?|Humidity \d+%))*$/, function (m) {
      return m[0].split(" · ").map(function (p) {
        var w = /^Wind (\d+) mph(?:, gusts (\d+))?$/.exec(p), h = /^Humidity (\d+)%$/.exec(p);
        if (p === "Wind calm") return "ماكانش ريح";
        if (w) return "الريح " + w[1] + " mph" + (w[2] ? "، وتضرب حتى " + w[2] + " mph" : "");
        return "الرطوبة " + h[1] + "%";
      }).join(" · ");
    }],
    [/^(.+?) \(([A-Z0-9]{3,5})\) · (.+)$/, function (m) { var c = clockZ(m[3]); return c ? (STATIONS[m[1]] || m[1]) + " (" + m[2] + ") · " + c : null; }],
    [/^(Nearest NWS station|La Porte Municipal Airport|Michigan City Municipal Airport) · (.+)$/, function (m) { var c = clockZ(m[2]); return c ? STATIONS[m[1]] + " · " + c : null; }],
    [/^(La Porte Municipal Airport|Nearest NWS station)$/, function (m) { return STATIONS[m[1]]; }],

    // 7-day and hourly cards
    [/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec) (\d{1,2})$/, function (m) { return monthDay(m[1], m[2]); }],
    [/^(Sun|Mon|Tue|Wed|Thu|Fri|Sat|Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)$/, function (m) { return DAYS[m[1]]; }],
    [/^Low (-?\d+)°$/, "الصغرى $1°"],
    [/^(\d+)% (rain|snow|rain\/snow)$/, function (m) { return PRECIP[m[2]] + " " + m[1] + "%"; }],
    [/^\d{1,2}(?::\d{2})? ?[AP]M$/, function (m) { return clock(m[0]); }],
    [/^, (.+)$/, function (m) { var c = cond(m[1]); return c ? "، " + c : null; }, ".hour-card"],
    [/^Official NWS forecast for (.+)\. Days and times are (.+) local time \((.+)\)\.$/, function (m) {
      return "التوقعات الرسمية تاع الأرصاد " + li(place(m[1])) + ". الأيام والأوقات بالتوقيت المحلي تاع " + place(m[2]) + " (" + m[3] + "). الحرارة بالسيلسيوس (°C) والريح بالكيلومتر فالساعة.";
    }],

    // Route and camp cards
    [/^(-?\d+)° · (\d+)% (rain|snow|rain\/snow) · (.+) wind$/, function (m) { var w = wind(m[4]); return w ? m[1] + "° · " + PRECIP[m[3]] + " " + m[2] + "% · ريح " + w : null; }],
    [/^(\d+)% precipitation chance · (.+)$/, function (m) { return "احتمال الشتا " + m[1] + "% · " + (cond(m[2]) || m[2]); }],
    [/^(.+?) wind · (.+)$/, function (m) { var w = wind(m[1]); return w ? "ريح " + w + " · " + (cond(m[2]) || m[2]) : null; }],

    // Updated line, radar, other towns
    [/^Live from the NWS · updated (.+?) · refreshes every 5 minutes$/, function (m) { var c = clockZ(m[1]); return c ? "مباشرة من الأرصاد · تبدّلت على " + c + " · تتجدد كل 5 دقايق" : null; }],
    [/^Couldn't update just now \((.+?)\)\.( The numbers above are the last reading saved on this device; its time is next to the temperature\.)?$/, function (m) {
      var c = clockZ(m[1]);
      return c ? "ما قدرناش نجددو دروك (" + c + ")." + (m[2] ? " الأرقام اللي لفوق هي آخر قراءة محفوظة فهاد الجهاز؛ الوقت تاعها حدا الحرارة." : "") : null;
    }],
    [/^Live radar: (.+)$/, function (m) { return "الرادار مباشر: " + place(m[1]); }],
    [/^Radar unavailable for (.+)$/, function (m) { return "الرادار ماكانش " + li(place(m[1])); }],
    [/^Latest NWS radar image from station ([A-Z0-9]{4}) near (.+)$/, function (m) { return "آخر تصويرة رادار من محطة " + m[1] + " قريب من " + place(m[2]); }],
    [/^Animated NWS radar loop from station ([A-Z0-9]{4}) near (.+)$/, function (m) { return "رادار متحرك من محطة " + m[1] + " قريب من " + place(m[2]); }],
    [/^(.+) Weather\. Free\. NWS\.$/, function (m) { return "طقس " + place(m[1]) + ". بلاش. من الأرصاد الجوية."; }],
    [/^Showing (.+)\.$/, function (m) { return "راك تشوف " + place(m[1]) + "."; }],
    [/^Your saved trip: (.+?) → (.+?)(?: · (Sun|Mon|Tue|Wed|Thu|Fri|Sat) (\w{3,4}) (\d{1,2}))? →$/, function (m) {
      var when = m[3] ? " · " + DAYS[m[3]] + " " + (monthDay(m[4], m[5]) || m[4] + " " + m[5]) : "";
      return "السفرية المحفوظة: من " + place(m[1]) + " " + li(place(m[2])) + when + " ←";
    }],

    // Town search
    [/^No US towns found for "(.*)"$/, function (m) { return "ما لقينا حتى مدينة فأمريكا بهاد الاسم: «" + m[1] + "»"; }],
    [/^Not there\? Add the state, like "(.*)"\.$/, function (m) { return "ماراهيش هنا؟ زيد الولاية، كيما «" + m[1] + "»."; }],
    [/^(.+) \(searched\)$/, function (m) { return m[1] + " (من التلواج)"; }],

    // Free alerts window
    [/^Get a notification on this phone or computer when the National Weather Service issues a watch or warning for your county, anywhere in the U\.S\. Free, with no account and no email address\. Follow up to (\d+) counties: home, work, family\.$/, function (m) {
      return "يوصلك إشعار فهاد التيليفون ولا الكمبيوتر كي الأرصاد الجوية تخرّج «مراقبة» ولا «إنذار» للمقاطعة تاعك، وين ما كنت فأمريكا. بلاش، بلا حساب وبلا إيمايل. تقدر تتبع حتى " + m[1] + " مقاطعات: الدار، الخدمة، العايلة.";
    }],
    [/^You're following (\d+) counties, the most we can send to one device\. Remove one to add another\.$/, function (m) {
      return "راك تتبع " + m[1] + " مقاطعات، هادا الأكثر اللي نقدرو نبعثو لجهاز واحد. نحّي وحدة باش تزيد أخرى.";
    }],
    [/^Add (.+ (?:County|Parish|Borough|Census Area|Municipality)(?:, [A-Z]{2})?|.+, (?:AK|DC|PR))$/, function (m) { return "زيد " + place(m[1]); }],
    [/^You're already following (.+)\.$/, function (m) { return "راك ديجا تتبع " + place(m[1]) + "."; }],
    [/^Alerts are on for (.+)\.$/, function (m) { return "التنبيهات شاعلة " + li(place(m[1])) + "."; }],
    [/^Removed (.+)\.$/, function (m) { return "نحّينا " + (m[1] === "that county" ? "هاد المقاطعة" : place(m[1])) + "."; }],
    [/^Finding the county for (.+)…$/, function (m) { return "راني نلوّج على المقاطعة تاع " + m[1] + "…"; }],
    [/^We couldn't find a U\.S\. county for (.+)\. Try a nearby town\.$/, function (m) { return "ما لقيناش مقاطعة فأمريكا " + li(m[1]) + ". جرّب مدينة قريبة."; }],

    // Weather wording shown on its own: the airport reading and forecast cards only
    [/^.+$/, function (m) { return cond(m[0]); }, "#nowCond, .wk-card .c, .hour-card, .decision-card .detail"],
  ];

  return {
    pages: ["/"],
    fill: "ar",
    exact: exact,
    patterns: patterns,
    notice: function (href) {
      return "هاد الصفحة بالدارجة. واش ماكانش فالقاموس تاعنا، Google يترجمو أوتوماتيكيا بالعربية الفصحى، وساعات يغلط شوية. " +
        '<a href="' + href("en") + '" lang="en" dir="ltr">English</a>';
    },
  };
});
