// Loads the measured ROC curves exported by run_phase2.py, when they exist.
//
// `npm run dev` / `npm run build` copy data/processed/roc_curves.json into
// public/ via scripts/sync-roc.mjs. If phase 2 hasn't been run the file is
// absent, the fetch fails, and the ROC view falls back to the single
// operating-point approximation derived from the confusion matrices.

// The export keys datasets by their short phase-2 config names.
const KEY_FOR_DATASET = {
  "WSN-DS": "WSN",
  "CIC-IoT-2023": "CIC",
  "Edge-IIoTset": "Edge",
};

function normalizeEntry(entry) {
  if (!entry || !Array.isArray(entry.curves)) return null;
  const curves = entry.curves
    .filter(
      (c) =>
        Array.isArray(c.fpr) &&
        Array.isArray(c.tpr) &&
        c.fpr.length === c.tpr.length &&
        c.fpr.length > 1
    )
    .map((c) => ({
      cid: Number(c.class_id),
      auc: typeof c.auc === "number" ? c.auc : null,
      points: c.fpr.map((x, i) => ({ x, y: c.tpr[i] })),
    }));
  if (!curves.length) return null;
  return {
    curves,
    macroAuc: typeof entry.macro_auc === "number" ? entry.macro_auc : null,
    microAuc: typeof entry.micro_auc === "number" ? entry.micro_auc : null,
  };
}

/**
 * Returns { [datasetName]: { curves, macroAuc, microAuc } } or null when the
 * export is unavailable or unusable. Never throws.
 */
export async function loadRealRoc() {
  try {
    const url = `${import.meta.env.BASE_URL}roc_curves.json`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    const raw = await res.json();
    if (!raw || typeof raw !== "object") return null;

    const out = {};
    for (const [dataset, key] of Object.entries(KEY_FOR_DATASET)) {
      const norm = normalizeEntry(raw[key]);
      if (norm) out[dataset] = norm;
    }
    return Object.keys(out).length ? out : null;
  } catch {
    // Missing file, bad JSON, non-JSON 404 page — all mean "use the fallback".
    return null;
  }
}
