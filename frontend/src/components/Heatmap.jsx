import { transferColor, deltaColor, confColor, C } from "../lib/theme.js";

// Annotated heatmap as responsive SVG. mode: "transfer" | "delta" | "conf".
export function Heatmap({ rows, cols, matrix, mode = "transfer", fmt = (v) => v, rowTitle = "trained on", colTitle = "tested on" }) {
  const n = rows.length;
  const m = cols.length;
  const cell = Math.min(78, Math.floor(430 / m));
  const lab = 48;
  const top = 26;
  const W = lab + m * cell + 6;
  const H = top + n * cell + lab;
  const rowSums = matrix.map((r) => r.reduce((a, b) => a + b, 0));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" style={{ overflow: "visible" }} role="img">
      <text x={lab + (m * cell) / 2} y={12} textAnchor="middle" fill={C.faint} fontSize={10.5}>{colTitle}</text>
      <text
        x={14}
        y={top + (n * cell) / 2}
        textAnchor="middle"
        fill={C.faint}
        fontSize={10.5}
        transform={`rotate(-90 14 ${top + (n * cell) / 2})`}
      >
        {rowTitle}
      </text>
      {cols.map((c, j) => (
        <text key={c} x={lab + j * cell + cell / 2} y={top - 8} textAnchor="middle" fill={C.muted} fontSize={11.5}>
          {c}
        </text>
      ))}
      {rows.map((r, i) => (
        <text key={r} x={lab - 8} y={top + i * cell + cell / 2 + 4} textAnchor="end" fill={C.muted} fontSize={11.5}>
          {r}
        </text>
      ))}
      {matrix.map((row, i) =>
        row.map((v, j) => {
          let fill, txt = "#fff";
          if (mode === "transfer") fill = transferColor(v);
          else if (mode === "delta") fill = deltaColor(v);
          else {
            const frac = rowSums[i] ? v / rowSums[i] : 0;
            fill = confColor(frac);
            if (frac < 0.06) txt = C.faint;
          }
          const x = lab + j * cell;
          const y = top + i * cell;
          const fs = cell >= 58 ? 13 : 11;
          const diag = i === j && mode !== "delta";
          return (
            <g key={`${i}-${j}`}>
              <rect
                x={x + 1}
                y={y + 1}
                width={cell - 2}
                height={cell - 2}
                rx={5}
                fill={fill}
                stroke={diag ? C.accent : "none"}
                strokeWidth={diag ? 1.4 : 0}
              >
                <title>{`${rows[i]} → ${cols[j]}: ${fmt(v)}`}</title>
              </rect>
              <text x={x + cell / 2} y={y + cell / 2 + fs / 3} textAnchor="middle" fill={txt} fontSize={fs} fontWeight={650} style={{ fontVariantNumeric: "tabular-nums" }}>
                {fmt(v)}
              </text>
            </g>
          );
        })
      )}
    </svg>
  );
}
