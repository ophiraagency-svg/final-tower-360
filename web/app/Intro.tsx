"use client";
import { useEffect, useRef, useState } from "react";

const LINES = [
  { t: 0, text: "Dubai Maritime City" },
  { t: 4.4, text: "Six towers on the Gulf" },
  { t: 8.6, text: "And one view that is yours" },
];

// 13 s opening film; ends (or is skipped) into the interactive tower.
export default function Intro({ onDone }: { onDone: (find?: boolean) => void }) {
  const v = useRef<HTMLVideoElement>(null);
  const [line, setLine] = useState(0);
  const [out, setOut] = useState(false);

  const finish = (find?: boolean) => { setOut(true); setTimeout(() => onDone(find), 900); };

  useEffect(() => {
    const el = v.current!;
    const tu = () => { const i = LINES.findLastIndex((l) => el.currentTime >= l.t); setLine(Math.max(0, i)); };
    el.addEventListener("timeupdate", tu);
    el.play().catch(() => finish()); // autoplay blocked: go straight to the tower
    return () => el.removeEventListener("timeupdate", tu);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={`intro ${out ? "out" : ""}`}>
      <video ref={v} src="/film/intro.mp4" poster="/film/poster.jpg" muted playsInline preload="auto" onEnded={() => finish()} />
      <p key={line} className="intro-line">{LINES[line].text}</p>
      <div className="skip-row">
        <button className="skip primary" onClick={() => finish(true)}>Find my residence</button>
        <button className="skip" onClick={() => finish()}>Explore the tower →</button>
      </div>
    </div>
  );
}
