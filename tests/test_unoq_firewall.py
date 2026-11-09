"""Firewall + block bookkeeping for the UNO Q detector. Runs anywhere: iptables is faked."""
import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("detector_server", ROOT / "scripts" / "detector_server.py")
ds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ds)


class FakeRun:
    """Records iptables calls (without the leading 'iptables -w'). '-C' answers 'rule absent'."""
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, **kw):
        args = cmd[2:]
        self.calls.append(" ".join(args))
        return subprocess.CompletedProcess(cmd, 1 if args[0] == "-C" else 0, "", "")


def make_fw():
    run = FakeRun()
    fw = ds.Firewall("iptables", port=8000, run=run, which=lambda _: "/usr/sbin/iptables")
    return fw, run


def test_setup_creates_chain_and_jump():
    _, run = make_fw()
    assert run.calls == ["-N WSENTRY", "-F WSENTRY", "-C INPUT -j WSENTRY", "-I INPUT 1 -j WSENTRY"]


def test_block_keeps_api_port_open_and_drops_the_rest():
    fw, run = make_fw()
    run.calls.clear()
    fw.block("192.168.1.50")
    assert run.calls == [
        "-A WSENTRY -s 192.168.1.50 -p tcp --dport 8000 -j RETURN",
        "-A WSENTRY -s 192.168.1.50 -j DROP",
    ]


def test_unblock_deletes_both_rules_and_teardown_removes_chain():
    fw, run = make_fw()
    run.calls.clear()
    fw.unblock("192.168.1.50")
    fw.teardown()
    assert run.calls == [
        "-D WSENTRY -s 192.168.1.50 -p tcp --dport 8000 -j RETURN",
        "-D WSENTRY -s 192.168.1.50 -j DROP",
        "-F WSENTRY", "-D INPUT -j WSENTRY", "-X WSENTRY",
    ]


def test_dryrun_never_runs_iptables():
    run = FakeRun()
    fw = ds.Firewall("dryrun", run=run)
    fw.block("1.2.3.4"); fw.unblock("1.2.3.4"); fw.clear(); fw.teardown()
    assert run.calls == []
    assert fw.describe("1.2.3.4", 7).startswith("[dry run] netsh")


class RecFw:
    mode = "iptables"
    def __init__(self):
        self.log = []
    def block(self, ip): self.log.append("block " + ip)
    def unblock(self, ip): self.log.append("unblock " + ip)
    def clear(self): self.log.append("clear")
    def describe(self, ip, rid): return f"rule {rid} {ip}"


def test_detector_adds_rule_once_and_expires_it():
    fw = RecFw()
    det = ds.Detector(fw=fw, engine=object())       # engine unused here: no model load
    assert det.block("10.0.0.5") and det.block("10.0.0.5")
    assert fw.log == ["block 10.0.0.5"]             # second block only extends the expiry
    det.blocks["10.0.0.5"] = 0                       # force expiry
    assert det.expire() == ["10.0.0.5"]
    assert fw.log == ["block 10.0.0.5", "unblock 10.0.0.5"] and not det.blocks


def test_detector_rejects_bad_or_self_addresses_when_enforcing():
    det = ds.Detector(fw=RecFw(), engine=object())
    for bad in ["", "0.0.0.0/0", "not-an-ip", "127.0.0.1", "0.0.0.0"]:
        assert det.block(bad) is False
    assert det.blocks == {}


def test_unblock_all_clears_chain():
    fw = RecFw()
    det = ds.Detector(fw=fw, engine=object())
    det.block("10.0.0.5"); det.block("10.0.0.6")
    det.unblock()
    assert det.blocks == {} and fw.log[-1] == "clear"


def test_manual_block_only_firewalls_connected_devices_when_enforcing():
    # The dashboard's idle simulation POSTs /api/block for made-up IPs (mockFeed.js:394).
    # A real kernel rule must only ever hit a device that actually connected (laptop B).
    det = ds.Detector(fw=RecFw(), engine=object())
    det.devices["192.168.1.77"] = {"ip": "192.168.1.77"}
    assert det.manual_block("192.168.1.50") is False
    assert det.manual_block("192.168.1.77") is True
    assert list(det.blocks) == ["192.168.1.77"]
    dry = ds.Detector(fw=ds.Firewall("dryrun"), engine=object())
    assert dry.manual_block("192.168.1.50") is True     # dry run: today's behaviour
