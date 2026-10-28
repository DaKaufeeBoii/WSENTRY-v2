"""
CLI runner for launching simulated attacks against the detector laptop.
"""
import sys
import time
import argparse
from src.attack.flood import syn_flood, udp_flood, icmp_flood, stop_flood
from src.attack.scan import port_scan, os_fingerprint, ping_sweep
from src.attack.arp_spoof import arp_spoof


def main():
    parser = argparse.ArgumentParser(
        description="W-SENTRY Attack Simulation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="attack_type", help="Attack command to run")

    # SYN Flood
    syn_p = subparsers.add_parser("syn-flood", help="TCP SYN flood attack")
    syn_p.add_argument("--target", required=True, help="Target victim IP")
    syn_p.add_argument("--port", type=int, default=80, help="Target TCP port")
    syn_p.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    syn_p.add_argument("--rate", type=int, default=100, help="Packet rate per sec")

    # UDP Flood
    udp_p = subparsers.add_parser("udp-flood", help="UDP flood attack")
    udp_p.add_argument("--target", required=True, help="Target victim IP")
    udp_p.add_argument("--port", type=int, default=53, help="Target UDP port")
    udp_p.add_argument("--duration", type=int, default=30, help="Duration in seconds")

    # ICMP Flood
    icmp_p = subparsers.add_parser("icmp-flood", help="ICMP flood attack")
    icmp_p.add_argument("--target", required=True, help="Target victim IP")
    icmp_p.add_argument("--duration", type=int, default=30, help="Duration in seconds")

    # Port Scan
    pscan_p = subparsers.add_parser("port-scan", help="Nmap SYN stealth port scan")
    pscan_p.add_argument("--target", required=True, help="Target victim IP")
    pscan_p.add_argument("--ports", default="1-1024", help="Port range (e.g. 1-1024)")

    # OS Scan
    oscan_p = subparsers.add_parser("os-scan", help="Nmap OS and version scan")
    oscan_p.add_argument("--target", required=True, help="Target victim IP")

    # Ping Sweep
    ping_p = subparsers.add_parser("ping-sweep", help="Subnet discovery ping sweep")
    ping_p.add_argument("--subnet", default="192.168.1.0/24", help="CIDR subnet")

    # ARP Spoof
    arp_p = subparsers.add_parser("arp-spoof", help="ARP cache poisoning MITM attack")
    arp_p.add_argument("--target", required=True, help="Target victim IP")
    arp_p.add_argument("--gateway", required=True, help="LAN Gateway / Router IP")
    arp_p.add_argument("--duration", type=int, default=60, help="Duration in seconds")

    args = parser.parse_args()

    if not args.attack_type:
        parser.print_help()
        sys.exit(1)

    print(f"\n[W-SENTRY Attack Suite] Initiating {args.attack_type.upper()}...")
    proc = None

    try:
        if args.attack_type == "syn-flood":
            proc = syn_flood(args.target, target_port=args.port, duration=args.duration, rate=args.rate)
            print(f"[*] SYN Flood launched at {args.target}:{args.port} for {args.duration}s. Press Ctrl+C to abort.")
            time.sleep(args.duration)

        elif args.attack_type == "udp-flood":
            proc = udp_flood(args.target, target_port=args.port, duration=args.duration)
            print(f"[*] UDP Flood launched at {args.target}:{args.port} for {args.duration}s.")
            time.sleep(args.duration)

        elif args.attack_type == "icmp-flood":
            proc = icmp_flood(args.target, duration=args.duration)
            print(f"[*] ICMP Flood launched at {args.target} for {args.duration}s.")
            time.sleep(args.duration)

        elif args.attack_type == "port-scan":
            proc = port_scan(args.target, port_range=args.ports)
            print(f"[*] Nmap port scan running against {args.target}...")
            stdout, stderr = proc.communicate()
            if stdout:
                print(stdout.decode(errors="ignore"))

        elif args.attack_type == "os-scan":
            proc = os_fingerprint(args.target)
            print(f"[*] OS fingerprinting scan running against {args.target}...")
            stdout, stderr = proc.communicate()
            if stdout:
                print(stdout.decode(errors="ignore"))

        elif args.attack_type == "ping-sweep":
            proc = ping_sweep(subnet=args.subnet)
            print(f"[*] Ping sweep running across {args.subnet}...")
            stdout, stderr = proc.communicate()
            if stdout:
                print(stdout.decode(errors="ignore"))

        elif args.attack_type == "arp-spoof":
            proc = arp_spoof(args.target, gateway_ip=args.gateway, duration=args.duration)
            print(f"[*] ARP Spoof active against {args.target} and gateway {args.gateway} for {args.duration}s.")
            time.sleep(args.duration)

    except KeyboardInterrupt:
        print("\n[!] Attack interrupted by user.")
    finally:
        if proc:
            stop_flood(proc)
        print("[*] Attack process completed/stopped.\n")


if __name__ == "__main__":
    main()

