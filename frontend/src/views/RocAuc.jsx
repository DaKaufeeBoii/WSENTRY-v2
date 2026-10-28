import { useState, useMemo, useEffect } from "react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, CartesianGrid } from "recharts";
import { Card, SectionHeader } from "../components/ui.jsx";
import { perClass, DATASETS } from "../data/results.js";
import { C, THREAT } from "../lib/theme.js";
import { loadRealRoc } from "../lib/rocData.js";

const labelFor = (cid) => THREAT[cid]?.label ?? `Class ${cid}`;
const colorFor = (cid) => THREAT[cid]?.color ?? C.accent;

// Fallback: one-vs-rest operating point per class from the RF confusion matrix,
// interpolated to the corners. Used until phase 2 exports real probabilities.
function approxRoc(ds) {
  const d = perClass[ds];
  const M = d.confusion;
  const total = M.flat().reduce((a, b) => a + b, 0);
  const curves = d.classIds.map((cid, i) => {
    const tp = M[i][i];
    const fn = M[i].reduce((a, v, j) => a + (j === i ? 0 : v), 0);
    const fp = M.reduce((a, row, r) => a + (r === i ? 0 : row[i]), 0);
    const tn = total - tp - fn - fp;
    const tpr = tp + fn ? tp / (tp + fn) : 0;
    const fpr = fp + tn ? fp / (fp + tn) : 0;
    const auc = 0.5 * fpr * tpr + 0.5 * (tpr + 1) * (1 - fpr);
    return {
      cid,
      label: labelFor(cid),
      color: colorFor(cid),
      tpr,
      fpr,
      auc,
      points: [
        { x: 0, y: 0 },
        { x: fpr, y: tpr },
        { x: 1, y: 1 },
      ],
    };
  });
  return {
    measured: false,
    curves,
    macro: curves.reduce((a, c) => a + c.auc, 0) / curves.length,
    micro: null,
  };
}

export default function RocAuc() {
  const [ds, setDs] = useState(DATASETS[0]);
  const [real, setReal] = useState(null);

  useEffect(() => {
    let alive = true;
    loadRealRoc().then((r) => alive && setReal(r));
    return () => {
      alive = false;
    };
  }, []);

  const fallback = useMemo(() => approxRoc(ds), [ds]);
  const entry = real && real[ds];

  const view = entry
    ? {
        measured: true,
        curves: entry.curves.map((c) => ({
          cid: c.cid,
          label: labelFor(c.cid),
          color: colorFor(c.cid),
          auc: c.auc,
          points: c.points,
        })),
        macro: entry.macroAuc,
        micro: entry.microAuc,
      }
    : fallback;

  return (
    <div>
      <SectionHeader
        eyebrow={view.measured ? "Measured curves" : "Per-class operating points"}
        title="ROC / AUC"
        sub={
          view.measured
            ? "Threshold-swept one-vs-rest ROC curves computed from the hybrid model's exported probabilities. Each curve is measured across every decision threshold, so the AUC is exact."
            : "One-vs-rest true-positive vs false-positive rate per class, computed from the RF confusion matrix. The marked point is the model's measured operating point; the line interpolates through it to the corners."
        }
      />

      <div className="flex gap-2 flex-wrap mb-4 items-center">
        {DATASETS.map((d) => (
          <button
            key={d}
            onClick={() => setDs(d)}
            className={`rounded-lg border px-4 py-2 text-[13px] font-semibold transition-colors ${
              ds === d ? "bg-accent text-[#06181c] border-accent" : "bg-surface2 text-muted border-edge hover:text-ink"
            }`}
          >
            {d}
          </button>
        ))}
        <span
          className={`ml-auto inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11.5px] font-semibold ${
            view.measured ? "border-good/40 bg-good/10 text-good" : "border-warn/40 bg-warn/10 text-warn"
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${view.measured ? "bg-good" : "bg-warn"}`} />
          {view.measured ? "MEASURED" : "APPROXIMATED"}
        </span>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <Card
          title={`ROC curves · ${ds}`}
          note={
            view.measured
              ? "hybrid model, native features · diagonal = random classifier"
              : "RF confusion matrix · diagonal = random classifier"
          }
        >
          <ResponsiveContainer width="100%" height={340}>
            <LineChart margin={{ top: 10, right: 12, left: -6, bottom: 4 }}>
              <CartesianGrid stroke={C.grid} />
              <XAxis
                type="number"
                dataKey="x"
                domain={[0, 1]}
                ticks={[0, 0.25, 0.5, 0.75, 1]}
                tick={{ fill: C.faint, fontSize: 11 }}
                axisLine={{ stroke: C.axis }}
                tickLine={false}
                label={{ value: "False positive rate", position: "insideBottom", offset: -2, fill: C.faint, fontSize: 11 }}
              />
              <YAxis
                type="number"
                domain={[0, 1]}
                ticks={[0, 0.25, 0.5, 0.75, 1]}
                tick={{ fill: C.faint, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip
                content={({ active, payload }) =>
                  active && payload && payload.length ? (
                    <div className="rounded-lg border border-edge bg-surface2/95 px-3 py-2 text-[12px]">
                      <div className="tnum">
                        FPR {Number(payload[0].payload.x).toFixed(3)} · TPR {Number(payload[0].payload.y).toFixed(3)}
                      </div>
                    </div>
                  ) : null
                }
              />
              <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke={C.axis} strokeDasharray="4 4" />
              {view.curves.map((c) => (
                <Line
                  key={c.cid}
                  data={c.points}
                  type="linear"
                  dataKey="y"
                  name={c.label}
                  stroke={c.color}
                  strokeWidth={2}
                  // Swept curves carry many points; dots would be noise.
                  dot={view.measured ? false : { r: 3, fill: c.color, stroke: "none" }}
                  activeDot={{ r: 5 }}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-2 text-[12px] text-muted">
            {view.curves.map((c) => (
              <span key={c.cid} className="inline-flex items-center gap-2">
                <span className="w-3 h-3 rounded-[3px]" style={{ background: c.color }} />
                {c.label}
              </span>
            ))}
          </div>
        </Card>

        <div className="space-y-4">
          <Card
            title={view.measured ? "Per-class AUC" : "Operating points & approximate AUC"}
            note={view.measured ? "exact, from swept thresholds" : "derived from the confusion matrix"}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="text-faint text-[11.5px] uppercase tracking-wide">
                    <th className="text-left font-semibold py-2 border-b border-edge">Class</th>
                    {!view.measured && (
                      <>
                        <th className="text-right font-semibold py-2 border-b border-edge">TPR</th>
                        <th className="text-right font-semibold py-2 border-b border-edge">FPR</th>
                      </>
                    )}
                    <th className="text-right font-semibold py-2 border-b border-edge">
                      {view.measured ? "AUC" : "AUC≈"}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {view.curves.map((c) => (
                    <tr key={c.cid} className="hover:bg-surface2">
                      <td className="py-2.5 border-b border-edgesoft">
                        <span className="inline-flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-[2px]" style={{ background: c.color }} />
                          {c.label}
                        </span>
                      </td>
                      {!view.measured && (
                        <>
                          <td className="py-2.5 border-b border-edgesoft text-right tnum">{c.tpr.toFixed(3)}</td>
                          <td className="py-2.5 border-b border-edgesoft text-right tnum">{c.fpr.toFixed(3)}</td>
                        </>
                      )}
                      <td className="py-2.5 border-b border-edgesoft text-right tnum font-semibold">
                        {c.auc != null ? c.auc.toFixed(3) : "—"}
                      </td>
                    </tr>
                  ))}
                  <tr>
                    <td className="py-2.5 font-semibold text-accent">Macro average</td>
                    {!view.measured && (
                      <>
                        <td />
                        <td />
                      </>
                    )}
                    <td className="py-2.5 text-right tnum font-bold text-accent">
                      {view.macro != null ? view.macro.toFixed(3) : "—"}
                    </td>
                  </tr>
                  {view.measured && view.micro != null && (
                    <tr>
                      <td className="py-2.5 font-semibold text-muted">Micro average</td>
                      <td className="py-2.5 text-right tnum font-semibold text-muted">{view.micro.toFixed(3)}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {view.measured ? (
            <div className="rounded-2xl border border-edge border-l-[3px] border-l-good bg-good/[0.07] px-5 py-4 text-[13px]">
              <span className="block font-semibold text-good mb-1">Measured, not approximated</span>
              These curves come from{" "}
              <span className="font-mono text-[12px]">data/processed/roc_curves.json</span>, exported by{" "}
              <span className="font-mono text-[12px]">run_phase2.py</span> from the hybrid model's per-class
              probabilities on the native-feature test split. Note this is a different model from the RF
              confusion matrices shown under Per-Class Metrics.
            </div>
          ) : (
            <div className="rounded-2xl border border-edge border-l-[3px] border-l-warn bg-warn/[0.07] px-5 py-4 text-[13px]">
              <span className="block font-semibold text-warn mb-1">Approximation, not a swept ROC</span>
              A full threshold-swept ROC needs the per-class score arrays. Run{" "}
              <span className="font-mono text-[12px]">python run_phase2.py</span> to export{" "}
              <span className="font-mono text-[12px]">data/processed/roc_curves.json</span>; this view switches
              to the measured curves automatically. Until then it interpolates through the single measured
              operating point, so AUC is a lower-bound estimate.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
