# W-SENTRY two-laptop live demo — architecture & diagnosis

How the networked demo works end to end, so a person or a coding agent can run it,
understand each part, and diagnose failures. The key property: the **real trained
model runs live** on laptop A and classifies the feature artifacts laptop B sends;
the model's own output drives detection and the block decision.

## 1. What is real and what is a prop

| Part | Real? | Detail |
|------|-------|--------|
| The network link between the laptops | **Real** | Laptop B discovers laptop A and sends it HTTP requests over the LAN. |
| The attacker's IP on the dashboard | **Real** | The source address laptop A's server saw on the request. |
| **The model's classification** | **Real, live** | Laptop A loads `models/saved/hybrid_model.pt` and runs it on every artifact laptop B sends. The class and confidence shown are the model's actual output, computed at that moment. |
| **The block decision** | **Real** | When the model flags a source with confidence ≥ 0.85, the detector blocks that IP and **refuses its next requests with HTTP 403**. Laptop B's terminal shows the 403s. |
| The attack "traffic" | **Prop** | Laptop B sends real held-out dataset records (20-feature sequences) over HTTP — not real flood/scan/spoof packets. No host is actually attacked. |
| The OS firewall rule (`netsh ...`) | **Prop (dry run)** | The command string is generated and shown, not executed. |

No real attack tools (hping3, nmap, arpspoof) are used. The "attack" is **real
model input** (dataset feature vectors) sent over HTTP; the model classifies it live.

## 2. The two machines

```
  LAPTOP B (attacker)                       LAPTOP A (detector)
  ┌────────────────────────┐                ┌────────────────────────────────────────┐
  │ scripts/attacker.py     │                │ scripts/detector_server.py  (port 8000) │
  │  attack_samples.json    │  UDP 50505 ───▶│   UDP discovery responder                │
  │  (real feature vectors) │  HTTP 8000 ───▶│   /api/connect /heartbeat /attack …      │
  │                         │◀── 200 / 403 ──│   InferenceEngine → hybrid_model.pt      │  ← REAL MODEL
  └────────────────────────┘                │        │ classify + mitigate              │
                                             │        │ SSE push                         │
                                             │        ▼                                  │
  ┌────────────────────────┐   SSE/HTTP      │   /api/events                            │
  │ dashboard (Vite 5173)   │◀──────────────▶│                                          │
  │  AttackDemo page        │   :8000/api     └────────────────────────────────────────┘
  └────────────────────────┘
```

Both the detector server and the dashboard run on **laptop A**. The dashboard
(port 5173) subscribes to the detector (port 8000) and renders what the model decided.

## 3. Processes to start on laptop A

1. **The dashboard** (needs Node):
   ```bash
   npm --prefix frontend run dev
   ```
2. **The live model server** (needs the project Python venv with torch):
   ```bash
   .venv/Scripts/python.exe scripts/detector_server.py
   ```
   It prints its LAN addresses and loads `models/saved/hybrid_model.pt`. If this is
   not running, the dashboard's Network link panel shows "model server offline".

Firewall (admin PowerShell, once) — the attacker reaches the **detector**, not the dashboard:
```bash
netsh advfirewall firewall add rule name="W-SENTRY model" dir=in action=allow protocol=TCP localport=8000
```
```bash
netsh advfirewall firewall add rule name="W-SENTRY discovery" dir=in action=allow protocol=UDP localport=50505
```

## 4. Discovery — how laptop B finds laptop A without an IP

`find_target()` in `attacker.py`, in order:
1. **UDP broadcast** `WSENTRY_DISCOVER` → `255.255.255.255:50505` and each `*.255`;
   the detector replies `{"wsentry":true,"host","port":8000}`.
2. **Saved / known IP** — `scripts/.wsentry_target` (last that worked), then the
   `KNOWN_TARGET` constant; each confirmed with `GET /api/hello`.
3. **Subnet scan** — `GET /api/hello` on every host of each local subnet.

Falls back to a typed IP: `python attacker.py <ip> dos`.

## 5. API (detector server, port 8000; CORS open so the dashboard can read it)

| Endpoint | Method | Body | Returns | Purpose |
|----------|--------|------|---------|---------|
| `/api/hello` | GET | — | `{wsentry,host}` | discovery confirm |
| `/api/connect` | POST | `{name,os,via}` | `{ok,detector,you}` | handshake |
| `/api/heartbeat` | POST | `{}` | `{ok,blocked}` | keep-alive (2 s) |
| `/api/attack` | POST | `{kind,samples:[[5][20]…]}` | `{ok,classified,action}` or `403 {blocked}` | **runs the model on the samples** |
| `/api/protection` | POST | `{on}` | `{ok}` | dashboard ON/OFF; off = classify but never block |
| `/api/events` | GET | — | SSE | detector → dashboard |
| `/api/block` /`/api/unblock` | POST | `{ip?}` | `{ok}` | manual block / clear |

`kind` ∈ `dos,scan,spoof,jam` (just the family the attacker drew from; the model
classifies independently). `samples` are real held-out sequences from `attack_samples.json`.

## 6. Data flow of one attack

1. Laptop B posts `/api/attack {kind:"dos", samples:[…real feature sequences…]}`.
2. Detector: if that IP is already blocked → `403` + SSE `refused`. Otherwise it runs
   `InferenceEngine.predict_batch(samples)` — **the real model** — getting (class, confidence)
   per sample.
3. `mitigate()` applies the policy: class > 0 and confidence ≥ 0.85 → block the IP
   (DoS/Spoof/Probe) or alert only (Jamming). A blocked IP is refused from then on.
4. Detector pushes SSE `attack {ip, results:[{cls,conf}], action, rule}`.
5. Dashboard `mockFeed.js` `ingest()` renders the model's real verdicts: per-packet class,
   the detection step, the mitigation step, and before/after IP status. `refused` events
   become dropped packets.

## 7. Running the attack (laptop B, two terminals)

```bash
python attacker.py connect
```
```bash
python attacker.py dos
```
Also `scan`, `spoof`, `jam`; `--duration 20`. Needs `attack_samples.json` beside the script.

## 8. Diagnosis — common failures

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Network link panel: "model server offline" | `detector_server.py` not running, or port 8000 blocked | Start it with the venv python; add the TCP 8000 firewall rule. |
| Dashboard loads but no devices/attacks | dashboard can't reach `:8000` (CORS/port) | Confirm `http://<hostA>:8000/api/hello` works in a browser; both processes on laptop A. |
| "Could not find W-SENTRY on this network" | different networks or UDP 50505 blocked | One hotspot; add the UDP rule; or pass the IP by hand. |
| `attack_samples.json not found` | file not copied to laptop B | `python scripts/make_attack_samples.py` on laptop A, copy the JSON next to `attacker.py`. |
| Model loads slowly / first attack lags | torch cold start | Start `detector_server.py` a minute early; it prints "model ready." |
| Attack never blocked even with W-SENTRY ON | confidence < 0.85, or protection OFF | Use DoS/scan (high confidence); toggle **W-SENTRY ON**. |
| Everything blocked even with OFF | two detector instances bound to 8000 | Kill all `detector_server.py`, start exactly one. |
| Jamming never blocks | by design | RF jamming can't be firewalled; policy is alert-only. |

## 9. Files

- `scripts/detector_server.py` — laptop A: loads the real model, runs it per attack, SSE + UDP discovery.
- `scripts/make_attack_samples.py` — builds `attack_samples.json` from the held-out split (features only).
- `scripts/attacker.py` — laptop B: discovery, handshake, heartbeat, sends real feature artifacts.
- `scripts/attack_samples.json` — real held-out feature sequences grouped by attack family.
- `frontend/src/lib/mockFeed.js` — dashboard feed: `onBridge`, `ingest`, `refused`, subscribes to `:8000`.
- `frontend/src/views/AttackDemo.jsx` — the Attack Demo page.
- `src/live/inference.py` — `InferenceEngine`, the model wrapper the detector uses.
