// Copy the phase-2 ROC export into public/ so the dev server and the build can
// serve it. Does nothing (successfully) if phase 2 hasn't been run yet — the
// dashboard then falls back to the operating-point approximation.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../data/processed/roc_curves.json");
const destDir = resolve(here, "../public");
const dest = resolve(destDir, "roc_curves.json");

if (!existsSync(src)) {
  console.log(
    "[sync:roc] data/processed/roc_curves.json not found — " +
      "dashboard will use the ROC approximation (run `python run_phase2.py` to generate it)"
  );
  process.exit(0);
}

mkdirSync(destDir, { recursive: true });
copyFileSync(src, dest);
console.log(`[sync:roc] copied roc_curves.json -> public/`);
