// Residence guide: buyer brief → deterministic matching over the one sample inventory.
// No AI here: parsing is rules-based, availability and money always come from data.ts.
import { FLOORS, unitsOn, payments, aed } from "./data.ts";
import type { Unit } from "./data.ts";

export type Purpose = "live" | "invest" | "explore";
export type Brief = {
  purpose?: Purpose; beds?: 1 | 2 | 3; budget?: number; upfront?: number;
  view?: "Sea" | "City"; viewMust?: boolean; high?: boolean; large?: boolean;
};
export type Match = { u: Unit; reasons: string[]; tradeoff?: string };
export type Result =
  | { kind: "matches"; items: Match[]; total: number }
  | { kind: "none"; why: string; options: { label: string; patch: Partial<Brief> }[] };

export const ALL = (): Unit[] => [...Array(FLOORS)].flatMap((_, i) => unitsOn(i + 1));
const viewName = (s: Unit["side"]) => (s === "Sea" ? "Gulf & Downtown" : "city & marina");

// "3m", "3 million", "3,000,000", "2.5M", "800k" → AED integer. Bare numbers under 1,000 are not money.
export function money(t: string): number | undefined {
  const m = /(\d+(?:[.,]\d+)*)\s*(m\b|mn\b|million|k\b|thousand)?/i.exec(t.replace(/aed/gi, ""));
  if (!m) return;
  let n = parseFloat(m[1].replace(/,(?=\d{3}\b)/g, "").replace(",", "."));
  const unit = (m[2] || "").toLowerCase();
  if (unit.startsWith("m")) n *= 1e6; else if (unit.startsWith("k") || unit.startsWith("t")) n *= 1e3;
  return n >= 1000 ? Math.round(n) : undefined;
}

// Free text → brief changes. Unknown things stay unknown.
export function parse(text: string): Partial<Brief> {
  const t = text.toLowerCase(), out: Partial<Brief> = {};
  const b = /\b(1|2|3|one|two|three)\s*-?\s*(bed|br|bedroom|bdr)/.exec(t);
  if (b) out.beds = ({ one: 1, two: 2, three: 3 } as Record<string, 1 | 2 | 3>)[b[1]] ?? (+b[1] as 1 | 2 | 3);
  const cash = /(upfront|up front|booking|down ?payment|deposit|cash now)/.test(t);
  const amount = money(t.replace(/\b[123]\s*-?\s*(bed|br|bedroom|bdr)\w*/g, ""));
  if (amount) out[cash ? "upfront" : "budget"] = amount;
  if (/\b(sea|gulf|water|beach|downtown|skyline)\b/.test(t)) out.view = "Sea";
  else if (/\b(city|marina)\b/.test(t)) out.view = "City";
  if (out.view && /\b(must|only|need|required)\b/.test(t)) out.viewMust = true;
  if (/\b(high|higher|top)\s*(floor|level)|\bup high\b/.test(t)) out.high = true;
  if (/\b(large|larger|bigger|spacious|more space)\b/.test(t)) out.large = true;
  if (/\b(live|living|family|home|move in|myself)\b/.test(t)) out.purpose = "live";
  else if (/\b(invest|investment|rental|rent out|yield|roi)\b/.test(t)) out.purpose = "invest";
  else if (/\b(explor|just looking|browsing)/.test(t)) out.purpose = "explore";
  return out;
}

// Hard limits: available, bedrooms, total price, booking cash, a view marked "must". Everything else only ranks.
function fits(u: Unit, b: Brief) {
  return u.status === "Available" && (!b.beds || +u.type[0] === b.beds) && (!b.budget || u.price <= b.budget)
    && (!b.upfront || payments(u).now <= b.upfront) && (!b.viewMust || u.side === b.view);
}

function score(u: Unit, b: Brief) {
  let s = 0;
  if (b.view) s += u.side === b.view ? 3 : 0;
  if (b.high) s += (u.floor / FLOORS) * 2;
  if (b.large) s += u.sqft / 1780;
  if (b.purpose === "invest") s += 1 - u.price / u.sqft / 5000; // lower price per sq ft
  if (b.budget) s += 0.5 * (u.price / b.budget); // use the budget, don't just show the cheapest
  return s;
}

function explain(u: Unit, b: Brief, pool: Unit[]): Match {
  const reasons: string[] = [];
  if (b.view && u.side === b.view) reasons.push(`Faces ${viewName(u.side)}`);
  if (b.high && u.floor >= 22) reasons.push(`Upper level ${u.floor}`);
  if (b.upfront) reasons.push(`Due on booking ${aed(payments(u).now)}, within your ${aed(b.upfront)}`);
  if (b.budget) reasons.push(`${aed(u.price)}, within your ${aed(b.budget)}`);
  if (b.beds || b.large) reasons.push(`${u.type.replace("BR", " bedroom")}, ${u.sqft.toLocaleString("en")} sq ft`);
  if (!reasons.length) reasons.push(`${u.type.replace("BR", " bedroom")} on level ${u.floor}, faces ${viewName(u.side)}`);
  let tradeoff: string | undefined;
  if (b.view && u.side !== b.view) tradeoff = `Faces ${viewName(u.side)}, not ${viewName(b.view)}`;
  else if (u.floor < 10) tradeoff = `Lower level (${u.floor})`;
  else {
    const cheapest = Math.min(...pool.map((x) => x.price));
    if (u.price > cheapest * 1.08) tradeoff = `${aed(u.price - cheapest)} more than the lowest match`;
  }
  return { u, reasons: reasons.slice(0, 2), tradeoff };
}

export function match(b: Brief, all = ALL()): Result {
  const pool = all.filter((u) => fits(u, b));
  if (pool.length) {
    const ranked = [...pool].sort((x, y) => score(y, b) - score(x, b) || x.price - y.price);
    // up to three, spread across views and heights so the buyer sees real choices
    const pick: Unit[] = [ranked[0]];
    for (const u of ranked) {
      if (pick.length >= 3) break;
      if (!pick.includes(u) && pick.every((p) => p.side !== u.side || p.type !== u.type || Math.abs(p.floor - u.floor) >= 6)) pick.push(u);
    }
    for (const u of ranked) { if (pick.length >= 3) break; if (!pick.includes(u)) pick.push(u); }
    return { kind: "matches", items: pick.map((u) => explain(u, b, pool)), total: pool.length };
  }
  // nothing fits: say which limit blocks it and offer explicit, priced relaxations
  const avail = all.filter((u) => u.status === "Available");
  const options: { label: string; patch: Partial<Brief> }[] = [];
  const sameBeds = avail.filter((u) => fits(u, { ...b, budget: undefined, upfront: undefined }));
  if (b.budget && sameBeds.length) {
    const lo = Math.min(...sameBeds.map((u) => u.price));
    options.push({ label: `Raise budget to ${aed(lo)}`, patch: { budget: lo } });
  }
  if (b.upfront && sameBeds.length) {
    const lo = Math.min(...sameBeds.filter((u) => !b.budget || u.price <= b.budget).map((u) => payments(u).now));
    if (Number.isFinite(lo)) options.push({ label: `Booking cash of ${aed(lo)}`, patch: { upfront: Math.ceil(lo / 1e4) * 1e4 } });
  }
  if (b.viewMust && avail.some((u) => fits(u, { ...b, viewMust: false }))) options.push({ label: "Consider any view", patch: { viewMust: false } });
  if (b.beds && b.beds > 1 && avail.some((u) => fits(u, { ...b, beds: (b.beds - 1) as 1 | 2 }))) {
    options.push({ label: `${b.beds - 1} bedroom instead`, patch: { beds: (b.beds - 1) as 1 | 2 } });
  }
  const what = [b.beds && `${b.beds}-bedroom`, b.viewMust && b.view && `${viewName(b.view)}-facing`].filter(Boolean).concat("residence").join(" ");
  const limits = [b.budget && `up to ${aed(b.budget)}`, b.upfront && `with ${aed(b.upfront)} due on booking`].filter(Boolean).join(" ");
  const lowest = sameBeds.length ? ` The lowest available ${what} is ${aed(Math.min(...sameBeds.map((u) => u.price)))}.` : "";
  return { kind: "none", why: `No available ${what} ${limits}.${lowest}`.replace(/\s+\./g, ".").replace(/\s+/g, " "), options };
}

// Next missing question (max four), or null when it is time to show results.
export const QUESTIONS = ["purpose", "beds", "budget", "view"] as const;
export type Q = (typeof QUESTIONS)[number];
export function nextQuestion(b: Brief, asked: Q[]): Q | null {
  for (const q of QUESTIONS) if (!asked.includes(q) && b[q] === undefined) return q;
  return null;
}

// "the second one", "compare these", "payments" → reference to what is on screen
export function command(text: string): { act: "select"; i: number } | { act: "compare" } | { act: "payments" } | { act: "cheaper" } | null {
  const t = text.toLowerCase();
  const ord = /\b(first|1st|second|2nd|third|3rd)\b/.exec(t);
  if (ord && /\b(show|open|see|view|one|that|this)\b/.test(t)) return { act: "select", i: ["first", "1st"].includes(ord[1]) ? 0 : ["second", "2nd"].includes(ord[1]) ? 1 : 2 };
  if (/\bcompare\b/.test(t)) return { act: "compare" };
  if (/\b(payment|payments|pay|instalment|installment|schedule)\b/.test(t) && !money(t)) return { act: "payments" };
  if (/\b(cheaper|less expensive|lower price)\b/.test(t) && !money(t)) return { act: "cheaper" };
  return null;
}
