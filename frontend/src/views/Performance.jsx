import { Card, KpiCard, SectionHeader, Legend } from "../components/ui.jsx";
import { GroupedBars } from "../components/charts.jsx";
import { MODEL } from "../lib/theme.js";
import { kpis, sameDataset, far, dann, sameTable, calibration } from "../data/results.js";

const legendOf = (series) => series.map((s) => ({ name: s.name, color: MODEL[s.key] }));

export default function Performance() {
  return (
    <div>
      <SectionHeader
        eyebrow="Model benchmarks"
        title="Performance overview"
        sub="Same-dataset results for the three benchmarks. Classical trees lead on WSN-DS and CIC-IoT by 1–2 points; the class-weighted hybrid model wins on Edge-IIoTset by handling the rare Spoofing class."
      />

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        {kpis.map((k) => (
          <KpiCard key={k.label} {...k} />
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Classification accuracy by model" note="same-dataset · full 0–100% scale">
          <Legend items={legendOf(sameDataset.series)} />
          <GroupedBars
            groups={sameDataset.groups}
            series={sameDataset.series}
            max={100}
            ticks={[0, 25, 50, 75, 100]}
            unit="%"
            fmt={(v) => v.toFixed(2)}
          />
        </Card>

        <Card title="False alarm rate (FAR)" note="tree baselines · lower is better">
          <Legend items={legendOf(far.series)} />
          <GroupedBars
            groups={far.groups}
            series={far.series}
            max={10}
            ticks={[0, 2.5, 5, 7.5, 10]}
            unit="%"
            fmt={(v) => v.toFixed(2)}
          />
          <p className="mt-3 text-[12.5px] text-muted">
            Both trees fire on ~8–9% of benign CIC-IoT flows versus well under 1% elsewhere.
          </p>
        </Card>

        <Card title="Per-dataset model vs joint DANN" note="one DANN covers both datasets · accuracy %">
          <Legend items={legendOf(dann.series)} />
          <GroupedBars groups={dann.groups} series={dann.series} max={100} ticks={[0, 25, 50, 75, 100]} unit="%" />
          <div className="mt-3 rounded-xl border border-edge border-l-[3px] border-l-warn bg-warn/[0.07] px-4 py-3 text-[13px]">
            <span className="font-semibold text-warn">3-domain DANN failed to converge.</span>{" "}
            Adding WSN-DS plateaus threat accuracy at ~55% — routing-layer features share no structure with transport
            flows, so no domain-invariant representation exists.
          </div>
        </Card>

        <Card title="Confidence calibration" note="temperature scaling · ECE < 2% before scaling">
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="text-faint text-[11.5px] uppercase tracking-wide">
                  <th className="text-left font-semibold py-2 border-b border-edge">Dataset</th>
                  <th className="text-right font-semibold py-2 border-b border-edge">Temp&nbsp;T</th>
                  <th className="text-right font-semibold py-2 border-b border-edge">ECE before</th>
                  <th className="text-right font-semibold py-2 border-b border-edge">ECE after</th>
                </tr>
              </thead>
              <tbody>
                {calibration.map((r) => (
                  <tr key={r[0]} className="hover:bg-surface2">
                    <td className="py-2.5 border-b border-edgesoft">{r[0]}</td>
                    <td className="py-2.5 border-b border-edgesoft text-right tnum">{r[1].toFixed(3)}</td>
                    <td className="py-2.5 border-b border-edgesoft text-right tnum">{r[2].toFixed(2)}%</td>
                    <td className="py-2.5 border-b border-edgesoft text-right tnum">{r[3].toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[12.5px] text-muted">
            CIC-IoT's T = 1.495 is the most overconfident softmax, but its ECE is already lowest (0.23%).
          </p>
        </Card>
      </div>

      <Card title="Accuracy & training cost" note="accuracy (%), false alarm rate (%), training time (s)" className="mt-4">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-faint text-[11.5px] uppercase tracking-wide">
                {["Dataset", "RF acc", "XGB acc", "Hybrid acc", "RF FAR", "XGB FAR", "RF train", "XGB train"].map(
                  (h, i) => (
                    <th
                      key={h}
                      className={`${i === 0 ? "text-left" : "text-right"} font-semibold py-2 border-b border-edge`}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {sameTable.map((r) => {
                const best = Math.max(r[1], r[2], r[3]);
                const cell = (v, suffix = "", isBest = false) => (
                  <td className={`py-2.5 border-b border-edgesoft text-right tnum ${isBest ? "text-accent font-bold" : ""}`}>
                    {v}
                    {suffix}
                  </td>
                );
                return (
                  <tr key={r[0]} className="hover:bg-surface2">
                    <td className="py-2.5 border-b border-edgesoft">{r[0]}</td>
                    {cell(r[1].toFixed(2), "", r[1] === best)}
                    {cell(r[2].toFixed(2), "", r[2] === best)}
                    {cell(r[3].toFixed(2), "", r[3] === best)}
                    {cell(r[4].toFixed(2))}
                    {cell(r[5].toFixed(2))}
                    {cell(r[6].toFixed(1) + "s")}
                    {cell(r[7].toFixed(1) + "s")}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
