"use client";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { track } from "@vercel/analytics";
import Orbit from "./Orbit";
import Intro from "./Intro";
import Guide, { GuideActions } from "./Guide";
import { FLOORS, Unit, unitsOn, unitById, aed, aedFull, payments, PLAN_NAME, ANCHOR, THROUGH, STILLS, BROKERS, PROJECT_ADVISOR, Broker } from "./data";
import type { Brief } from "./match";

const Tour = dynamic(() => import("./Tour"), { ssr: false });

const typeName = (u: Unit) => u.type.replace("BR", " bedroom");
const viewName = (u: Unit) => (u.side === "Sea" ? "Gulf & Downtown" : "City & marina");
const clean = (ids: string[]) => [...new Set(ids)].filter((id) => unitById(id)).slice(0, 3);

export default function Experience() {
  const [night, setNight] = useState(false);
  const [floor, setFloor] = useState(0);
  const [unit, setUnit] = useState<Unit | null>(null);
  const [tour, setTour] = useState(false);
  const [gallery, setGallery] = useState(-1);
  const [ref, setRef] = useState("");
  const [intro, setIntro] = useState(true);
  const [ready, setReady] = useState(false); // URL read: decides whether the film plays at all
  const [list, setList] = useState<string[]>([]);
  const [compare, setCompare] = useState(false);
  const [cmp, setCmp] = useState<string[] | null>(null); // guide matches compared without touching the shortlist
  const [handoff, setHandoff] = useState(false);
  const [copied, setCopied] = useState("");
  const [guide, setGuide] = useState(false);
  const [guideUsed, setGuideUsed] = useState(false);
  const [invite, setInvite] = useState(false);
  const [brief, setBrief] = useState<Brief>({});
  const [matchFloors, setMatchFloors] = useState<number[]>([]);
  const [payOpen, setPayOpen] = useState(0);

  // ?ref= is attribution only; it maps to an advisor solely through the BROKERS directory
  const advisor: Broker | null = BROKERS[ref] || (PROJECT_ADVISOR.wa ? PROJECT_ADVISOR : null);

  useEffect(() => {
    const q = new URLSearchParams(location.search);
    try {
      const r = (q.get("ref") || "").toLowerCase().replace(/[^a-z0-9_-]/g, "").slice(0, 32);
      if (r) sessionStorage.setItem("ref", r);
      setRef(r || sessionStorage.getItem("ref") || "");
    } catch { /* storage blocked: no broker attribution */ }
    let saved: string[] = [];
    try { saved = JSON.parse(localStorage.getItem("list") || "[]"); } catch { /* ignore */ }
    const shared = clean((q.get("list") || "").split(","));
    setList(clean([...shared, ...(Array.isArray(saved) ? saved : [])]));
    const u = unitById(q.get("unit") || "");
    // a direct link goes straight to the sales information, no film
    if (u) { openUnit(u); setIntro(false); track("open_unit_link", { unit: u.id }); }
    if (shared.length) { setCompare(true); setIntro(false); track("open_shortlist_link", { n: shared.length }); }
    setReady(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { try { localStorage.setItem("list", JSON.stringify(list)); } catch { /* ignore */ } }, [list]);

  // one-time invitation to the guide after the film
  useEffect(() => {
    if (intro) return;
    try { if (localStorage.getItem("invited")) return; localStorage.setItem("invited", "1"); } catch { /* show anyway */ }
    const t = setTimeout(() => setInvite(true), 1800);
    return () => clearTimeout(t);
  }, [intro]);

  const units = useMemo(() => (floor ? unitsOn(floor) : []), [floor]);
  const free = units.filter((u) => u.status === "Available").length;
  const saved = list.map(unitById).filter(Boolean) as Unit[];
  const listed = compare && cmp ? (cmp.map(unitById).filter(Boolean) as Unit[]) : saved;
  const closeCompare = () => { setCompare(false); setCmp(null); };
  const small = () => typeof window !== "undefined" && innerWidth <= 720;

  function openUnit(u: Unit) {
    setFloor(u.floor); setUnit(u); setCompare(false); setCmp(null);
    if (small()) setGuide(false); // one sheet at a time on phones
    track("unit_view", { unit: u.id, type: u.type });
  }
  const openGuide = () => { setGuide(true); setGuideUsed(true); setInvite(false); if (small()) { setFloor(0); setUnit(null); } };

  const link = (p: Record<string, string>) => `${location.origin}/?${new URLSearchParams({ ...p, ...(ref && { ref }) })}`;
  const line = (u: Unit) => `• Residence ${u.id}: ${typeName(u)}, ${u.sqft.toLocaleString("en")} sq ft, ${viewName(u)} view, level ${u.floor}, from ${aed(u.price)}`;
  const wa = (text: string) => `https://wa.me/${advisor?.wa || ""}?text=${encodeURIComponent(text + (ref ? `\nRef: ${ref}` : ""))}`;
  const waLabel = advisor?.wa ? `Message ${advisor.name.split(" ")[0]} on WhatsApp` : "Share on WhatsApp";

  const save = (id: string) => setList((l) => {
    if (l.includes(id)) return l.filter((x) => x !== id);
    track("shortlist_changed", { unit: id, op: "add" });
    return [...l, id].slice(-3);
  });
  async function share(url: string, what: string) {
    track("share", { what });
    try {
      if (navigator.share) { await navigator.share({ title: "The Final Tower", url }); return; }
      await navigator.clipboard.writeText(url); setCopied(what); setTimeout(() => setCopied(""), 2200);
    } catch { /* share sheet closed */ }
  }

  // the guide can only drive the explorer through these, and every ID is re-checked against the data
  const act: GuideActions = {
    select: (id) => { const u = unitById(id); if (u) openUnit(u); },
    payments: (id) => { const u = unitById(id); if (u) { openUnit(u); setPayOpen((n) => n + 1); } },
    tour: (id) => { const u = unitById(id); if (u?.type === "2BR") setTour(true); },
    save: (id) => { if (unitById(id) && !list.includes(id)) save(id); },
    compare: (ids) => { const ok = clean(ids); if (ok.length) { setCmp(ok); setCompare(true); track("compare_open", { n: ok.length, from: "guide" }); } },
    matches: (floors) => setMatchFloors(floors.filter((f) => Number.isInteger(f) && f >= 1 && f <= FLOORS)),
  };

  return (
    <main className={(night ? "night " : "") + (floor ? "open " : "") + (guide ? "guiding" : "")}>
      <Orbit night={night} selected={floor} matches={matchFloors} paused={tour}
        active={!floor && !tour && !intro && !compare && !guide} onFloor={(f) => { setFloor(f); setUnit(null); }} />

      <header className="brand">
        <span className="kicker">Dubai Maritime City · Waterfront</span>
        <h1>The Final Tower</h1>
        <p>33 levels on the Gulf, facing the Downtown skyline.</p>
      </header>

      <div className="switch" role="group" aria-label="Light">
        <button className={!night ? "on" : ""} aria-pressed={!night} onClick={() => setNight(false)}>Day</button>
        <button className={night ? "on" : ""} aria-pressed={night} onClick={() => setNight(true)}>Blue hour</button>
      </div>
      {BROKERS[ref] && <div className="advisor">Your advisor · <b>{BROKERS[ref].name}</b></div>}

      <div className="dock">
        <button className="primary" onClick={openGuide}>Find my residence</button>
        <button onClick={() => setTour(true)}><span className="wide">Walk a </span>2BR · 360°</button>
        <button onClick={() => setGallery(0)}>Interiors</button>
        <button onClick={() => { setFloor(24); setUnit(null); }}>Levels</button>
      </div>
      {invite && !guide && (
        <div className="invite" role="status">
          <p>Tell me what matters. I&apos;ll help you compare the residences.</p>
          <button className="cta" onClick={openGuide}>Find my residence</button>
          <button className="x" onClick={() => setInvite(false)} aria-label="Dismiss">×</button>
        </div>
      )}
      {saved.length > 0 && !compare && (
        <button className="listbar" onClick={() => { setCompare(true); track("compare_open", { n: saved.length }); }}>
          Shortlist <b>{saved.length}</b> · Compare →
        </button>
      )}

      {floor > 0 && (
        <aside className="panel" aria-label={`Level ${floor}`}>
          <button className="x" onClick={() => { setFloor(0); setUnit(null); }} aria-label="Close level">×</button>
          {guideUsed && !guide && <button className="back-guide" onClick={openGuide}>← Back to the guide</button>}
          <div className="lvl">
            <button onClick={() => { setFloor(Math.max(1, floor - 1)); setUnit(null); }} aria-label="Level down">−</button>
            <div><small>Level</small><b>{floor}</b></div>
            <button onClick={() => { setFloor(Math.min(FLOORS, floor + 1)); setUnit(null); }} aria-label="Level up">+</button>
          </div>
          <Levels floor={floor} matches={matchFloors} onPick={(f) => { setFloor(f); setUnit(null); }} />
          <p className="avail">{free} of 12 residences available</p>
          <Legend />
          <Plate units={units} sel={unit} saved={list} onSel={openUnit} />
          <details className="ulist">
            <summary>List view</summary>
            <ul>{units.map((u) => (
              <li key={u.id}><button onClick={() => openUnit(u)} aria-current={unit?.id === u.id}>
                <b>{u.id}</b><span>{u.type} · {u.side === "Sea" ? "Gulf" : "City"} · {aed(u.price)}</span><span className={`st ${u.status}`}>{u.status}</span>
              </button></li>
            ))}</ul>
          </details>
          {unit ? (
            <div className="card">
              <div className="row"><h3>Residence {unit.id}</h3><span className={`st ${unit.status}`}>{unit.status}</span></div>
              <dl>
                <div><dt>Type</dt><dd>{typeName(unit)}</dd></div>
                <div><dt>Size</dt><dd>{unit.sqft.toLocaleString("en")} sq ft</dd></div>
                <div><dt>View</dt><dd>{viewName(unit)}</dd></div>
                <div><dt>From</dt><dd>{aed(unit.price)}</dd></div>
              </dl>
              {unit.status !== "Sold" && <Payments key={unit.id + ":" + payOpen} u={unit} open={payOpen > 0} />}
              <div className="pair">
                <button className={"cta ghost" + (list.includes(unit.id) ? " saved" : "")} onClick={() => save(unit.id)} aria-pressed={list.includes(unit.id)}>
                  {list.includes(unit.id) ? "★ In shortlist" : "☆ Add to shortlist"}
                </button>
                <button className="cta ghost" onClick={() => share(link({ unit: unit.id }), "unit")}>{copied === "unit" ? "Link copied" : "Share"}</button>
              </div>
              {unit.type === "2BR"
                ? <button className="cta" onClick={() => setTour(true)}>360° walk · representative 2BR</button>
                : <button className="cta" onClick={() => setGallery(0)}>See interior images</button>}
              {unit.status !== "Sold" && (
                <a className="cta ghost" href={wa(`Hello, I'm interested in this residence:\n${line(unit)}\n${link({ unit: unit.id })}`)} target="_blank" rel="noreferrer"
                  onClick={() => track("whatsapp_click", { from: "unit", unit: unit.id, routed: !!advisor?.wa })}>{waLabel}</a>
              )}
              <p className="note">{unit.type === "2BR" ? "The 360° walk is a representative two-bedroom layout, not this exact unit, floor or view." : "No 360° walk exists for this layout yet; the interior images are illustrative."}</p>
            </div>
          ) : (
            <p className="note">Choose a residence on the plan or in the list.</p>
          )}
        </aside>
      )}

      <Guide brief={brief} setBrief={setBrief} unit={unit} act={act} open={guide} onClose={() => setGuide(false)} />

      {compare && (
        <div className="sheet" onClick={closeCompare} onKeyDown={(e) => e.key === "Escape" && closeCompare()}>
          <section className="compare" role="dialog" aria-modal="true" aria-label="Compare residences" onClick={(e) => e.stopPropagation()}>
            <button className="x" onClick={closeCompare} aria-label="Close" autoFocus>×</button>
            <span className="kicker">{cmp ? "Guide suggestions" : "Your shortlist"}</span>
            <h2>Compare residences</h2>
            {listed.length === 0 ? <p className="note">Your shortlist is empty. Save residences from any level.</p> : (
              <div className="ctable" style={{ gridTemplateColumns: `minmax(74px, .8fr) repeat(${listed.length}, minmax(92px, 1fr))` }}>
                <span />
                {listed.map((u) => (
                  <div key={u.id} className="chead">
                    <b>{u.id}</b>
                    <span className={`st ${u.status}`}>{u.status}</span>
                    <button onClick={() => openUnit(u)}>View</button>
                    {cmp
                      ? <button onClick={() => save(u.id)} aria-pressed={list.includes(u.id)}>{list.includes(u.id) ? "★ Saved" : "☆ Save"}</button>
                      : <button onClick={() => save(u.id)} aria-label={`Remove ${u.id}`}>Remove</button>}
                  </div>
                ))}
                {ROWS.map(([label, f]) => <Row key={label} label={label} cells={listed.map(f)} />)}
              </div>
            )}
            {listed.length > 0 && (
              <div className="cactions">
                <button className="cta" onClick={() => { setHandoff(true); track("handoff_prepared", { n: listed.length }); }}>
                  {advisor?.wa ? `Send to ${advisor.name.split(" ")[0]}` : "Prepare a message for an advisor"}
                </button>
                <button className="cta ghost" onClick={() => share(link({ list: listed.map((u) => u.id).join(",") }), "list")}>{copied === "list" ? "Link copied" : "Share with family"}</button>
              </div>
            )}
            <p className="note">{ANCHOR} Prices, availability and the plan are sample data. A shared link only contains the residence numbers and can be forwarded.</p>
          </section>
        </div>
      )}

      {handoff && <Handoff units={listed} brief={brief} advisor={advisor} wa={wa} link={link({ list: listed.map((u) => u.id).join(",") })} onClose={() => setHandoff(false)} />}

      {tour && <Tour onClose={() => setTour(false)} night={night} setNight={setNight} />}

      {gallery >= 0 && (
        <div className="gallery" onClick={() => setGallery(-1)}>
          <img src={STILLS[gallery].src} alt={STILLS[gallery].label} />
          <div className="gbar" onClick={(e) => e.stopPropagation()}>
            {STILLS.map((s, i) => (
              <button key={s.src} className={i === gallery ? "on" : ""} onClick={() => setGallery(i)}>{s.label}</button>
            ))}
            <button onClick={() => setGallery(-1)}>Close</button>
          </div>
        </div>
      )}

      {!ready && <div className="intro" />}
      {ready && intro && <Intro onDone={(find) => { setIntro(false); if (find) openGuide(); }} />}

      <footer className="credit">Concept by Ophira · not affiliated with DAMAC · images are design visualisations · availability and prices are sample data</footer>
    </main>
  );
}

const ROWS: [string, (u: Unit) => string][] = [
  ["Type", typeName],
  ["Size", (u) => `${u.sqft.toLocaleString("en")} sq ft`],
  ["Level", (u) => String(u.floor)],
  ["View", viewName],
  ["Price", (u) => aed(u.price)],
  ["Per sq ft", (u) => aedFull(u.price / u.sqft)],
  ["Due on booking", (u) => aedFull(payments(u).now)],
  [THROUGH, (u) => aedFull(payments(u).firstYear)],
  ["On handover", (u) => aedFull(payments(u).handover)],
];

function Row({ label, cells }: { label: string; cells: string[] }) {
  const same = cells.every((c) => c === cells[0]);
  return (<>
    <span className="clab">{label}</span>
    {cells.map((c, i) => <span key={i} className={same ? "" : "diff"}>{c}</span>)}
  </>);
}

function Payments({ u, open }: { u: Unit; open: boolean }) {
  const p = payments(u), el = useRef<HTMLDetailsElement>(null);
  useEffect(() => { if (open) el.current?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, [open]);
  return (
    <details ref={el} className="pay" open={open} onToggle={(e) => (e.target as HTMLDetailsElement).open && track("payment_viewed", { unit: u.id })}>
      <summary>
        <span>Due on booking</span><b>{aedFull(p.now)}</b>
        <small>{PLAN_NAME} · see schedule</small>
      </summary>
      <ol>
        {p.steps.map((s) => <li key={s.label}><span>{s.label}<small>{s.when} · {s.pct}%</small></span><b>{aedFull(s.amount)}</b></li>)}
        <li><span>DLD registration<small>4% · on booking</small></span><b>{aedFull(p.dld)}</b></li>
        <li><span>Oqood &amp; admin<small>sample fee · on booking</small></span><b>{aedFull(p.admin)}</b></li>
      </ol>
      <p className="note">{THROUGH}: <b>{aedFull(p.firstYear)}</b>. Balance on handover: <b>{aedFull(p.handover)}</b>. {ANCHOR} Other charges may apply; not legal or financial advice.</p>
    </details>
  );
}

function Levels({ floor, matches, onPick }: { floor: number; matches: number[]; onPick: (f: number) => void }) {
  const counts = useMemo(() => [...Array(FLOORS)].map((_, i) => unitsOn(i + 1).filter((u) => u.status === "Available").length), []);
  return (
    <div className="levels" role="group" aria-label="All levels">
      {counts.map((n, i) => {
        const m = matches.includes(i + 1);
        return (
          <button key={i} className={(i + 1 === floor ? "on " : "") + (n ? "" : "full ") + (m ? "match" : "")} onClick={() => onPick(i + 1)}
            aria-label={`Level ${i + 1}, ${n} available${m ? ", has a guide match" : ""}`} aria-current={i + 1 === floor}>{i + 1}</button>
        );
      })}
    </div>
  );
}

function Legend() {
  return (
    <div className="legend" aria-hidden="true">
      <span><i className="Available" />Available</span><span><i className="Reserved" />Reserved</span><span><i className="Sold" />Sold</span><span>★ Shortlisted</span>
    </div>
  );
}

// Editable summary; nothing is sent until the visitor presses send inside WhatsApp.
function Handoff({ units, brief, advisor, wa, link, onClose }: {
  units: Unit[]; brief: Brief; advisor: Broker | null; wa: (t: string) => string; link: string; onClose: () => void;
}) {
  const [name, setName] = useState(""), [day, setDay] = useState("Tomorrow"), [slot, setSlot] = useState("Afternoon (12:00–17:00 GST)");
  const [lang, setLang] = useState("English"), [qs, setQs] = useState(""), [withBrief, setWithBrief] = useState(false);
  const [copied, setCopied] = useState(false);
  const tz = typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "";
  const briefText = [brief.purpose && `Purpose: ${brief.purpose}`, brief.beds && `${brief.beds} bedroom`, brief.budget && `Budget up to ${aed(brief.budget)}`, brief.upfront && `Booking cash up to ${aed(brief.upfront)}`, brief.view && `Prefers ${brief.view === "Sea" ? "Gulf" : "city"} view`].filter(Boolean).join(", ");
  const text = [
    `Hello${advisor?.wa ? " " + advisor.name.split(" ")[0] : ""}, I'm ${name || "interested in The Final Tower"}.`,
    `Residences I'm considering:`, ...units.map((u) => `• ${u.id}: ${u.type}, ${u.sqft.toLocaleString("en")} sq ft, level ${u.floor}, ${aed(u.price)}`),
    withBrief && briefText ? `About me: ${briefText}.` : "",
    `Could we speak ${day.toLowerCase()}, ${slot}? (My time zone: ${tz}.) I'd prefer ${lang}.`,
    qs.trim() ? `My questions: ${qs.trim()}` : "",
    link,
  ].filter(Boolean).join("\n");
  return (
    <div className="sheet top" onClick={onClose} onKeyDown={(e) => e.key === "Escape" && onClose()}>
      <form className="compare callf" role="dialog" aria-modal="true" aria-label="Message for an advisor" onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => { e.preventDefault(); track("whatsapp_click", { from: "handoff", n: units.length, routed: !!advisor?.wa, brief: withBrief }); window.open(wa(text), "_blank", "noopener"); }}>
        <button type="button" className="x" onClick={onClose} aria-label="Close">×</button>
        <h2>Request a call</h2>
        <p className="note">{advisor?.wa ? `This goes to ${advisor.name}, ${advisor.agency}.` : "No advisor number is set up for this concept, so WhatsApp will ask you who to send it to."} It is a request: the advisor confirms the time.</p>
        <label>Your name<input value={name} onChange={(e) => setName(e.target.value)} autoComplete="given-name" /></label>
        <div className="two">
          <label>Day<select value={day} onChange={(e) => setDay(e.target.value)}>{["Today", "Tomorrow", "This week"].map((o) => <option key={o}>{o}</option>)}</select></label>
          <label>Language<select value={lang} onChange={(e) => setLang(e.target.value)}>{["English", "Arabic", "Russian", "Hindi", "Mandarin", "French", "Spanish"].map((o) => <option key={o}>{o}</option>)}</select></label>
        </div>
        <label>Time (Dubai, GST = UTC+4)<select value={slot} onChange={(e) => setSlot(e.target.value)}>
          {["Morning (09:00–12:00 GST)", "Afternoon (12:00–17:00 GST)", "Evening (17:00–20:00 GST)"].map((o) => <option key={o}>{o}</option>)}
        </select></label>
        <label>Questions<textarea value={qs} onChange={(e) => setQs(e.target.value)} rows={2} maxLength={400} dir="auto" /></label>
        {briefText && <label className="check"><input type="checkbox" checked={withBrief} onChange={(e) => setWithBrief(e.target.checked)} />Include what I told the guide ({briefText})</label>}
        <details className="preview"><summary>Preview message</summary><pre dir="auto">{text}</pre></details>
        <button className="cta" type="submit">{advisor?.wa ? `Open WhatsApp to ${advisor.name.split(" ")[0]}` : "Open WhatsApp"}</button>
        <button type="button" className="cta ghost" onClick={async () => { try { await navigator.clipboard.writeText(text); setCopied(true); } catch { /* ignore */ } }}>{copied ? "Copied" : "Copy message"}</button>
        <p className="note">Nothing is sent until you press send in WhatsApp.</p>
      </form>
    </div>
  );
}

// Long slab: 6 residences on the Gulf side (top), 6 on the city side (bottom), core in the middle.
function Plate({ units, sel, saved, onSel }: { units: Unit[]; sel: Unit | null; saved: string[]; onSel: (u: Unit) => void }) {
  const W = 340, H = 120, core = 22;
  const sea = units.filter((u) => u.side === "Sea"), city = units.filter((u) => u.side === "City");
  const row = (list: Unit[], y: number, h: number) => {
    const tot = list.reduce((a, u) => a + u.sqft, 0); let x = 4;
    return list.map((u) => {
      const w = ((W - 8) * u.sqft) / tot; const r = (
        <g key={u.id} className={`u ${u.status} ${sel?.id === u.id ? "sel" : ""}`} onClick={() => onSel(u)}
          role="button" tabIndex={0} aria-pressed={sel?.id === u.id}
          aria-label={`Residence ${u.id}, ${typeName(u)}, ${viewName(u)}, ${aed(u.price)}, ${u.status}${saved.includes(u.id) ? ", shortlisted" : ""}`}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onSel(u))}>
          <rect x={x + 1} y={y} width={w - 2} height={h} rx={2} />
          <text x={x + w / 2} y={y + h / 2 - 1}>{u.type}</text>
          <text className="sub" x={x + w / 2} y={y + h / 2 + 9}>{u.status === "Available" ? u.id : u.status}</text>
          {saved.includes(u.id) && <text className="star" x={x + w - 7} y={y + 9}>★</text>}
        </g>);
      x += w; return r;
    });
  };
  return (
    <svg className="plate" viewBox={`0 0 ${W} ${H + 18}`} aria-label="Floor plan">
      <text className="lab" x={W / 2} y={10}>THE GULF · DOWNTOWN</text>
      {row(sea, 14, (H - core) / 2 - 2)}
      <rect className="core" x={4} y={14 + (H - core) / 2} width={W - 8} height={core - 4} rx={2} />
      {row(city, 14 + (H + core) / 2 - 2, (H - core) / 2 - 2)}
    </svg>
  );
}
