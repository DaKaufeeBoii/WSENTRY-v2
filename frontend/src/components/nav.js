import { Activity, Grid3x3, Radar, Spline, Layers3, ShieldAlert, Crosshair } from "lucide-react";

export const NAV = [
  { to: "/demo", label: "Attack Demo", icon: Crosshair, desc: "Launch attacks live" },
  { to: "/performance", label: "Performance", icon: Activity, desc: "Model benchmarks" },
  { to: "/transfer", label: "Transfer Matrix", icon: Grid3x3, desc: "Cross-dataset gap" },
  { to: "/monitor", label: "Live SOC Monitor", icon: Radar, desc: "Test-set replay" },
  { to: "/roc", label: "ROC / AUC", icon: Spline, desc: "Per-class operating points" },
  { to: "/classes", label: "Per-Class Metrics", icon: Layers3, desc: "Precision · recall · F1" },
  { to: "/mitigation", label: "Mitigation Engine", icon: ShieldAlert, desc: "Firewall responses" },
];
