#!/usr/bin/env python3
"""Subscription generator: Clash YAML, v2rayN socks URIs, generic Base64."""
from __future__ import annotations
import base64
import hashlib
import json
import time
import urllib.parse


def _sanitize_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in " -_()[]").strip() or "node"


def build_proxy_list(entries: list) -> list:
    """entries: [{port, label, country}] -> [proxy dict]"""
    proxies = []
    for e in entries:
        proxies.append({
            "name": _sanitize_name(e["label"]),
            "type": "socks5",
            "server": e["server"],
            "port": int(e["port"]),
            "username": e.get("username", ""),
            "password": e.get("password", ""),
            "udp": True,
        })
    return proxies


def clash_yaml(entries: list, extra_rules: str = "") -> str:
    proxies = build_proxy_list(entries)
    group_names = ["proxy"]
    lines = []
    lines.append("# VPN-Subscription-Gateway Clash Config")
    lines.append("mixed-port: 7890")
    lines.append("allow-lan: false")
    lines.append("mode: rule")
    lines.append("log-level: info")
    lines.append("")
    lines.append("proxies:")
    for p in proxies:
        lines.append("  - name: " + p["name"])
        lines.append("    type: socks5")
        lines.append("    server: " + p["server"])
        lines.append("    port: " + str(p["port"]))
        if p["username"]:
            lines.append("    username: " + p["username"])
        if p["password"]:
            lines.append("    password: " + p["password"])
        lines.append("    udp: true")
    lines.append("")
    lines.append("proxy-groups:")
    lines.append("  - name: proxy")
    lines.append("    type: url-test")
    lines.append("    url: http://www.gstatic.com/generate_204")
    lines.append("    interval: 300")
    lines.append("    proxies:")
    for p in proxies:
        lines.append("      - " + p["name"])
    lines.append("  - name: select")
    lines.append("    type: select")
    lines.append("    proxies:")
    lines.append("      - proxy")
    for p in proxies:
        lines.append("      - " + p["name"])
    lines.append("")
    lines.append("rules:")
    lines.append("  - GEOIP,CN,DIRECT")
    lines.append("  - MATCH,proxy")
    return "\n".join(lines)


def v2ray_socks_uris(entries: list) -> str:
    """v2rayN / NekoBox compatible socks:// URIs, one per line."""
    lines = []
    for e in entries:
        server = e["server"]
        port = int(e["port"])
        user = urllib.parse.quote(e.get("username", ""))
        pw = urllib.parse.quote(e.get("password", ""))
        label = urllib.parse.quote(_sanitize_name(e["label"]))
        if user and pw:
            uri = "socks://" + user + ":" + pw + "@" + server + ":" + str(port) + "#" + label
        else:
            uri = "socks://" + server + ":" + str(port) + "#" + label
        lines.append(uri)
    return "\n".join(lines)


def base64_subscription(entries: list) -> str:
    """Generic Base64-encoded subscription (URI list)."""
    plain = v2ray_socks_uris(entries)
    return base64.b64encode(plain.encode("utf-8")).decode("ascii")


def generate_all(entries: list) -> dict:
    return {
        "clash": clash_yaml(entries),
        "v2ray": v2ray_socks_uris(entries),
        "base64": base64_subscription(entries),
    }


def build_entries(server_host: str, tunnels: list, proxy_user: str, proxy_pass: str) -> list:
    """从隧道状态构建订阅条目(仅 alive 隧道)。"""
    entries = []
    for t in tunnels:
        if not t.get("alive"):
            continue
        entries.append({
            "server": server_host,
            "port": t["port"],
            "label": t["label"],
            "username": proxy_user,
            "password": proxy_pass,
        })
    return entries


def token_ok(token: str, expected: str) -> bool:
    if not expected or expected == "auto":
        return True
    return hashlib.sha256(token.encode()).hexdigest() == hashlib.sha256(expected.encode()).hexdigest()
