// W-SENTRY experimental results — ported verbatim from
// data/processed/phase1_results.json and phase2_results.json.
// The log-normalization ablation figure is from the paper draft (Table VI).

export const DATASETS = ["WSN-DS", "CIC-IoT-2023", "Edge-IIoTset"];
export const TM_LABELS = ["WSN", "CIC", "Edge"];

// Unified 5-class taxonomy.
export const THREAT_LABELS = {
  0: "Normal",
  1: "Jamming",
  2: "Spoofing",
  3: "DoS",
  4: "Intrusion",
};

// Same-dataset accuracy (%) by model.
export const sameDataset = {
  groups: DATASETS,
  series: [
    { name: "RF", key: "rf", vals: [99.6, 99.42, 92.06] },
    { name: "XGBoost", key: "xgb", vals: [99.56, 99.44, 91.92] },
    { name: "Hybrid DL", key: "hybrid", vals: [98.06, 97.8, 94.39] },
  ],
};

// False alarm rate (%) — tree baselines only (phase 1).
export const far = {
  groups: DATASETS,
  series: [
    { name: "RF", key: "rf", vals: [0.29, 8.24, 0.59] },
    { name: "XGBoost", key: "xgb", vals: [0.33, 9.31, 0.58] },
  ],
};

// dataset, rfAcc, xgbAcc, dlAcc, rfFar, xgbFar, rfTrain(s), xgbTrain(s)
export const sameTable = [
  ["WSN-DS", 99.6, 99.56, 98.06, 0.29, 0.33, 117.16, 24.87],
  ["CIC-IoT-2023", 99.42, 99.44, 97.8, 8.24, 9.31, 32.79, 35.41],
  ["Edge-IIoTset", 92.06, 91.92, 94.39, 0.59, 0.58, 10.4, 26.19],
];

// 3x3 transfer matrices (rows = trained on, cols = tested on), accuracy %.
export const transferRF = [
  [99.6, 0.18, 11.94],
  [1.26, 99.42, 26.3],
  [1.9, 67.64, 92.06],
];
export const transferDL = [
  [97.79, 0.3, 80.7],
  [0.99, 97.79, 15.4],
  [26.96, 61.77, 97.42],
];
export const transferDelta = transferDL.map((row, i) =>
  row.map((v, j) => +(v - transferRF[i][j]).toFixed(1))
);

// DANN two-domain (CIC + Edge) vs per-dataset hybrid (behavioral diagonal).
export const dann = {
  groups: ["CIC-IoT", "Edge-IIoT"],
  series: [
    { name: "Per-dataset hybrid", key: "hybrid", vals: [97.79, 97.42] },
    { name: "DANN (joint)", key: "dann", vals: [96.5, 96.29] },
  ],
};

// Edge-IIoTset log-normalization ablation (paper Table VI).
export const ablation = {
  before: { label: "Clip + RobustScaler", acc: 56.8 },
  after: { label: "Log + clip + RobustScaler", acc: 94.39 },
  delta: 37.59,
};

// dataset, temperature T, ECE before (%), ECE after (%)
export const calibration = [
  ["WSN-DS", 1.04, 1.7, 1.86],
  ["CIC-IoT", 1.495, 0.23, 0.43],
  ["Edge-IIoT", 1.077, 1.78, 2.04],
];

// Per-class metrics + confusion matrices (RF model).
export const perClass = {
  "WSN-DS": {
    classes: ["Normal", "Jamming", "Spoofing", "DoS"],
    classIds: [0, 1, 2, 3],
    precision: [1.0, 0.95, 0.99, 0.91],
    recall: [1.0, 0.93, 1.0, 1.0],
    f1: [1.0, 0.94, 0.99, 0.95],
    support: [68014, 1328, 4929, 662],
    confusion: [
      [67818, 67, 65, 64],
      [93, 1233, 2, 0],
      [9, 0, 4920, 0],
      [2, 0, 0, 660],
    ],
    note:
      "All four classes clear F1 0.94. The weakest, DoS/Flooding, still hits recall 1.00 — errors are benign flows flagged as attacks, not missed attacks.",
  },
  "CIC-IoT-2023": {
    classes: ["Normal", "Spoofing", "DoS", "Intrusion"],
    classIds: [0, 2, 3, 4],
    precision: [0.91, 0.83, 1.0, 0.79],
    recall: [0.92, 0.79, 1.0, 0.82],
    f1: [0.91, 0.81, 1.0, 0.8],
    support: [934, 421, 38307, 335],
    confusion: [
      [857, 46, 0, 31],
      [50, 334, 0, 37],
      [0, 0, 38301, 6],
      [35, 21, 4, 275],
    ],
    note:
      "DoS/Flooding is near-perfect (F1 1.00) because it dominates the sample; Normal, Spoofing and Intrusion trade misclassifications among themselves (F1 0.80–0.91).",
  },
  "Edge-IIoTset": {
    classes: ["Normal", "Spoofing", "DoS", "Intrusion"],
    classIds: [0, 2, 3, 4],
    precision: [1.0, 0.01, 0.92, 0.92],
    recall: [0.99, 1.0, 0.57, 0.92],
    f1: [1.0, 0.02, 0.7, 0.92],
    support: [29121, 22, 6092, 4764],
    confusion: [
      [28948, 108, 1, 64],
      [0, 22, 0, 0],
      [0, 2298, 3463, 331],
      [1, 79, 294, 4390],
    ],
    note:
      "The minority-class failure: Spoofing has just 22 test samples. RF catches all 22 (recall 1.00) but floods the class with false positives — precision 0.01, F1 0.02. This is the gap the class-weighted hybrid model narrows.",
  },
};

export const kpis = [
  { label: "Hybrid DL · WSN-DS", value: 98.06, unit: "%", sub: "same-dataset accuracy" },
  { label: "Hybrid DL · CIC-IoT", value: 97.8, unit: "%", sub: "same-dataset accuracy" },
  { label: "Hybrid DL · Edge-IIoT", value: 94.39, unit: "%", sub: "beats RF by +2.3 pt" },
  { label: "WSN → Edge transfer", value: 80.7, unit: "%", sub: "up from 11.9% (RF)", highlight: true },
  { label: "DANN joint (CIC+Edge)", value: 96.4, unit: "%", sub: "one model, no tuning" },
];

// Derived transfer summary.
export const transferSummary = {
  rfOffDiag: 18.2,
  dlOffDiag: 31.0,
  domainGap: 78.8,
  diagAvg: 97.0,
};
