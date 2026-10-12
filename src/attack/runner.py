"""
Unified Attack Runner CLI for W-SENTRY live evaluations.
"""
import argparse
import sys
import time

from src.attack.flood import syn_flood, udp_flood, icmp_flood
from src.attack.scan import port_scan, os_fingerprint, ping_sweep
from src.attack.arp_spoof import arp_spoof


def main() -> None:
    parser = argparse.ArgumentParser(description="W-SENTRY Live Attack Orchestrator")
    subparsers = parser.add_subparsers(dest="attack", required=True)

    # syn-flood
    p_syn = subparsers.add_parser("syn-flood", help="TCP SYN Flood")
    p_syn.add_argument("--target", required=True, help="Target victim IP")
    p_syn.add_argument("--port", type=int, default=80, help="Target port")
    p_syn.add_argument("--duration", type=int, default=30, help="Attack duration in seconds")
    p_syn.add_argument("--rate", type=int, default=100, help="Approx packets/sec")

    # udp-flood
    p_udp = subparsers.add_parser("udp-flood", help="UDP Flood")
    p_udp.add_argument("--target", required=True, help="Target victim IP")
    p_udp.add_argument("--port", type=int, default=53, help="Target port")
    p_udp.add_argument("--duration", type=int, default=30, help="Attack duration in seconds")
    p_udp.add_argument("--packet-size", type=int, default=512, help="Payload size")

    # icmp-flood
    p_icmp = subparsers.add_parser("icmp-flood", help="ICMP Ping Flood")
    p_icmp.add_argument("--target", required=True, help="Target victim IP")
    p_icmp.add_argument("--duration", type=int, default=30, help="Attack duration in seconds")
    p_icmp.add_argument("--packet-size", type=int, default=1024, help="Payload size")

    # port-scan
    p_scan = subparsers.add_parser("port-scan", help="Nmap SYN Port Scan")
    p_scan.add_argument("--target", required=True, help="Target victim IP")
    p_scan.add_argument("--ports", default="1-1024", help="Port range")

    # os-scan
    p_os = subparsers.add_parser("os-scan", help="Nmap OS Fingerprinting")
    p_os.add_argument("--target", required=True, help="Target victim IP")

    # ping-sweep
    p_ping = subparsers.add_parser("ping-sweep", help="Subnet Ping Sweep")
    p_ping.add_argument("--subnet", default="192.168.1.0/24", help="Target subnet CIDR")

    # arp-spoof
    p_arp = subparsers.add_parser("arp-spoof", help="ARP Cache Poisoning / MITM")
    p_arp.add_argument("--target", required=True, help="Target victim IP")
    p_arp.add_argument("--gateway", required=True, help="Gateway router IP")
    p_arp.add_argument("--iface", default="eth0", help="Network interface")
    p_arp.add_argument("--duration", type=int, default=60, help="Attack duration in seconds")

    args = parser.parse_args()

    proc = None
    if args.attack == "syn-flood":
        proc = syn_flood(args.target, target_port=args.port, duration=args.duration, rate=args.rate)
    elif args.attack == "udp-flood":
        proc = udp_flood(args.target, target_port=args.port, duration=args.duration, packet_size=args.packet_size)
    elif args.attack == "icmp-flood":
        proc = icmp_flood(args.target, duration=args.duration, packet_size=args.packet_size)
    elif args.attack == "port-scan":
        proc = port_scan(args.target, port_range=args.ports)
    elif args.attack == "os-scan":
        proc = os_fingerprint(args.target)
    elif args.attack == "ping-sweep":
        proc = ping_sweep(subnet=args.subnet)
    elif args.attack == "arp-spoof":
        proc = arp_spoof(args.target, gateway_ip=args.gateway, iface=args.iface, duration=args.duration)

    if proc:
        try:
            print("[ATTACK] Running attack process. Press Ctrl+C to terminate early.")
            proc.wait()
        except KeyboardInterrupt:
            print("\n[ATTACK] Interrupted by user.")
            proc.terminate()


if __name__ == "__main__":
    main()
