import { useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { NAV } from "./nav.js";
import { useFeed } from "../lib/mockFeed.js";

export function Topbar() {
  const loc = useLocation();
  const feed = useFeed();
  const current = NAV.find((n) => loc.pathname.startsWith(n.to)) || NAV[0];
  const [clock, setClock] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const threatHigh = feed.threatRate >= 25;
  return (
    <header className="h-16 shrink-0 border-b border-edge bg-bg/70 backdrop-blur flex items-center gap-4 px-5">
      <div className="min-w-0">
        <h1 className="text-[15px] font-semibold leading-tight truncate">{current.label}</h1>
        <p className="text-[11.5px] text-faint truncate">{current.desc}</p>
      </div>
      <div className="ml-auto flex items-center gap-3">
        <span
          className={`hidden sm:inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11.5px] tnum ${
            threatHigh ? "border-bad/40 bg-bad/10 text-bad" : "border-edge bg-surface2 text-muted"
          }`}
          title="Rolling threat rate (last 15s)"
        >
          threat rate {feed.threatRate.toFixed(0)}%
        </span>
        <span
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11.5px] ${
            feed.running ? "border-good/40 bg-good/10 text-good" : "border-edge bg-surface2 text-faint"
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${feed.running ? "bg-good animate-pulsedot" : "bg-faint"}`} />
          {feed.running ? "LIVE" : "PAUSED"}
        </span>
        <span className="hidden md:block text-[12px] text-faint tnum font-mono">
          {clock.toLocaleTimeString([], { hour12: false })}
        </span>
      </div>
    </header>
  );
}
