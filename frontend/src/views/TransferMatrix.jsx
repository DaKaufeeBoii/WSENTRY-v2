import { Card, SectionHeader, Stat } from "../components/ui.jsx";
import { Heatmap } from "../components/Heatmap.jsx";
import { TM_LABELS, transferRF, transferDL, transferDelta, transferSummary } from "../data/results.js";
import { C } from "../lib/theme.js";

function Ramp({ from, mid, to, lo, hi }) {
  return (
    <div className="flex items-center gap-2 mt-3 text-[11px] text-faint">
      <span>{lo}</span>
      <span
        className="h-2 flex-1 max-w-[180px] rounded-full"
        style={{ background: `linear-gradient(90deg, ${from}, ${mid}, ${to})` }}
      />
      <span>{hi}</span>
    </div>
  );
}

export default function TransferMatrix() {
  return (
    <div>
      <SectionHeader
        eyebrow="Cross-dataset gap"
        title="Transfer matrix"
        sub="Train on the row dataset, test on the column dataset. The diagonal is same-dataset accuracy; everything off it measures the domain gap. The RF baseline collapses off-diagonal; the hybrid model with behavioral features recovers much of it — most dramatically WSN→Edge."
      />

      <div className="grid md:grid-cols-3 gap-4">
        <Card title="RF baseline" note="native features · accuracy %">
          <div className="overflow-x-auto">
            <Heatmap rows={TM_LABELS} cols={TM_LABELS} matrix={transferRF} mode="transfer" fmt={(v) => v.toFixed(1)} />
          </div>
          <Ramp from="hsl(0 58% 40%)" mid="hsl(70 58% 40%)" to="hsl(140 58% 40%)" lo="0%" hi="100%" />
        </Card>

        <Card title="Hybrid CNN-BiLSTM-Attn" note="behavioral features · accuracy %">
          <div className="overflow-x-auto">
            <Heatmap rows={TM_LABELS} cols={TM_LABELS} matrix={transferDL} mode="transfer" fmt={(v) => v.toFixed(1)} />
          </div>
          <Ramp from="hsl(0 58% 40%)" mid="hsl(70 58% 40%)" to="hsl(140 58% 40%)" lo="0%" hi="100%" />
        </Card>

        <Card title="Change (Hybrid − RF)" note="percentage-point delta">
          <div className="overflow-x-auto">
            <Heatmap
              rows={TM_LABELS}
              cols={TM_LABELS}
              matrix={transferDelta}
              mode="delta"
              fmt={(v) => (v > 0 ? "+" : "") + v.toFixed(1)}
            />
          </div>
          <Ramp from="hsl(0 55% 38%)" mid="#2a2a28" to="hsl(140 55% 38%)" lo="−12" hi="+69" />
        </Card>
      </div>

      <div className="grid md:grid-cols-2 gap-4 mt-4">
        <div className="rounded-2xl border border-edge border-l-[3px] border-l-accent bg-accent/[0.08] px-5 py-4 text-[13.5px]">
          <span className="block font-semibold text-accent mb-1">WSN→Edge: 11.9% → 80.7%</span>
          The deep model's behavioral features transfer routing-derived signal to Edge traffic — a <b>+68.8&nbsp;pt</b>{" "}
          jump. The reverse (Edge→WSN) stays low at 27%: transport patterns don't map back to routing semantics.
        </div>
        <Card>
          <div className="flex flex-col gap-3.5 justify-center h-full">
            <Stat label="Off-diagonal avg · RF" value={`${transferSummary.rfOffDiag}%`} color={C.bad} />
            <Stat label="Off-diagonal avg · Hybrid" value={`${transferSummary.dlOffDiag}%`} color={C.good} />
            <div className="border-t border-edge pt-3">
              <Stat label="Domain gap (RF, diag − off-diag)" value={`${transferSummary.domainGap} pt`} />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
