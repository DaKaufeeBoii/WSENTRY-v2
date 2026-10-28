# W-SENTRY SOC Dashboard

An obsidian-themed React + Vite Security Operations Center for the W-SENTRY
cross-domain intrusion detection project. It visualizes the Phase 1/2 results
and runs a **self-contained, simulated live monitor** — no Python backend
required to demo it.

## Run

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

Build a static bundle:

```bash
npm run build && npm run preview
```

## Views

| Route          | View                | Source                                                        |
|----------------|---------------------|---------------------------------------------------------------|
| `/performance` | Performance overview| same-dataset accuracy, FAR, DANN, calibration (real results)  |
| `/transfer`    | Transfer matrix     | RF vs hybrid 3×3 transfer heatmaps + delta (real results)     |
| `/monitor`     | Live SOC monitor    | **simulated** packet stream, classified in-browser            |
| `/roc`         | ROC / AUC           | measured curves from `roc_curves.json`, else an operating-point fallback |
| `/classes`     | Per-class metrics   | precision/recall/F1 + confusion matrices (real results)       |
| `/mitigation`  | Mitigation engine   | **simulated** firewall response log + manual block/unblock    |

## What is real vs simulated

- **Real** — every number in Performance, Transfer, Per-Class, and the ROC
  operating points is ported verbatim from `data/processed/phase1_results.json`
  and `phase2_results.json` (see `src/data/results.js`). The log-normalization
  figure comes from the paper draft (Table VI).
- **Simulated** — the Live Monitor and Mitigation views are driven entirely by
  a client-side generator (`src/lib/mockFeed.js`). No packets are captured, no
  model runs, and no firewall rule is ever executed; the `netsh` / `iptables`
  command strings are illustrative only. This lets the dashboard demo the SOC
  workflow standalone. Wire it to the FastAPI backend later by replacing the
  `feed` store with a WebSocket client that emits the same packet/mitigation
  shapes.
- **Measured when available** — the ROC view reads
  `data/processed/roc_curves.json`, exported by `run_phase2.py` and copied into
  `public/` by `npm run sync:roc` (which `predev` and `prebuild` run for you).
  When that file is present the view shows real threshold-swept curves and
  labels itself **MEASURED**; those curves come from the hybrid model on native
  features, which is a different model from the RF confusion matrices under
  Per-Class Metrics. When the file is absent it falls back to interpolating
  through a single operating point and labels itself **APPROXIMATED**.

## Theme

Obsidian palette (`#09090B` bg, `#18181B` cards, `#27272A` borders, `#22D3EE`
cyan accent), matching `paper/w-sentry-results.html`. Tokens live in
`tailwind.config.js` and `src/lib/theme.js`.

## Stack

React 18 · Vite 5 · Tailwind CSS 3 · Recharts 2 · lucide-react · react-router-dom (HashRouter).
