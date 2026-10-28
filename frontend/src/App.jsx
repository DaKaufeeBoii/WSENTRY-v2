import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Sidebar, MobileNav } from "./components/Sidebar.jsx";
import { Topbar } from "./components/Topbar.jsx";
import { feed } from "./lib/mockFeed.js";
import Performance from "./views/Performance.jsx";
import TransferMatrix from "./views/TransferMatrix.jsx";
import LiveMonitor from "./views/LiveMonitor.jsx";
import RocAuc from "./views/RocAuc.jsx";
import PerClass from "./views/PerClass.jsx";
import Mitigation from "./views/Mitigation.jsx";

export default function App() {
  useEffect(() => {
    feed.start();
  }, []);

  return (
    <div className="flex h-full w-full overflow-hidden bg-bg text-ink">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <MobileNav />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1200px] px-4 md:px-6 py-6">
            <Routes>
              <Route path="/" element={<Navigate to="/performance" replace />} />
              <Route path="/performance" element={<Performance />} />
              <Route path="/transfer" element={<TransferMatrix />} />
              <Route path="/monitor" element={<LiveMonitor />} />
              <Route path="/roc" element={<RocAuc />} />
              <Route path="/classes" element={<PerClass />} />
              <Route path="/mitigation" element={<Mitigation />} />
              <Route path="*" element={<Navigate to="/performance" replace />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
}
