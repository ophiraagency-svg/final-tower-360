# Residence guide: implementation report (15 Nov 2026)

## What changed
- `web/app/match.ts`: new rules-based guide logic (no AI).
  - Brief parsing understands "3m", "3 million", "3,000,000", "2 bed", sea/city, must, high floor, upfront.
  - Hard limits: available, bedrooms, total price, booking cash including DLD and fees, and a view marked "must". Everything else only changes the ranking.
  - Returns up to 3 matches spread across real alternatives, each with reasons and a trade-off.
  - When nothing fits, it says why and offers priced relaxations, but only ones that actually produce results.
  - Understands follow-ups: "the second one", "compare these", "payments", "cheaper".
- `web/app/Guide.tsx`: the guide panel.
  - Desktop: a 390 px panel on the right. Mobile: a bottom sheet.
  - One question at a time with tap options; a brief typed in one go skips the remaining questions.
  - Labelled "Guided demo", not AI.
  - Drives the tower only through a fixed set of actions. Every unit ID is checked again before any action runs.
- `web/app/Experience.tsx`:
  - New entry points: "Find my residence" in the intro and the dock, plus a one-time invitation after the film.
  - Floors with matches are marked on the tower and in the level grid.
  - Guide comparison is kept separate from the visitor's own shortlist.
  - Legend, keyboard-usable unit shapes on the plan, and a named list view.
  - "Through Dec 2027" window with its stated assumption (reservation in Nov 2026).
  - Request-a-call form: time windows in GST with the visitor's own time zone, editable preview, optional "include my brief", copy button. Nothing is sent until the visitor presses send in WhatsApp.
  - Broker routing comes only from `BROKERS` in `data.ts`; phone numbers in the URL are ignored. With no number configured, the button says "Share on WhatsApp".
  - The intro film no longer downloads on direct unit or shortlist links.
- `web/app/Tour.tsx`: changes to the 360° walk.
  - Only one panorama is kept on the GPU at a time (it used to warm three neighbours at about 40 MB each).
  - Pixel ratio capped at 1.5; WebGL context released on close; spots re-render only when they move.
  - Recovery screen when WebGL fails or the context is lost, plus Escape to close.
  - Labelled "Representative 2-bedroom layout · not unit-specific".
- `web/app/Orbit.tsx`:
  - Stops its loop while the tour is open or the tab is hidden.
  - Draws match bands on the tower.
  - Fixed a bug where, with no floor selected, everything except the tower was painted gold.
- `web/tests/match.test.ts`: 8 tests (`npm test`).

## Checks run
- `npm test`: 8/8 pass. Covers parsing, deterministic IDs, payment totals, hard limits, a unit sold after it was recommended, booking-cash limits, the honest 3M no-match, and commands.
- Headless Chrome end-to-end checks: 30/30 pass at 1440, 390 and 430 px.
  - Guided journey, "second one", payments, compare without overwriting the shortlist.
  - No-match and relaxation.
  - Prompt-injection text treated as data.
  - Known broker, unknown broker, and a phone number in the URL (ignored).
  - Invalid and duplicate IDs; refresh; keyboard selection; handoff only on submit.
  - 6 tour open/close cycles with no canvas build-up (JS heap 9 → 12 MB); no horizontal overflow on mobile.
- Without WebGL, the tour shows its recovery screen instead of breaking.
- The original "page couldn't load" was not reproduced. Most likely cause: up to 8 panoramas on the GPU plus the orbit loop running behind the tour. Both are fixed, but this was not confirmed on the auditor's machine.

## Load, measured
Conditions: headless Chrome on a fast connection, no throttling, 8 s after navigation.

| Page | Before (production) | After (local static build) |
|---|---|---|
| Desktop `/` | 7.2 MB | 7.2 MB (the film plays) |
| Desktop `?unit=2402` | 6.8 MB | 3.3 MB |
| Mobile `/` | 5.4 MB | 6.1 MB |
| Mobile `?unit=2402` | 1.5 MB | 2.2 MB |

Production serves the film with partial range requests, so the mobile figures are not directly comparable. Controls appear in under 1 s in every case. Mobile 3G was not tested.

## Not done (honest limits)
- **No live AI.** The site is a static export with no server or API key. Adding one needs a Vercel function plus `ANTHROPIC_API_KEY`, which would be a hosting change.
- **English only** (Arabic text displays right-to-left in the guide).
- **No real broker numbers.** `BROKERS.sara` is a sample entry with no number.
- **Analytics events** only show on a Vercel Pro plan.
- **Inventory, prices and the payment plan are sample data.**

## 90-second demo
1. Open the link and press **Find my residence** on the film.
2. Tap **To live in**, then **2 bedrooms**, **Up to AED 4.5M**, **Prefer Gulf & Downtown**. Three residences appear: 1602, 1002 and 405. Their floors light up on the tower.
3. Type "show me the second one". Residence 1002 opens on level 10.
4. Type "show the payments". AED 1,013,250 is due on booking, and AED 1,680,000 on handover.
5. Type "compare these", then **Prepare a message for an advisor** to show the time window in GST and the message preview.
6. To show an honest no-match: **Start again**, then type "2 bed, must have sea view, under 3m". The answer is that there is none, and the lowest is AED 3.80M. Tap **Raise budget to AED 3.80M**.
