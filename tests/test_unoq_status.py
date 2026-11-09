"""Board status helpers: kernel counter parsers, lights frame, protection toggle, identity."""
import importlib.util
import platform
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("detector_server", ROOT / "scripts" / "detector_server.py")
ds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ds)

NET_DEV = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo:    1200      12    0    0    0     0          0         0     1200      12    0    0    0     0       0          0
 wlan0: 9876543   54321    0    0    0     0          0        10   123456     789    0    0    0     0       0          0
"""
SNMP = """Ip: Forwarding DefaultTTL InReceives InHdrErrors InAddrErrors ForwDatagrams InUnknownProtos InDiscards InDelivers OutRequests
Ip: 2 64 5000 0 0 0 0 0 4900 3000
Icmp: InMsgs InErrors
Icmp: 3 0
"""
IPT = """Chain WSENTRY (1 references)
    pkts      bytes target     prot opt in     out     source               destination
      14      840 RETURN     6    --  *      *       192.168.1.50         0.0.0.0/0            tcp dpt:8000
    2500  1300000 DROP       0    --  *      *       192.168.1.50         0.0.0.0/0
       7      420 DROP       0    --  *      *       192.168.1.51         0.0.0.0/0
"""


def test_kernel_counter_parsers():
    assert ds.parse_net_dev(NET_DEV, "wlan0") == 54321
    assert ds.parse_net_dev(NET_DEV, "eth9") == 0
    assert ds.parse_in_delivers(SNMP) == 4900
    assert ds.parse_drops(IPT) == 2507


def new_det():
    return ds.Detector(fw=ds.Firewall("dryrun"), engine=object())


def test_lights_frame():
    det = new_det()
    det.traffic = {"rx_pps": 0}
    assert det.lights_frame() == [0, 0, 0]                 # safe, no attack, empty graph
    det.traffic = {"rx_pps": 1000}
    assert det.lights_frame()[2] == 8                      # 1000 packets/s fills the graph
    det.traffic = {"rx_pps": 10}
    assert det.lights_frame()[2] == 2
    det.last = {"label": "DoS_Flood", "ts": time.time()}
    assert det.lights_frame()[:2] == [1, 3]                # alert, DDoS
    det.block("10.0.0.9")
    assert det.lights_frame()[0] == 2                      # blocked
    det.set_protection(False)
    assert det.lights_frame()[0] == 3 and det.blocks == {} # off, and every block released


def test_device_info_fields():
    info = ds.device_info()
    assert {"board", "soc", "cpu", "arch", "os", "host", "model_sha"} <= set(info)
    assert info["arch"] == platform.machine() and len(info["model_sha"]) == 16
