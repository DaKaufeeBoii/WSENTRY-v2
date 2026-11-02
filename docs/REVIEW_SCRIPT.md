# W-SENTRY Review Script (4 speakers, 10–15 min + Q&A)

Team: Riteesh Thiruveedhula, M. Vikas Goud, Shaik Gafar, V. Sai Tarun Reddy. Decide who is Speaker 1–4 before you go in.

Rules for everyone:
- Every number below comes from `data/processed/phase1_results.json` (P1), `data/processed/phase2_results.json` (P2) or `data/processed/showcase_eval.json` (SE). Don't use any other number.
- Never say "56.8% → 94.39%", "+37.6 points" or "closes 85% of the gap". No saved run backs those numbers.
- Never say temperature scaling improved calibration. It didn't.
- If you don't know an answer, say "we didn't measure that", then say what we did measure.

---

## Speaker 1: The problem (~3 min)

[cue: title slide]

Good morning. We are presenting W-SENTRY, a cross-domain intrusion detection system for wireless and IoT networks.

[cue: motivation slide]

IoT and wireless sensor networks are everywhere: smart homes, factories, field sensors.
They are attacked with floods, spoofing, scanning and jamming.
Most research trains an intrusion detector on one dataset and tests it on the same dataset.
The reported accuracies are very high, often above 99 percent.
We asked a simple question: does that accuracy survive when the network changes?

[cue: datasets slide]

We used three public datasets that come from very different kinds of networks.
- WSN-DS is a wireless sensor network dataset with routing and scheduling attacks. Our copy has 374,661 records.
- CICIoT2023 is smart-home IoT traffic. Our Kaggle copy has 1,048,575 records. That is exactly Excel's row limit, so the copy is truncated.
- Edge-IIoTset is industrial IoT traffic with many protocols, such as MQTT, Modbus and DNS.

We mapped every dataset's labels onto one five-class taxonomy: Normal, Jamming, Spoofing, DoS, and Intrusion or Probe.

[cue: Phase 1 results slide]

Phase 1 was the baseline. We trained Random Forest and XGBoost on each dataset's own features.
On the same dataset, the numbers look excellent.
Random Forest gets 99.6 percent on WSN-DS, 99.42 percent on CICIoT2023 and 92.06 percent on Edge-IIoTset. XGBoost is almost identical.

[cue: transfer matrix slide]

Then we trained on one dataset and tested on another.
Accuracy collapsed.
Trained on WSN-DS and tested on Edge-IIoTset, Random Forest gets 11.94 percent.
Trained on Edge-IIoTset and tested on WSN-DS, it gets 1.9 percent.
WSN-DS to CICIoT2023 gives 0.18 percent.

So same-dataset accuracy is not evidence that a detector will work on a new network.
That is the problem the rest of our project works on.
Over to [Speaker 2].

---

## Speaker 2: The approach (~3 min)

[cue: approach overview slide]

Our approach has four parts: shared behavioral features, log normalization, a hybrid deep model, and domain adversarial training.

[cue: behavioral features slide]

First, features. Each dataset ships with its own columns, so a model trained on one has nothing to read in another.
We defined 20 behavioral features that every dataset can fill in, such as volume, rate, the SYN ratio, the ACK ratio, port spread and timing.
We call these protocol-agnostic. To be honest, we mapped each dataset's columns onto these 20 slots by hand, and that mapping has not been validated as a common representation.

[cue: preprocessing slide]

Second, preprocessing. Some raw fields, such as TCP sequence and acknowledgement numbers, reach into the billions.
Values that large wreck gradient-based training.
So we apply a signed log, sign of x times log of one plus the absolute value, clip to minus 50 to 50, and then fit a robust scaler on the training data only.

[cue: hybrid model slide]

Third, the model. It's a hybrid CNN, BiLSTM and attention network.
The 1-D convolution picks up local patterns across features.
The bidirectional LSTM reads a window of five records.
Attention pools the LSTM outputs into one vector, and a dense head outputs the five classes.
On each dataset's native features, it gets 98.06 percent on WSN-DS, 97.8 percent on CICIoT2023 and 94.39 percent on Edge-IIoTset.

[cue: DANN slide]

Fourth, DANN, the domain adversarial neural network.
A shared encoder feeds two heads: one predicts the threat, the other predicts which dataset the sample came from.
Between the encoder and the domain head sits a gradient reversal layer. It pushes the encoder toward features that hide the source dataset.
We trained one unified model on CICIoT2023 and Edge-IIoTset together, using labels from both.
It gets 96.5 percent on CICIoT2023 and 96.29 percent on Edge-IIoTset.
Because it saw labels from both datasets, this is a unified model, not a transfer result.

[cue: behavioral transfer slide]

Did the behavioral features help transfer? Partly.
WSN-DS to Edge-IIoTset rose from 11.94 percent with native features to 80.7 percent with behavioral features.
Edge-IIoTset to WSN-DS rose from 1.9 to 26.96 percent.
But WSN-DS and CICIoT2023 still don't transfer in either direction: 0.3 and 0.99 percent.
And CICIoT2023 to Edge-IIoTset got worse, from 26.3 to 15.4 percent.
We report all of these, not only the good ones.
Over to [Speaker 3] for the system.

---

## Speaker 3: The system (~3 min)

[cue: architecture diagram]

Results on paper are one thing. We also built a working security operations system around the model.
It has four layers.

[cue: point at layer 1]

Layer one is data. The demo replays our held-out test set: records the model never saw during training.
Each record goes through the same preprocessing as training: signed log, clipping, and the saved robust scaler.

[cue: point at layer 2]

Layer two is the model. We trained a deployable checkpoint on all three datasets combined, with 40,000 records from each.
On 23,824 held-out test windows, it scores 94.6 percent accuracy and a macro ROC-AUC of 0.991.
The inference engine loads the checkpoint and the temperature scaler, then returns a class and a confidence for each window.

[cue: point at layer 3]

Layer three is the mitigation engine. It turns each detection into a response.
- Jamming is a radio-layer attack, so a firewall cannot block it. We raise an alert and recommend channel hopping.
- Spoofing, DoS floods and probes get a block rule against the source IP.
The engine supports Windows `netsh`, Linux `iptables` through WSL, and a dry-run mode.
For the demo it runs in dry-run mode: it builds and logs the exact firewall command but doesn't execute it.
Each IP has a cooldown so it isn't blocked twice, and rules expire automatically after five minutes.

[cue: point at layer 4]

Layer four is the dashboard. It's a React and Vite security operations console with six views: Performance, Transfer Matrix, Live Monitor, ROC and AUC, Per-Class metrics, and Mitigation.
The performance views read our saved result files directly, so every chart matches what we report.

[cue: tests slide, optional]

The project has an automated test suite covering capture buffering, feature shapes, the mitigation logic and the dashboard data contracts.
Over to [Speaker 4] for the demo.

---

## Speaker 4: Demo + close (~4 min)

[cue: switch to the dashboard, Performance view]

This is the W-SENTRY console. Performance shows same-dataset accuracy for Random Forest, XGBoost and our hybrid model on all three datasets.

[cue: Transfer Matrix view]

This is the transfer matrix [Speaker 1] described. Rows are training datasets, columns are test datasets.
The diagonal is high. Off the diagonal it collapses. On the right is the behavioral version, where WSN-DS to Edge-IIoTset rises to 80.7 percent.

### Two-laptop setup (do this before the review)

- **Laptop A (detector):** runs the dashboard and is projected for the panel.
- **Laptop B (attacker):** runs the attack script and sits next to the presenter.

1. **Put both laptops on the same network.** A phone hotspot is safest, because college Wi-Fi often blocks traffic between devices.
2. **Start the dashboard on laptop A**, from the `w-sentry` folder:

   ```bash
   npm --prefix frontend run dev
   ```

3. **You don't need laptop A's IP.** `attacker.py` finds laptop A by itself on whatever network both laptops are on (a LAN broadcast first, then the last address that worked, then a scan of the local subnet), so a change of Wi-Fi at the venue doesn't matter. If it can't find it, read the IP from the **Network link** panel on laptop A and pass it as the first argument: `python attacker.py <ip> connect`.

4. **Let laptop B through laptop A's firewall.** When Windows asks whether Node.js may use the network, allow it on **private networks**. If you miss that prompt, run this in an admin PowerShell on laptop A:

   ```bash
   netsh advfirewall firewall add rule name="W-SENTRY demo" dir=in action=allow protocol=TCP localport=5173
   ```

   And this one, so laptop B's discovery broadcast can find laptop A:

   ```bash
   netsh advfirewall firewall add rule name="W-SENTRY discovery" dir=in action=allow protocol=UDP localport=50505
   ```

5. **Copy `scripts/attacker.py` to laptop B.** It needs only Python 3, with no extra packages. Open **two terminals** on laptop B: terminal 1 keeps the `connect` heartbeat running, terminal 2 launches the attacks. Delete the script (and the `.wsentry_target` file next to it) from laptop B after the review.

**30-second rehearsal checklist**

- [ ] The dashboard is open on laptop A, on the **Attack Demo** page, with **Reset** pressed.
- [ ] Laptop B runs `connect` and shows as **ONLINE** in the Network link panel, with its real IP.
- [ ] A short `dos` run from laptop B shows "delivered" lines on B and the attack on A's dashboard.
- [ ] With W-SENTRY **ON**, laptop B's terminal switches to "X BLOCKED by W-SENTRY - target refused (403)".
- [ ] Press **Reset** on laptop A afterwards so the comparison table starts empty.
- [ ] Fallback: if the network fails on the day, the attack buttons on laptop A still work. Use them and skip Step 0.

### Live attack demo (Attack Demo page, ~2 min)

> **For presenters, not read aloud.**
> - **Real:** the network connection between the laptops, laptop B's IP on the dashboard, and the blocking. Once W-SENTRY blocks laptop B, the dashboard server actually refuses its requests.
> - **Real model output:** each attack request carries real attack records of that type from our held-out test set (records the model never saw in training). The verdict and confidence on screen are the trained model's actual output, and if it misses a record, that record shows as reaching the gateway.
> - **Dry run:** the operating-system firewall rule (`netsh`) is generated but not executed.
> - If anyone asks, use Q&A 22–26.

[cue: laptop A on screen, **Attack Demo** page. Press **Reset**. Click **OFF (no IDS)**. Laptop B is ready with a terminal open.]

Now let's watch the system handle a real attack from another machine.
This laptop runs W-SENTRY and protects our gateway.
That laptop is the attacker. It's a separate device on the same network.

**Step 0: establish the connection**

[cue: on laptop B, terminal 1, type:]

```bash
python attacker.py connect
```

[cue: point at the **Network link** panel on laptop A]

The attacker laptop has just connected.
Here's its name and its IP address, which is the address our server actually saw.
It sends a heartbeat every two seconds, so you can see it's online right now.
[point at the connection log] And here's the handshake in the log.

**Step 1: the network without W-SENTRY**

[cue: W-SENTRY is **OFF**. On laptop B, terminal 2, type the command below, then point at laptop A's screen.]

```bash
python attacker.py dos --duration 20
```

First, the network with no intrusion detection.
The attacker launches a DoS flood at us.
[point at laptop B's terminal] Every request is "delivered".
[point at the counters on laptop A] Every attack packet reaches the gateway.
Nothing is inspected and nothing is blocked. The attacker's IP stays active.
That's the before picture.

**Step 2: the same attack with W-SENTRY**

[cue: on laptop A click **W-SENTRY ON**. On laptop B run the same `dos` command again. Keep laptop A on screen, with laptop B's terminal visible next to it.]

Now the same attack, with W-SENTRY switched on.
Every packet now goes through our hybrid CNN-BiLSTM-Attention model.
[point at timeline step 2] The model classifies it as DoS at [read the confidence] percent confidence after [read the number] packet(s).
[point at step 3] The mitigation engine blocks the attacker's IP straight away and adds rate limiting. This is the firewall rule it generated.
[point at laptop B's terminal] And look at the attacker: its requests are now refused. "Blocked by W-SENTRY."
[point at step 4 and the counters] From then on, everything it sends is dropped: [read "Blocked"] blocked. Only [read "Reached the target"] got through before the block.
[point at the IP cards] Before: laptop B's IP is active and flooding the gateway. After: blocked and rate-limited.

**Step 3: an attack you can't firewall**

[cue: on laptop B run `python attacker.py jam`, or click **Jamming** on laptop A]

Not every attack can be stopped with a firewall.
Jamming is radio interference on the sensor network.
The model recognises it [read the confidence], but blocking an IP doesn't stop radio noise.
So the engine raises an alert, and the sensor network moves to a clean channel.
That's why the action here is "alert" and not "block". The response depends on the type of threat.

**Step 4: our hardest case (optional, if time allows)**

[cue: on laptop B run `python attacker.py scan`, or click **Port scan** on laptop A]

Port scans are our hardest class, because they look a lot like light normal traffic.
[if it's caught in 1–2 packets] Here the model caught it after [read the number] packets.
[if it takes longer or some get through] Notice it needs more packets here. That matches our results: probes are our weakest class, at 64 percent recall.

**Step 5: before vs after**

[cue: scroll to the "Before vs after W-SENTRY" table]

This table sums it up. It's the same DoS attack both times.
Without W-SENTRY, 100 percent of the attack reached the gateway.
With W-SENTRY, the attacker was detected within [read the time] and blocked, and only [read the number] packets got through.

[cue: Mitigation view]

Every response is logged here with its timestamp, threat class and exact command.
Blocks expire on their own, and an analyst can block or unblock any IP manually.

[cue: ROC/AUC, then Per-Class view]

ROC curves per class, and per-class precision, recall and confusion matrices.
Intrusion and probe is our weakest class: 64 percent recall on the deployed model. Probes are often mistaken for normal traffic.

[cue: limitations slide]

Limitations. We'd rather state them ourselves.
- Every number comes from a single run, with no variance across seeds.
- The five-record windows come from a shuffled split, so the LSTM sees no real time order.
- DANN saw labels from both datasets, so it is not true unsupervised adaptation.
- The live packet-capture path computes its features differently from training, so we don't use it for detection yet.

[cue: future work slide]

Future work.
- Extract common features directly from raw packet captures, so live traffic matches training.
- Build real time-ordered windows from flows.
- Run multiple seeds, and test DANN on a truly held-out network.
- Validate on a live two-machine lab setup.

[cue: thank-you slide]

Thank you. We're happy to take questions.

---

## Q&A sheet: everyone reads this

1. **Why behavioral features instead of each dataset's own columns?**
   Native columns don't exist across datasets, so a model trained on one has nothing to read in another. Random Forest on native features fell to 11.94% (WSN-DS→Edge-IIoTset) and 1.9% (Edge-IIoTset→WSN-DS). The 20 shared features give every dataset the same input. Source: P1 `transfer_matrix`, `src/data/dataset_loader.py` (`FEATURE_COLS`).

2. **Did the behavioral features fix transfer?**
   Only partly. WSN-DS→Edge-IIoTset rose to 80.7% and Edge-IIoTset→WSN-DS to 26.96%. WSN-DS↔CICIoT2023 stayed at 0.3% and 0.99%, and CICIoT2023→Edge-IIoTset dropped to 15.4% (RF native: 26.3%). Caveat: these compare RF on native features with the hybrid on behavioral features, so two things changed at once. Source: P1 and P2 `behavioral_transfer_matrix`.

3. **What does log normalization do?**
   It computes sign(x)·log(1+|x|), then clips to [−50, 50]. Fields like TCP sequence and ACK numbers reach billions, and that destroys gradient training. It acts on each value separately, so it leaks nothing across the split. The robust scaler is then fit on training data only. Source: `src/features/preprocessor.py`. We have no saved run *without* it, so don't quote a before/after number.

4. **Why CNN + BiLSTM + attention?**
   The CNN finds local patterns across features, the BiLSTM reads a window of records in both directions, and attention weights the most informative positions before classification. Native-feature accuracy: 98.06% / 97.8% / 94.39% (WSN-DS / CICIoT2023 / Edge-IIoTset). Source: `src/models/hybrid_dl.py`, P2 `native_same_dataset`.

5. **Is the hybrid better than Random Forest?**
   Not overall. RF and XGBoost lead on WSN-DS (99.6%) and CICIoT2023 (99.42%). The hybrid leads on Edge-IIoTset (94.39% vs 92.06%). Features and class balancing also differ between those runs, so we don't attribute the gap to the architecture. Source: P1 `same_dataset`, P2.

6. **What is the 5-step sequence the LSTM reads?**
   Honest answer: we cut each partition into windows of 5 rows and label each window by its last row. But the rows are shuffled during the train/test split first, so the 5 rows are unrelated records, not 5 moments of one connection. In effect the model classifies the last record, with four random records as context. The LSTM learns no real temporal pattern. That's a known limitation, and building time-ordered windows from flows is future work. Source: `src/features/preprocessor.py` (`preprocess`, `_make_sequences`).

7. **What does DANN / gradient reversal do?**
   A shared encoder feeds a threat head and a domain head. The gradient reversal layer flips the domain head's gradient on its way back to the encoder, so the encoder learns features that hide which dataset a sample came from. Loss = threat loss + 0.1 × domain loss. Source: `src/models/dann.py`, `run_phase2.py` (`run_dann_2domain`).

8. **So DANN solved cross-dataset transfer?**
   No. Our DANN saw labels from both CICIoT2023 and Edge-IIoTset, so it's a unified model, not a transfer result. It gets 96.5% and 96.29%, which is 1.1–1.3 points below the per-dataset behavioral models (97.79%, 97.42%). We have no control run without gradient reversal, so we can't claim the adversarial term caused anything. Source: P2 `dann_2domain`, `behavioral_transfer_matrix` diagonal.

9. **Did temperature scaling improve calibration?**
   No. ECE got slightly worse on all three datasets: WSN-DS 1.70→1.86, CICIoT2023 0.23→0.43, Edge-IIoTset 1.78→2.04 (%). The model was already well calibrated before scaling. Source: P2 `calibration`.

10. **Is the Live Monitor real?**
    If the backend replay is running, say: "The Live Monitor replays our held-out test set through the trained model, and the firewall runs in dry-run mode." If it's the built-in browser feed, say: "The Live Monitor is a simulation of the SOC workflow. Our detection numbers come from our evaluation, not from this screen." Don't claim live packet capture.

11. **Why don't you show live packet capture?**
    The live capture code computes the 20 features with different formulas from the ones used in training (packet-window sums instead of per-record dataset fields). It also skips the trained scaler. Its predictions wouldn't be meaningful, so we don't present them. Aligning live features with training is future work. Source: `src/live/feature_extractor.py` vs `src/data/dataset_loader.py`.

12. **How good is the deployed model?**
    It was trained on all three datasets combined (40,000 records each). On 23,824 held-out windows: 94.6% accuracy, macro ROC-AUC 0.991, ECE 1.02%. Source: SE.

13. **Which class is weakest, and why?**
    Intrusion/Probe, with 64.34% recall (F1 0.714). Most of its misses go to Normal: 392 of 1,607. Scans and probes look a lot like normal light traffic. Jamming (81.46% recall) and Spoofing (80.81%) come next. Source: SE `per_class`, `confusion_matrix`.

14. **What does the false alarm rate look like?**
    RF FAR is 0.29% on WSN-DS, 0.59% on Edge-IIoTset, and 8.24% on CICIoT2023, which is the highest. Source: P1 `same_dataset.*.far`.

15. **How big are the datasets, and how did you split them?**
    WSN-DS: 374,661 records. CICIoT2023 (Kaggle copy): 1,048,575, which is Excel's row limit, so the copy is truncated. Edge-IIoTset: 2,219,201 records in the DNN file and 157,800 in the ML file. The 70/10/20 train/validation/test split is stratified by class, with seed 42. Source: row counts of `data/raw/*.csv`, `src/features/preprocessor.py`.

16. **Why five classes? Isn't "Jamming" odd?**
    We merged each dataset's labels into one taxonomy so the models could be compared. Jamming holds only WSN-DS TDMA scheduling attacks; the other datasets have none. Spoofing merges different mechanisms (blackhole/grayhole routing, ARP/DNS spoofing). The mapping is our own judgment and hasn't been validated. Source: `src/data/dataset_loader.py`.

17. **What does the mitigation engine actually do?**
    It maps each class to an action: Normal → none, Jamming → alert only, Spoofing/DoS/Probe → block the source IP. It has a 30-second per-IP cooldown and expires rules after 300 seconds. In the demo it runs dry-run and only logs the `netsh` command. It can execute rules on Windows (`netsh`) or WSL (`iptables`). Source: `src/live/mitigation.py`.

18. **What is new here? Isn't cross-dataset collapse already known?**
    Yes, it's known. Layeghy & Portmann (arXiv 2205.04112) and Sarhan et al. report it. Our contribution is: measuring it across three very different network types, including a wireless sensor network; a shared 20-feature behavioral schema; a hybrid + DANN study; and a working SOC system with detection, mitigation and a dashboard. Source: `paper/w-sentry-paper-ieee.tex` Related Work.

19. **Can these results be reproduced?**
    The scripts are in the repo (`run_phase1.py`, `run_phase2.py`, `scripts/train_model.py`) with seed 42. Honest caveat: the saved Phase 1/2 results came from earlier script versions, and each number is a single run without variance. Source: paper Limitations section.

20. **What would you do with more time?**
    Extract features from raw captures so live traffic matches training. Build real time-ordered windows. Run multiple seeds. Add a DANN control and a truly held-out target network. Run a two-machine live lab test (`docs/DEMO_RUNBOOK.md`).

21. **How fast is it?**
    Fast enough for real time. Measured on the live detector over the network: median detection latency ~29 ms per artifact (95th percentile ~35 ms), and ~425 classifications per second in batches. RF inference on the full WSN-DS test set took 0.94 s. Source: live measurement against `detector_server.py`; P1 `RF_WSN-DS.inference_time_s`.

### Attack Demo questions

22. **Are those real attacks you're launching?**
    The traffic really comes from laptop B over the network, and the IP on the dashboard is laptop B's real address. What each attack request carries is real attack records of that type from our held-out test set, which the model never saw in training. The verdict and confidence on screen are the trained model's actual output; if it misses a record, that record shows as reaching the gateway. When W-SENTRY blocks laptop B, the dashboard server actually refuses its requests. We don't run live attack tools such as hping3 or nmap in the hall; that full lab setup is in `docs/DEMO_RUNBOOK.md`. The local attack buttons are a fallback, and with those the attacker IPs are display labels. Source: `scripts/attacker.py`, `scripts/export_replay.py`, `frontend/public/replay.json`.

23. **Why is the attack caught on the first packet?**
    Each "packet" is a full dataset record with its traffic features, not one raw packet, so the model has enough to decide. DoS is the class it's most sure of: 97.03% recall on the held-out set. Probes are harder (64.34% recall), so a port scan can take several packets. Source: SE `per_class`.

24. **Would it really block the IP?**
    On this laptop it runs in dry-run mode: it generates the `netsh` command but doesn't execute it. The engine supports real execution on Windows (`netsh advfirewall`) and on Linux/WSL (`iptables`). Source: `src/live/mitigation.py`.

25. **What does "OFF" represent?**
    The same network with no intrusion detection: traffic isn't inspected and nothing is blocked. It's the baseline we compare against.

26. **How do we know the other laptop is really connected?**
    Its handshake and its heartbeats (one every two seconds) arrive at this laptop over the local network. The IP shown is the source address our server saw on those requests, not a value typed into the dashboard. Stop the script or take laptop B off the network and it shows as offline within a few seconds. Source: `scripts/attacker.py`, `frontend/vite.config.js`.
