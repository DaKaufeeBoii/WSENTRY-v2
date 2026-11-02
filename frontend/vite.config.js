import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "./" keeps asset paths relative so the built app works from any subpath.
// The live demo's network + model backend is scripts/detector_server.py (port 8000);
// the dashboard talks to it directly, so no dev-server bridge is needed here.
// strictPort: attacker.py and the firewall rule expect 5173.
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { port: 5173, strictPort: true, host: true },
});
