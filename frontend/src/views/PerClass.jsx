import { useState } from "react";
import { Card, SectionHeader, Legend, Meter } from "../components/ui.jsx";
import { GroupedBars } from "../components/charts.jsx";
import { Heatmap } from "../components/Heatmap.jsx";
import { perClass, DATASETS } from "../data/results.js";
import { MODEL, THREAT, compact } from "../lib/theme.js";

export default function PerClass() {
  const [ds, setDs] = useState(DATASETS[0]);
  const d = perClass[ds];
  const totalSupport = d.support.reduce((a, b) => a + b, 0);

  const series = [
    { name: "Precision", color: MODEL.rf, vals: d.precision },
    { name: "Recall", color: MODEL.xgb, vals: d.recall },
    { name: "F1", color: MODEL.hybrid, vals: d.f1 },
  ];

  return (
    <div>
      <SectionHeader
        eyebrow="Precision · recall · F1"
        title="Per-class behavior"
        sub="Per-class metrics and the confusion matrix for the RF model. Headline accuracy hides minority-class difficulty — most starkly Edge-IIoTset's Spoofing class."
      />

      <div className="flex gap-2 flex-wrap mb-4">
        {DATASETS.map((name) => (
          <button
            key={name}
            onClick={() => setDs(name)}
            className={`rounded-lg border px-4 py-2 text-[13px] font-semibold transition-colors ${
              ds === name ? "bg-accent text-[#06181c] border-accent" : "bg-surface2 text-muted border-edge hover:text-ink"
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <Card title={`Per-class metrics · ${ds}`} note="RF model">
          <Legend items={series.map((s) => ({ name: s.name, color: s.color }))} />
          <GroupedBars groups={d.classes} series={series} max={1} ticks={[0, 0.25, 0.5, 0.75, 1]} fmt={(v) => v.toFixed(2)} />
        </Card>

        <Card title="Confusion matrix" note="rows = true, columns = predicted · counts">
          <div className="overflow-x-auto">
            <Heatmap
              rows={d.classes}
              cols={d.classes}
              matrix={d.confusion}
              mode="conf"
              rowTitle="true"
              colTitle="predicted"
              fmt={compact}
            />
          </div>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mt-4">
        <Card title="Class distribution" note={`test split · ${totalSupport.toLocaleString()} samples`}>
          <div className="space-y-3">
            {d.classes.map((label, i) => {
              const cid = d.classIds[i];
              const pct = (d.support[i] / totalSupport) * 100;
              return (
                <div key={label}>
                  <div className="flex items-center justify-between text-[12.5px] mb-1">
                    <span className="inline-flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-[2px]" style={{ background: THREAT[cid].color }} />
                      {label}
                    </span>
                    <span className="tnum text-muted">
                      {d.support[i].toLocaleString()} · {pct.toFixed(pct < 1 ? 2 : 1)}%
                    </span>
                  </div>
                  <Meter value={d.support[i]} max={totalSupport} color={THREAT[cid].color} height={6} />
                </div>
              );
            })}
          </div>
        </Card>

        <div className="rounded-2xl border border-edge border-l-[3px] border-l-warn bg-warn/[0.07] px-5 py-4 text-[13.5px] self-start">
          <span className="block font-semibold text-warn mb-1">Reading {ds}</span>
          {d.note}
        </div>
      </div>
    </div>
  );
}
