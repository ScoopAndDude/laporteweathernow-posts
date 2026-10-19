# The "Ask us" website helper

A small chat button for the websites Scoop builds for local businesses (added Oct. 19, 2026; Scoop: "do all of these
suggestions"). Visitors ask about hours, services, the area the business covers, or how to get a quote, and get a
short answer in a few seconds from that business's own fact sheet. Anything the fact sheet doesn't cover, and
anything that needs a person (quotes, scheduling, complaints), goes to the business's phone, text, email or quote
page. It never makes up prices, times or promises.

- Demo: https://scoopanddude.github.io/laporteweathernow-posts/helper/demo.html (a made-up business, "demo-lawn").
- Answers are written by Claude (Haiku 5.5) on the monthly Claude API credit that comes with Scoop's Max plan
  (the "Website Helper" workspace in the Claude Console, spend limit $10 a month). An answer costs a small
  fraction of a cent.

## Adding it to a client's site

1. Add the business to `sites.json` here: a new key (lowercase letters, numbers and dashes, like `keene-roofing`)
   with `name`, `greeting`, `services`, `area`, `hours`, `phone`, `text`, `email`, `quoteUrl` (an https page, or
   blank), `faqs` (`{ "q", "a" }` pairs), `notOffered`, `notes`, and `color` (`#rrggbb`). Only facts the business
   gave you: the helper answers from these and nothing else. It's live within 10 minutes of the push.
2. Put one line on their site, just before `</body>`:

   ```html
   <script src="https://scoopanddude.github.io/laporteweathernow-posts/helper/ask.js" data-site="keene-roofing" defer></script>
   ```

   Options: `data-color="#1f7a4d"` (the button's color), `data-open="true"` (starts open), `data-credit="off"`
   (hides the small "Helper by La Porte Weather Now" link).
3. To switch a business off (they stopped paying, say), set `"active": false` in `sites.json`.

## How it works

- `ask.js`: the button and chat box, drawn in its own shadow root so the client's styles can't bend it. It reads
  `sites.json` for the business's name, greeting, color and contact buttons, and sends each question to the
  backend. Answers are shown as plain text, never HTML.
- `backend.gs`: a Google Apps Script web app that holds the Claude key (the `ANTHROPIC_API_KEY` script property)
  and asks Claude. It's the "Ask helper" file in the "LPWN timer" project (laporteweathernow@gmail.com), which
  already had the permission it needs. Free, and it never touches laporteweathernow.com's Netlify credits. Setup
  steps are at the top of the file. After changing it: Deploy > Manage deployments > edit > Version: New version
  (the address stays the same). A syntax error in any file stops the whole project, the timer too, so run the
  tests first.
- Limits: 200 questions per business per day (`dailyCap` in `sites.json` changes it), 1,000 a day in all, 25 per
  visitor, 500 characters per question. The workspace's spend limit is the backstop.
- Counts: run `askShowCounts` in the Apps Script editor to see today's and this month's questions per business
  (handy for a monthly note to the client). Each question and answer is also in Executions (View > Executions).
- Tests: `node tools/helper/test_helper.js` (no network).
