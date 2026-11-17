"use client";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { NODES, LINKS, NodeId } from "./data";

// Equirect panoramas from Blender. Panorama centre = looking at the sea (-y in unit coordinates),
// panorama right = -x. lon is measured from the panorama centre, positive to the right.
function lonTo(a: NodeId, b: NodeId) {
  const A = NODES[a], B = NODES[b];
  return Math.atan2(-(B.x - A.x), -(B.y - A.y));
}
const dir = (lon: number, lat: number) =>
  new THREE.Vector3(Math.sin(lon) * Math.cos(lat), Math.sin(lat), -Math.cos(lon) * Math.cos(lat));

export default function Tour({ onClose, night, setNight }: { onClose: () => void; night: boolean; setNight: (n: boolean) => void }) {
  const host = useRef<HTMLDivElement>(null);
  const [node, setNode] = useState<NodeId>("living");
  const [fade, setFade] = useState(false);
  const [photo, setPhoto] = useState(false);
  const view = useRef({ lon: 0, lat: 0, fov: 75 });
  const nightRef = useRef(night);
  const api = useRef<{ load: (n: NodeId) => Promise<void>; spots: () => { id: NodeId; x: number; y: number; on: boolean }[] } | null>(null);
  const [spots, setSpots] = useState<{ id: NodeId; x: number; y: number; on: boolean }[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    addEventListener("keydown", onKey); return () => removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    const el = host.current!;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: "high-performance" }); }
    catch { setFailed(true); return; }
    renderer.setPixelRatio(Math.min(1.5, devicePixelRatio));
    renderer.domElement.addEventListener("webglcontextlost", (e) => { e.preventDefault(); setFailed(true); });
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const cam = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    const geo = new THREE.SphereGeometry(100, 96, 64); geo.scale(-1, 1, 1);
    const mat = new THREE.MeshBasicMaterial();
    const sphere = new THREE.Mesh(geo, mat);
    sphere.rotation.y = -Math.PI / 2; // texture centre (u=0.5) faces -z, the default forward
    scene.add(sphere);
    const loader = new THREE.TextureLoader();
    const cache = new Map<string, THREE.Texture>();
    let cur: NodeId = "living";

    const prep = (t: THREE.Texture) => { t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy()); return t; };
    const get = (n: NodeId) => {
      const url = nightRef.current ? NODES[n].night : NODES[n].src;
      return cache.get(url) ? Promise.resolve(cache.get(url)!) : new Promise<THREE.Texture>((res, rej) =>
        loader.load(url, (t) => { cache.set(url, prep(t)); res(t); }, undefined, () => {
          // no night version: fall back to day; no day version either: show the recovery screen
          if (url === NODES[n].src) return rej(new Error("panorama failed"));
          loader.load(NODES[n].src, (t) => { cache.set(url, prep(t)); res(t); }, undefined, () => rej(new Error("panorama failed")));
        }));
    };

    api.current = {
      async load(n) {
        let t: THREE.Texture;
        try { t = await get(n); } catch { setFailed(true); return; }
        mat.map = t; mat.needsUpdate = true; cur = n;
        cache.forEach((x, url) => { if (x !== t) { x.dispose(); cache.delete(url); } });
      },
      spots() {
        const w = el.clientWidth, h = el.clientHeight;
        return LINKS[cur].map((id) => {
          const p = dir(lonTo(cur, id), -0.32).multiplyScalar(50).project(cam);
          return { id, x: (p.x * 0.5 + 0.5) * w, y: (-p.y * 0.5 + 0.5) * h, on: p.z < 1 };
        });
      },
    };
    api.current.load("living");

    const size = () => { const w = el.clientWidth, h = el.clientHeight; renderer.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); };
    size(); addEventListener("resize", size);

    let raf = 0, last = "";
    const loop = () => {
      if (document.hidden) { raf = requestAnimationFrame(loop); return; }
      const v = view.current;
      v.lat = Math.max(-1.3, Math.min(1.3, v.lat));
      cam.fov = v.fov; cam.updateProjectionMatrix();
      cam.lookAt(dir(v.lon, v.lat));
      renderer.render(scene, cam);
      const sp = api.current!.spots(), key = sp.map((s) => `${s.id}${Math.round(s.x)},${Math.round(s.y)}${s.on}`).join();
      if (key !== last) { last = key; setSpots(sp); }
      raf = requestAnimationFrame(loop);
    };
    loop();

    // drag / pinch / wheel
    let px = 0, py = 0, down = false, pinch = 0;
    const pts = new Map<number, { x: number; y: number }>();
    const pd = (e: PointerEvent) => { pts.set(e.pointerId, { x: e.clientX, y: e.clientY }); down = true; px = e.clientX; py = e.clientY; el.setPointerCapture(e.pointerId); };
    const pm = (e: PointerEvent) => {
      if (!pts.has(e.pointerId)) return;
      pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
      const v = view.current;
      if (pts.size === 2) {
        const [a, b] = [...pts.values()]; const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch) v.fov = Math.max(35, Math.min(95, v.fov * (pinch / d)));
        pinch = d; return;
      }
      if (!down) return;
      const k = (v.fov / el.clientHeight) * (Math.PI / 180) * 1.1;
      v.lon -= (e.clientX - px) * k; v.lat += (e.clientY - py) * k; px = e.clientX; py = e.clientY;
    };
    const pu = (e: PointerEvent) => { pts.delete(e.pointerId); pinch = 0; down = pts.size > 0; };
    const wh = (e: WheelEvent) => { e.preventDefault(); view.current.fov = Math.max(35, Math.min(95, view.current.fov + e.deltaY * 0.04)); };
    el.addEventListener("pointerdown", pd); el.addEventListener("pointermove", pm);
    el.addEventListener("pointerup", pu); el.addEventListener("pointercancel", pu);
    el.addEventListener("wheel", wh, { passive: false });
    return () => {
      cancelAnimationFrame(raf); removeEventListener("resize", size);
      renderer.dispose(); renderer.forceContextLoss(); geo.dispose(); mat.dispose(); cache.forEach((t) => t.dispose());
      el.removeChild(renderer.domElement);
    };
  }, []);

  useEffect(() => {
    if (nightRef.current === night) return;
    nightRef.current = night;
    (async () => { setFade(true); await new Promise((r) => setTimeout(r, 280)); await api.current?.load(node); setFade(false); })();
  }, [night]); // eslint-disable-line react-hooks/exhaustive-deps

  async function go(n: NodeId) {
    setFade(true);
    await new Promise((r) => setTimeout(r, 280));
    const from = node;
    await api.current!.load(n);
    // keep looking the way we walked
    view.current.lon = lonTo(from, n); view.current.lat = 0;
    setNode(n); setFade(false);
  }

  return (
    <div className="tour" role="dialog" aria-label="360° walk through a representative two-bedroom residence">
      <div ref={host} className="tour-gl" />
      <div className="tour-fade" style={{ opacity: fade ? 1 : 0 }} />
      {spots.filter((s) => s.on).map((s) => (
        <button key={s.id} className="spot" style={{ left: s.x, top: s.y }} onClick={() => go(s.id)}>
          <span className="ring" /><em>{NODES[s.id].label}</em>
        </button>
      ))}
      <div className="tour-top">
        <button className="back" onClick={onClose}>← Back to the tower</button>
        <div className="switch inline" role="group" aria-label="Light">
          <button className={!night ? "on" : ""} onClick={() => setNight(false)}>Day</button>
          <button className={night ? "on" : ""} onClick={() => setNight(true)}>Blue hour</button>
        </div>
      </div>
      <span className="room">{NODES[node].label}<small>Representative 2-bedroom layout · not unit-specific</small></span>
      {failed && (
        <div className="tour-fail">
          <p>The 360° view couldn&apos;t load on this device.</p>
          <button className="cta" onClick={() => { setFailed(false); setPhoto(true); }}>See the photographs</button>
          <button className="cta ghost" onClick={onClose}>Back to the tower</button>
        </div>
      )}
      <button className="photo-btn" onClick={() => setPhoto(true)}>View as photograph</button>
      {photo && (
        <div className="gallery" onClick={() => setPhoto(false)}>
          <img src={NODES[node].photo} alt={NODES[node].label} />
          <div className="gbar"><button className="on">{NODES[node].label}</button><button onClick={() => setPhoto(false)}>Back to 360°</button></div>
        </div>
      )}
      <nav className="rooms">
        {(Object.keys(NODES) as NodeId[]).map((n) => (
          <button key={n} className={n === node ? "on" : ""} onClick={() => n !== node && go(n)}>{NODES[n].label}</button>
        ))}
      </nav>
    </div>
  );
}
