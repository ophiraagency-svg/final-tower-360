"use client";
import { useEffect, useRef, useState } from "react";
import { track } from "@vercel/analytics";
import { Unit, aed, payments, DATA_VERSION } from "./data";
import { Brief, Q, QUESTIONS, Result, match, parse, nextQuestion, command } from "./match";

export type GuideActions = {
  select: (id: string) => void; payments: (id: string) => void; tour: (id: string) => void;
  save: (id: string) => void; compare: (ids: string[]) => void; matches: (floors: number[]) => void;
};
type Msg = { from: "guide" | "you"; text: string; q?: Q; result?: Result };

const CHIPS: Record<Q, { label: string; patch: Partial<Brief> }[]> = {
  purpose: [{ label: "To live in", patch: { purpose: "live" } }, { label: "As an investment", patch: { purpose: "invest" } }, { label: "Just exploring", patch: { purpose: "explore" } }],
  beds: [{ label: "1 bedroom", patch: { beds: 1 } }, { label: "2 bedrooms", patch: { beds: 2 } }, { label: "3 bedrooms", patch: { beds: 3 } }, { label: "Any", patch: {} }],
  budget: [{ label: "Up to AED 3M", patch: { budget: 3e6 } }, { label: "Up to AED 4.5M", patch: { budget: 4.5e6 } }, { label: "Up to AED 6M", patch: { budget: 6e6 } }, { label: "Up to AED 8M", patch: { budget: 8e6 } }, { label: "No limit", patch: {} }],
  view: [{ label: "Prefer Gulf & Downtown", patch: { view: "Sea" } }, { label: "Must face the Gulf", patch: { view: "Sea", viewMust: true } }, { label: "Prefer city & marina", patch: { view: "City" } }, { label: "No preference", patch: {} }],
};
const ASK: Record<Q, string> = {
  purpose: "Is this a home for you, or an investment?",
  beds: "How many bedrooms?",
  budget: "What total price are you comfortable with? (Fees and booking cash are shown separately.)",
  view: "Does the view matter?",
};

export default function Guide({ brief, setBrief, unit, act, open, onClose }: {
  brief: Brief; setBrief: (b: Brief) => void; unit: Unit | null; act: GuideActions; open: boolean; onClose: () => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [asked, setAsked] = useState<Q[]>([]);
  const [text, setText] = useState("");
  const latest = useRef<Unit[]>([]);
  const log = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  const say = (m: Msg[]) => setMsgs((x) => [...x, ...m]);
  useEffect(() => { log.current?.scrollTo({ top: log.current.scrollHeight, behavior: "smooth" }); }, [msgs]);
  useEffect(() => {
    if (!open) return;
    if (!msgs.length) { track("guide_open"); step(brief, asked, [{ from: "guide", text: "Tell me what matters and I'll find residences that fit, then show them on the tower." }]); }
    input.current?.focus({ preventScroll: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // ask the next missing question, or show results
  function step(b: Brief, a: Q[], pre: Msg[] = []) {
    const q = nextQuestion(b, a);
    if (q) return say([...pre, { from: "guide", text: ASK[q], q }]);
    const r = match(b);
    track(r.kind === "matches" ? "matches_shown" : "no_match", { n: r.kind === "matches" ? r.items.length : 0, data: DATA_VERSION });
    if (a.length >= 4 && pre.every((m) => !m.result)) track("brief_complete");
    if (r.kind === "matches") {
      latest.current = r.items.map((m) => m.u);
      act.matches([...new Set(r.items.map((m) => m.u.floor))]);
      say([...pre, { from: "guide", text: r.total > r.items.length ? `${r.total} available residences fit. These ${r.items.length} show the real choices; their levels are marked on the tower.` : `${r.items.length === 1 ? "One residence fits" : `${r.items.length} residences fit`}. Their levels are marked on the tower.`, result: r }]);
    } else {
      latest.current = []; act.matches([]);
      say([...pre, { from: "guide", text: r.why, result: r }]);
    }
  }

  function apply(patch: Partial<Brief>, label: string, q?: Q) {
    const b = { ...brief, ...patch }, a = q && !asked.includes(q) ? [...asked, q] : asked;
    setBrief(b); setAsked(a);
    step(b, a, [{ from: "you", text: label }]);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const t = text.trim().slice(0, 300); if (!t) return;
    setText("");
    const you: Msg = { from: "you", text: t };
    const c = command(t);
    if (c?.act === "select") {
      const u = latest.current[c.i];
      if (!u) return say([you, { from: "guide", text: "There isn't one in that position in the latest suggestions." }]);
      act.select(u.id); return say([you, { from: "guide", text: `Opening residence ${u.id} on level ${u.floor}.` }]);
    }
    if (c?.act === "compare") {
      if (!latest.current.length) return say([you, { from: "guide", text: "Tell me what you need first, then I can compare the matches." }]);
      act.compare(latest.current.map((u) => u.id)); return say([you, { from: "guide", text: "Here they are side by side." }]);
    }
    if (c?.act === "payments") {
      const u = unit || latest.current[0];
      if (!u) return say([you, { from: "guide", text: "Choose a residence first and I'll open its payment plan." }]);
      act.payments(u.id); return say([you, { from: "guide", text: `Payment plan for residence ${u.id}: ${aed(payments(u).now)} due on booking, ${aed(payments(u).handover)} on handover.` }]);
    }
    if (c?.act === "cheaper") {
      if (!latest.current.length) return say([you, { from: "guide", text: "Cheaper than what? Tell me a total price, for example “under 3.5m”." }]);
      const below = Math.min(...latest.current.map((u) => u.price)) - 10000;
      const b = { ...brief, budget: below }; setBrief(b);
      return step(b, asked, [you, { from: "guide", text: `Looking below ${aed(below + 10000)}, the lowest price I showed you.` }]);
    }
    const patch = parse(t);
    if (!Object.keys(patch).length) return say([you, { from: "guide", text: "I didn't catch a requirement there. Try something like “2 bed, sea view, under 4.5m”." }]);
    // someone who types a whole brief at once gets results, not the remaining questions
    const a = Object.keys(patch).length >= 2 ? [...QUESTIONS] : [...new Set([...asked, ...(Object.keys(patch).filter((k) => (QUESTIONS as readonly string[]).includes(k)) as Q[])])];
    const b = { ...brief, ...patch };
    setBrief(b); setAsked(a);
    step(b, a, [you]);
  }

  const restart = () => { setBrief({}); setAsked([]); latest.current = []; act.matches([]); setMsgs([]); step({}, [], [{ from: "guide", text: "Starting again. What matters to you?" }]); };
  const lastQ = msgs.length ? msgs[msgs.length - 1].q : undefined;

  return (
    <section className={"guide" + (open ? "" : " hidden")} aria-label="Residence guide" aria-hidden={!open}>
      <header>
        <div><span className="kicker">Residence guide</span><span className="badge" title="Rules-based guide, not a live AI">Guided demo</span></div>
        <div>
          {msgs.length > 2 && <button className="restart" onClick={restart}>Start again</button>}
          <button className="x" onClick={onClose} aria-label="Close guide">×</button>
        </div>
      </header>
      <div className="glog" ref={log} aria-live="polite">
        {msgs.map((m, i) => (
          <div key={i} className={"gm " + (m.from === "you" ? "you" : "bot")} dir="auto">
            <p>{m.text}</p>
            {m.result?.kind === "matches" && m.result.items.map(({ u, reasons, tradeoff }, k) => (
              <article key={u.id} className="gcard">
                <div className="row"><b>{k + 1}. Residence {u.id}</b><span>{aed(u.price)}</span></div>
                <small>Level {u.floor} · {u.type} · {u.sqft.toLocaleString("en")} sq ft · {aed(payments(u).now)} on booking · {aed(payments(u).handover)} on handover</small>
                <ul>{reasons.map((r) => <li key={r}>{r}</li>)}{tradeoff && <li className="trade">Trade-off: {tradeoff}</li>}</ul>
                <div className="gact">
                  <button onClick={() => { act.select(u.id); track("recommendation_open", { unit: u.id }); }}>View</button>
                  <button onClick={() => act.payments(u.id)}>Payments</button>
                  <button onClick={() => act.save(u.id)}>Shortlist</button>
                  {u.type === "2BR" && <button onClick={() => act.tour(u.id)}>360° (sample 2BR)</button>}
                </div>
              </article>
            ))}
            {m.result?.kind === "none" && m.result.options.length > 0 && (
              <div className="chips">{m.result.options.map((o) => <button key={o.label} onClick={() => apply(o.patch, o.label)}>{o.label}</button>)}</div>
            )}
            {m.q && m.q === lastQ && i === msgs.length - 1 && (
              <div className="chips">
                {CHIPS[m.q].map((c) => <button key={c.label} onClick={() => apply(c.patch, c.label, m.q)}>{c.label}</button>)}
              </div>
            )}
            {m.result?.kind === "matches" && i === msgs.length - 1 && (
              <div className="chips">
                {m.result.items.length > 1 && <button onClick={() => act.compare(latest.current.map((u) => u.id))}>Compare these</button>}
              </div>
            )}
          </div>
        ))}
      </div>
      <form className="gin" onSubmit={submit}>
        <input ref={input} value={text} onChange={(e) => setText(e.target.value)} dir="auto" maxLength={300} enterKeyHint="send"
          placeholder="e.g. 2 bed, sea view, under 4.5m" aria-label="Tell the guide what you need" />
        <button type="submit" aria-label="Send">→</button>
      </form>
      <p className="gnote">Rules-based guide (English). Sample inventory {DATA_VERSION}; not live availability.</p>
    </section>
  );
}
