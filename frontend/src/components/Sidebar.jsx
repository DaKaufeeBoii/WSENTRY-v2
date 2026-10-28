import { NavLink } from "react-router-dom";
import { NAV } from "./nav.js";
import { useFeed } from "../lib/mockFeed.js";

function LiveDot({ running }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${
        running ? "bg-good animate-pulsedot shadow-[0_0_8px_1px_rgba(52,211,153,0.6)]" : "bg-faint"
      }`}
    />
  );
}

export function Sidebar() {
  const feed = useFeed();
  return (
    <aside className="hidden md:flex md:w-64 shrink-0 flex-col border-r border-edge bg-surface/40 h-full">
      <div className="px-5 h-16 flex items-center gap-3 border-b border-edge">
        <span className="w-2.5 h-2.5 rounded-full bg-accent shadow-glow" />
        <div className="leading-tight">
          <div className="font-bold tracking-[0.14em] text-sm">W-SENTRY</div>
          <div className="text-[11px] text-faint tracking-wide">SOC CONSOLE</div>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {NAV.map(({ to, label, icon: Icon, desc }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `group flex items-start gap-3 rounded-xl px-3 py-2.5 transition-colors ${
                isActive ? "bg-accent/10 text-ink ring-1 ring-accent/25" : "text-muted hover:bg-surface2 hover:text-ink"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={18} className={isActive ? "text-accent" : "text-faint group-hover:text-muted"} />
                <span className="min-w-0">
                  <span className="block text-[13.5px] font-medium leading-tight">{label}</span>
                  <span className="block text-[11px] text-faint">{desc}</span>
                </span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-edge p-4 text-[11.5px] text-faint">
        <div className="flex items-center gap-2 mb-1">
          <LiveDot running={feed.running} />
          <span className="text-muted font-medium">{feed.running ? "Capture live" : "Capture paused"}</span>
        </div>
        <div className="tnum">
          {feed.pps} pps · {feed.stats.total.toLocaleString()} pkts · {feed.stats.threats.toLocaleString()} threats
        </div>
      </div>
    </aside>
  );
}

export function MobileNav() {
  return (
    <nav className="md:hidden flex gap-1 overflow-x-auto border-b border-edge bg-surface/60 px-3 py-2">
      {NAV.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-[12.5px] font-medium ${
              isActive ? "bg-accent text-[#06181c]" : "text-muted bg-surface2"
            }`
          }
        >
          <Icon size={14} />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
