#!/usr/bin/env python3
"""Node fetch and speed test from VPNGate API"""
from __future__ import annotations
import base64
import csv
import json
import socket
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import config


def fetch_vpngate_raw(timeout: int = 15) -> str:
    req = urllib.request.Request(
        config.VPNGATE_API,
        headers={"User-Agent": "Mozilla/5.0 (compatible; vpn-subscription-gateway/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_vpngate(text: str) -> list:
    lines2 = [ln for ln in text.splitlines() if ln and not ln.startswith("*")]
    if not lines2:
        return []
    reader = csv.reader(lines2)
    header = next(reader, None)
    if not header or not header[0].startswith("#HostName"):
        reader = csv.reader(lines2)
    nodes = []
    for row in reader:
        if not row or len(row) < 15:
            continue
        hostname = row[0].lstrip("#").strip()
        node = {
            "hostname": hostname,
            "ip": row[1].strip(),
            "score": row[2].strip(),
            "ping": row[3].strip(),
            "speed": row[4].strip(),
            "country_long": row[5].strip(),
            "country_short": row[6].strip().upper(),
            "sessions": row[7].strip(),
            "uptime": row[8].strip(),
            "users": row[9].strip(),
            "traffic": row[10].strip(),
            "log_type": row[11].strip(),
            "operator": row[12].strip()[:80],
            "message": row[13].strip()[:120],
            "config_b64": row[14].strip(),
        }
        try:
            node["openvpn_config"] = base64.b64decode(node["config_b64"]).decode("utf-8", errors="replace")
        except Exception:
            node["openvpn_config"] = ""
        node["id"] = node["ip"] + ":" + hostname
        nodes.append(node)
    return nodes


def tcp_probe(ip: str, port: int, timeout: float = 3.0):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        t0 = time.monotonic()
        sock.connect((ip, port))
        rtt = time.monotonic() - t0
        sock.close()
        return rtt
    except Exception:
        return None


def test_node(node: dict) -> dict:
    result = dict(node)
    result["latency_ms"] = None
    result["reachable"] = False
    ip = node.get("ip", "")
    if not ip:
        return result
    rtt = tcp_probe(ip, 443, timeout=3)
    if rtt is None:
        rtt = tcp_probe(ip, 1194, timeout=3)
    if rtt is None:
        rtt = tcp_probe(ip, 80, timeout=3)
    if rtt is not None:
        result["latency_ms"] = round(rtt * 1000, 1)
        result["reachable"] = True
    return result


def test_many(nodes: list, max_workers: int = 12) -> list:
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(test_node, nodes))
    results.sort(key=lambda n: (not n["reachable"], n["latency_ms"] if n["latency_ms"] is not None else 10**9))
    return results


def refresh_nodes(force: bool = False) -> list:
    cache = None
    if not force and config.NODES_CACHE.exists():
        try:
            cache = json.loads(config.NODES_CACHE.read_text(encoding="utf-8"))
            if time.time() - cache.get("ts", 0) < config.FETCH_INTERVAL:
                return cache.get("nodes", [])
        except Exception:
            pass
    try:
        raw = fetch_vpngate_raw()
        nodes = parse_vpngate(raw)
        nodes = test_many(nodes)
        config.NODES_CACHE.write_text(
            json.dumps({"ts": time.time(), "nodes": nodes}, ensure_ascii=False),
            encoding="utf-8",
        )
        return nodes
    except Exception as e:
        print("[nodes] refresh failed: " + str(e), flush=True)
        if cache:
            return cache.get("nodes", [])
        return []


def get_countries(nodes: list) -> list:
    agg = {}
    for n in nodes:
        cc = n.get("country_short", "??")
        agg[cc] = agg.get(cc, 0) + 1
    return [{"code": k, "count": v} for k, v in sorted(agg.items())]


def public_ip(timeout: int = 10) -> str:
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ip = resp.read().decode().strip()
                if ip:
                    return ip
        except Exception:
            continue
    return ""

if __name__ == "__main__":
    nodes = refresh_nodes(force=True)
    print("total nodes: " + str(len(nodes)))
    reach = sum(1 for n in nodes if n.get("reachable"))
    print("reachable: " + str(reach))
    for n in nodes[:10]:
        print(n["country_short"], n["ip"], n.get("latency_ms"), "ms" if n.get("latency_ms") else "-")
