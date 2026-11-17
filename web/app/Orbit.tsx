"use client";
import { useEffect, useRef, useState } from "react";
import { ORBIT, FLOORS } from "./data";

type Props = { night: boolean; onFloor: (f: number) => void; active: boolean; selected: number; paused?: boolean; matches?: number[] };
const pad = (i: number) => String(i).padStart(3, "0");
const STEP = ORBIT.n / ORBIT.keys;

// Drag the whole complex through 360°. When it comes to rest it snaps to the nearest key
// angle and dissolves into the photograph of that angle (day or blue hour).
export default function Orbit({ night, onFloor, active, selected, paused, matches }: Props) {
  const cv = useRef<HTMLCanvasElement>(null);
  const hl = useRef<HTMLCanvasElement>(null);
  const frames = useRef<{ day: HTMLImageElement[]; dusk: HTMLImageElement[] }>({ day: [], dusk: [] });
  const masks = useRef<(ImageData | null)[]>([]);
  const st = useRef({ pos: 0, vel: 0, drag: false, lastX: 0, moved: 0, idle: true, target: -1 as number });
  const [frame, setFrame] = useState(0);
  const [settled, setSettled] = useState(-1);
  const [floor, setFloor] = useState(0);
  const [loaded, setLoaded] = useState(0);
  const [hint, setHint] = useState(true);
  const focus = useRef<number[]>([]);
  const [vw, setVw] = useState({ w: 16, h: 9 });
  useEffect(() => { fetch("/orbit/focus.json").then((r) => r.json()).then((f) => { focus.current = f; draw(frame); }).catch(() => {}); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const fx = (i: number) => focus.current[i] ?? 0.5;

  // Load the 8 key angles first; the 136 in-between frames only once the visitor can turn the building
  // (intro over, no panel), so a direct unit link stays light. Blue hour loads on first use.
  const [loadedDusk, setLoadedDusk] = useState(0);
  const all = useRef(false);
  function preload(set: "day" | "dusk") {
    const list = frames.current[set];
    const want = [...Array(ORBIT.n).keys()].filter((i) => (all.current || i % STEP === 0) && !list[i]);
    want.forEach((i) => {
      const im = new Image();
      im.decoding = "async";
      im.src = `/orbit/${set}${innerWidth < 800 ? "-s" : ""}/${pad(i)}.jpg`;
      im.onload = () => { (set === "day" ? setLoaded : setLoadedDusk)((n) => n + 1); if (i === 0) draw(0); };
      list[i] = im;
    });
  }
  const loadAll = () => { if (all.current) return; all.current = true; preload("day"); if (night) preload("dusk"); };
  useEffect(() => { preload("day"); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (active) loadAll(); }, [active]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (night) preload("dusk"); }, [night]); // eslint-disable-line react-hooks/exhaustive-deps
  const [seen, setSeen] = useState<Set<number>>(() => new Set([0]));

  function draw(i: number) {
    const ok = (im?: HTMLImageElement) => !!im && im.complete && !!im.naturalWidth;
    const dusk = night && ok(frames.current.dusk[i]);
    const c = cv.current, im = dusk ? frames.current.dusk[i] : frames.current.day[i];
    setTinted(night && !dusk);
    if (!c || !ok(im)) return;
    const ctx = c.getContext("2d")!;
    cover(ctx, im, c.width, c.height, fx(i));
  }

  // animation loop: inertia, idle auto-rotation, snapping
  useEffect(() => {
    if (paused) return; // the 360° tour is open: no work behind it
    let raf = 0, last = performance.now();
    const tick = (t: number) => {
      if (document.hidden) { last = t; raf = requestAnimationFrame(tick); return; }
      const dt = Math.min(50, t - last) / 16.67; last = t;
      const s = st.current;
      if (!s.drag) {
        if (s.idle && active) s.vel = ORBIT.n / (60 * 40); // one slow turn every 40 s until touched
        else if (Math.abs(s.vel) > 0.02) s.vel *= Math.pow(0.93, dt);
        else {
          s.vel = 0;
          if (s.target < 0) {
            const k = Math.round(s.pos / STEP);
            s.target = k * STEP;
          }
          const d = s.target - s.pos;
          s.pos += d * 0.12 * dt;
          if (Math.abs(d) < 0.02) { s.pos = s.target; }
        }
        s.pos += s.vel * dt;
      }
      const i = (((Math.round(s.pos) % ORBIT.n) + ORBIT.n) % ORBIT.n);
      setFrame((f) => (f === i ? f : i));
      const atKey = !s.drag && s.vel === 0 && Math.abs(s.pos - s.target) < 0.05;
      setSettled(atKey ? (((Math.round(s.target / STEP) % ORBIT.keys) + ORBIT.keys) % ORBIT.keys) : -1);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, paused]);

  const [tinted, setTinted] = useState(false);
  useEffect(() => { if (settled >= 0 && !seen.has(settled)) setSeen((x) => new Set(x).add(settled)); }, [settled, seen]);
  useEffect(() => { draw(frame); }, [frame, loaded, loadedDusk, night]); // eslint-disable-line react-hooks/exhaustive-deps

  // canvas size
  useEffect(() => {
    const fit = () => {
      for (const c of [cv.current, hl.current]) {
        if (!c) continue;
        const r = c.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio);
        c.width = r.width * dpr; c.height = r.height * dpr;
      }
      setVw({ w: innerWidth, h: innerHeight });
      draw(frame);
    };
    fit(); addEventListener("resize", fit);
    return () => removeEventListener("resize", fit);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // floor mask for the frame under the pointer (red channel = floor * 7)
  async function maskFor(i: number): Promise<ImageData | null> {
    if (masks.current[i] !== undefined) return masks.current[i];
    masks.current[i] = null;
    const im = new Image(); im.src = `${ORBIT.mask}/${pad(i)}.png`;
    await im.decode().catch(() => null);
    if (!im.naturalWidth) return null;
    const c = document.createElement("canvas"); c.width = im.naturalWidth; c.height = im.naturalHeight;
    const x = c.getContext("2d", { willReadFrequently: true })!; x.drawImage(im, 0, 0);
    return (masks.current[i] = x.getImageData(0, 0, c.width, c.height));
  }

  async function pick(cx: number, cy: number) {
    const c = cv.current; if (!c || settled < 0) return 0; // masks match the photos exactly only at the key angles
    const m = await maskFor(frame); if (!m) return 0;
    const r = c.getBoundingClientRect();
    const [u, v] = coverUV(cx - r.left, cy - r.top, r.width, r.height, m.width, m.height, fx(frame));
    if (u < 0 || v < 0 || u >= m.width || v >= m.height) return 0;
    const f = Math.round(m.data[(v * m.width + u) * 4] / 7);
    return f > 0 && f <= FLOORS ? f : 0;
  }

  // paint the hovered floor
  useEffect(() => {
    (async () => {
      const c = hl.current; if (!c) return;
      const ctx = c.getContext("2d")!; ctx.clearRect(0, 0, c.width, c.height);
      const f = floor || selected, mt = new Set(matches || []);
      if ((!f && !mt.size) || settled < 0) return;
      const m = await maskFor(frame); if (!m) return;
      const o = new ImageData(m.width, m.height);
      // the floor in focus is solid gold; floors holding guide matches get a lighter band
      for (let p = 0; p < m.data.length; p += 4) {
        const g = Math.round(m.data[p] / 7);
        if (f && g === f) { o.data[p] = 232; o.data[p + 1] = 190; o.data[p + 2] = 105; o.data[p + 3] = 185; }
        else if (g && mt.has(g)) { o.data[p] = 246; o.data[p + 1] = 222; o.data[p + 2] = 168; o.data[p + 3] = 150; }
      }
      const t = document.createElement("canvas"); t.width = m.width; t.height = m.height;
      t.getContext("2d")!.putImageData(o, 0, 0);
      cover(ctx, t, c.width, c.height, fx(frame));
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [floor, frame, selected, settled, matches]);

  const down = (e: React.PointerEvent) => {
    loadAll();
    const s = st.current; s.drag = true; s.idle = false; s.lastX = e.clientX; s.moved = 0; s.vel = 0; s.target = -1;
    setHint(false);
    (e.target as Element).setPointerCapture(e.pointerId);
  };
  const move = async (e: React.PointerEvent) => {
    const s = st.current;
    if (s.drag) {
      const dx = e.clientX - s.lastX; s.lastX = e.clientX; s.moved += Math.abs(dx);
      const k = -dx * (ORBIT.n / (innerWidth * 1.6));
      s.pos += k; s.vel = k;
      if (s.moved > 6) setFloor(0);
    } else if (e.pointerType === "mouse") {
      setFloor(await pick(e.clientX, e.clientY));
    }
  };
  const up = async (e: React.PointerEvent) => {
    const s = st.current; s.drag = false;
    if (s.moved < 6) {
      const f = await pick(e.clientX, e.clientY);
      if (f) { setFloor(f); onFloor(f); }
    }
  };

  return (
    <div className="orbit" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}
      style={{ cursor: floor ? "pointer" : "grab" }}>
      <canvas ref={cv} className="layer" style={{ filter: tinted ? "brightness(.55) saturate(1.25) hue-rotate(-12deg) contrast(1.05)" : "none", transition: "filter .8s" }} />
      {[...Array(ORBIT.keys).keys()].map((k) => seen.has(k) && (
        <div key={k} className="layer photo" style={{ opacity: settled === k ? 1 : 0 }}>
          <img src={`/keys/k${k}_day.jpg`} alt="" style={{ objectPosition: objPos(vw, fx(k * STEP)) }} />
          {night && <img src={`/keys/k${k}_dusk.jpg`} alt="" style={{ objectPosition: objPos(vw, fx(k * STEP)) }} />}
        </div>
      ))}
      <canvas ref={hl} className="layer hl" />
      {floor > 0 && <div className="floortag">Level {floor}<small>Tap to see the residences</small></div>}
      {hint && <div className="hint">Drag to turn the building · tap a floor</div>}
      {!hint && settled < 0 && <div className="hint soft">Release to land on a view</div>}
      {(night ? loadedDusk : loaded) < ORBIT.n && <div className="load" style={{ width: `${((night ? loadedDusk : loaded) / ORBIT.n) * 100}%` }} />}
    </div>
  );
}

// cover-crop that keeps the hero tower (horizontal focus f, 0..1) in view when the screen is narrower than 16:9
const offX = (W: number, w: number, f: number) => Math.min(0, Math.max(W - w, W / 2 - f * w));

function cover(ctx: CanvasRenderingContext2D, im: CanvasImageSource & { width: number; height: number }, W: number, H: number, f: number) {
  const iw = (im as HTMLImageElement).naturalWidth || im.width, ih = (im as HTMLImageElement).naturalHeight || im.height;
  const s = Math.max(W / iw, H / ih), w = iw * s, h = ih * s;
  ctx.drawImage(im, offX(W, w, f), (H - h) / 2, w, h);
}

function coverUV(x: number, y: number, W: number, H: number, iw: number, ih: number, f: number) {
  const s = Math.max(W / iw, H / ih), ox = offX(W, iw * s, f), oy = (H - ih * s) / 2;
  return [Math.floor((x - ox) / s), Math.floor((y - oy) / s)];
}

function objPos(v: { w: number; h: number }, f: number) {
  const w = Math.max(v.w, (v.h * 16) / 9);
  return v.w === w ? "50% 50%" : `${(offX(v.w, w, f) / (v.w - w)) * 100}% 50%`;
}
