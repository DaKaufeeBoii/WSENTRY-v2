# W-SENTRY attacker (laptop B)

Everything the second laptop needs for the demo. Only **Python 3** is required.

## Use it (easiest)

1. Make sure laptop A is running the dashboard **and** the detector, on the same
   Wi-Fi / hotspot as this laptop (see the main repo's `docs/DEMO_NETWORK.md`).
2. **Double-click `run.cmd`** (or run `python menu.py`).
3. It finds laptop A automatically and shows a menu. Pick an attack by number:

   ```
   1. DoS flood
   2. SYN flood
   3. UDP flood
   4. Port scan
   5. OS fingerprinting
   6. Spoofing / MITM
   7. Jamming (RF)
   8. Multi-stage combo
   9. Before vs after W-SENTRY
   0. Quit
   ```

While the menu is open, this laptop shows as **ONLINE** on the dashboard.

If auto-discovery fails, run `python menu.py <laptop-A-ip>` (the IP is shown in
the dashboard's **Network link** panel).

## Or type commands directly

```
python attacker.py connect        keep the link alive (ONLINE)
python attacker.py dos             launch a DoS attack
python attacker.py dos --before-after   run it with W-SENTRY OFF, then ON
python attacker.py combo           multi-stage attack
```
Attack names: `dos synflood udpflood httpflood scan osfingerprint vulnscan spoof mitm jam`.

## Files

- `run.cmd` - double-click launcher (Windows)
- `menu.py` - the text menu
- `attacker.py` - the client (discovery, handshake, attacks)
- `attack_samples.json` - real held-out dataset records the model classifies

## After the review

Delete this folder from laptop B (it also writes a `.wsentry_target` file here).

## Note

No real attack is performed. The script sends real dataset records to laptop A
over HTTP; the trained model there classifies them live and decides whether to
block this machine. The IP addresses are real; the firewall action is dry-run.
