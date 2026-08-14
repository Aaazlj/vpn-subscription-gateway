#!/usr/bin/env python3
"""Multi-tunnel OpenVPN manager. One tunnel per selected node, each with own tun device and routing table."""
from __future__ import annotations
import os
import re
import shlex
import signal
import subprocess
import threading
import time
from pathlib import Path

from . import config


def _run(cmd: list, timeout: int = 10) -> tuple:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return -1, "", str(e)


def _sh(cmd: str, timeout: int = 10) -> tuple:
    rc, out, err = _run(["/bin/sh", "-c", cmd], timeout)
    return rc, (out + "\n" + err).strip()


def _check_iproute() -> bool:
    rc, _ = _sh("command -v ip")
    return rc == 0


def _check_openvpn() -> bool:
    rc, _ = _sh("command -v openvpn")
    return rc == 0


def write_openvpn_config(node: dict, index: int) -> Path:
    """Generate OpenVPN config from node, force dev tunN, return config path."""
    cfg_dir = config.DATA_DIR / "configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    raw = node.get("openvpn_config", "")
    cleaned = []
    drop_prefixes = (
        "dev ", "dev-", "route ", "redirect-gateway", "ifconfig",
        "up ", "down ", "script-security", "auth-user-pass", "auth-nocache",
        "persist-tun", "keepalive", "ping ", "ping-restart", "ping-exit",
        "verb ", "mute ", "log ", "status ", "writepid", "daemon",
        "setenv", "user ", "group ",
    )
    for ln in raw.splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith(";"):
            cleaned.append(ln)
            continue
        low = s.lower()
        if low.startswith(drop_prefixes):
            continue
        cleaned.append(ln)
    dev = config.TUN_PREFIX + str(index)
    # VPNGate 公共认证账号
    auth_file = cfg_dir / ("auth_" + str(index) + ".txt")
    auth_file.write_text("vpn\nvpn\n", encoding="utf-8")
    lines = [
        "client",
        "dev " + dev,
        "dev-type tun",
        "persist-tun",
        "auth-nocache",
        "auth-user-pass " + str(auth_file),
        "script-security 2",
        "route-nopull",
        "verb 3",
    ]
    lines.extend(cleaned)
    path = cfg_dir / ("node_" + str(index) + ".ovpn")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def setup_policy_routing(tun: str, table: int) -> tuple:
    if not _check_iproute():
        return False, "iproute2 not installed"
    _sh("ip route flush table " + str(table))
    rc, out = _sh("ip route add default dev " + tun + " table " + str(table))
    if rc != 0:
        return False, out
    _sh("ip rule add from all lookup " + str(table) + " pref " + str(table))
    return True, ""


def cleanup_policy_routing(tun: str, table: int) -> None:
    _sh("ip rule del pref " + str(table) + " 2>/dev/null")
    _sh("ip route flush table " + str(table) + " 2>/dev/null")


class Tunnel:
    """Single OpenVPN tunnel."""

    def __init__(self, index: int, node: dict):
        self.index = index
        self.node = node
        self.tun = config.TUN_PREFIX + str(index)
        self.table = config.ROUTE_TABLE_BASE + index
        self.port = config.PROXY_PORT_BASE + index
        self.proc = None
        self.alive = False
        self.last_error = ""
        self.started_at = 0.0
        self.exit_ip = ""
        self.lock = threading.Lock()

    @property
    def country(self) -> str:
        return self.node.get("country_short", "??")

    @property
    def label(self) -> str:
        return (self.country + " " + str(self.index + 1) + " " + self.node.get("hostname", "")).strip()

    def _wait_ready(self, timeout: int = 45) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc is None or self.proc.poll() is not None:
                self.last_error = "openvpn process exited"
                return False
            rc, _ = _sh("ip link show " + self.tun + " 2>/dev/null | grep -q " + self.tun)
            if rc == 0:
                self.alive = True
                return True
            time.sleep(1)
        self.last_error = "tun device not ready in " + str(timeout) + "s"
        return False

    def connect(self) -> bool:
        with self.lock:
            self.disconnect(cleanup=True)
            if not _check_openvpn():
                self.last_error = "openvpn binary not found"
                return False
            cfg = write_openvpn_config(self.node, self.index)
            cmd = ["openvpn", "--config", str(cfg)]
            try:
                self.proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, errors="replace", bufsize=1,
                )
            except Exception as e:
                self.last_error = "failed to start openvpn: " + str(e)
                return False
            self.started_at = time.time()
            if not self._wait_ready():
                self.disconnect(cleanup=True)
                return False
            ok, msg = setup_policy_routing(self.tun, self.table)
            if not ok:
                self.last_error = "policy routing failed: " + msg
                self.disconnect(cleanup=True)
                return False
            print("[tunnel] " + self.label + " up on " + self.tun + " table " + str(self.table) + " port " + str(self.port), flush=True)
            return True

    def check_health(self) -> bool:
        if self.proc is None or self.proc.poll() is not None:
            self.alive = False
            self.last_error = "process dead"
            return False
        rc, _ = _sh("ip link show " + self.tun + " 2>/dev/null | grep -q " + self.tun)
        self.alive = (rc == 0)
        if not self.alive:
            self.last_error = "tun missing"
        return self.alive

    def disconnect(self, cleanup: bool = True) -> None:
        if cleanup:
            cleanup_policy_routing(self.tun, self.table)
        if self.proc is not None:
            try:
                self.proc.send_signal(signal.SIGTERM)
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
        self.alive = False

    def status_dict(self) -> dict:
        return {
            "index": self.index,
            "node_id": self.node.get("id", ""),
            "label": self.label,
            "country": self.country,
            "tun": self.tun,
            "table": self.table,
            "port": self.port,
            "alive": self.alive,
            "exit_ip": self.exit_ip,
            "last_error": self.last_error,
            "started_at": self.started_at,
            "latency_ms": self.node.get("latency_ms"),
        }


class TunnelManager:
    """Manage a set of tunnels (one per selected node)."""

    def __init__(self):
        self.tunnels = [None] * config.MAX_TUNNELS
        self.lock = threading.Lock()
        self.running = False
        self._thread = None

    def apply_nodes(self, nodes: list, selected_ids: list) -> dict:
        with self.lock:
            alive_ids = set(selected_ids)
            for t in self.tunnels:
                if t is not None and t.node.get("id") not in alive_ids:
                    t.disconnect(cleanup=True)
            by_id = {n.get("id"): n for n in nodes}
            new_tunnels = []
            for i, nid in enumerate(selected_ids[:config.MAX_TUNNELS]):
                node = by_id.get(nid)
                if node is None:
                    new_tunnels.append(None)
                    continue
                existing = None
                for t in self.tunnels:
                    if t is not None and t.node.get("id") == nid:
                        existing = t
                        break
                if existing is not None:
                    existing.index = i
                    existing.tun = config.TUN_PREFIX + str(i)
                    existing.table = config.ROUTE_TABLE_BASE + i
                    existing.port = config.PROXY_PORT_BASE + i
                    new_tunnels.append(existing)
                else:
                    t = Tunnel(i, node)
                    ok = t.connect()
                    new_tunnels.append(t if ok else None)
            for t in self.tunnels:
                if t is not None and t not in new_tunnels:
                    t.disconnect(cleanup=True)
            self.tunnels = new_tunnels
            return self.summary()

    def summary(self) -> dict:
        alive = [t for t in self.tunnels if t is not None and t.alive]
        return {
            "total": len(self.tunnels),
            "alive": len(alive),
            "tunnels": [t.status_dict() for t in self.tunnels if t is not None],
        }

    def start_health_checker(self):
        if self.running:
            return
        self.running = True

        def loop():
            while self.running:
                time.sleep(config.CHECK_INTERVAL)
                with self.lock:
                    for t in self.tunnels:
                        if t is None:
                            continue
                        if not t.check_health():
                            print("[tunnel] " + t.label + " unhealthy, reconnecting...", flush=True)
                            t.connect()

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop_all(self):
        self.running = False
        with self.lock:
            for t in self.tunnels:
                if t is not None:
                    t.disconnect(cleanup=True)
            self.tunnels = [None] * config.MAX_TUNNELS


def system_check() -> dict:
    import shutil
    return {
        "openvpn": shutil.which("openvpn") is not None,
        "iproute2": shutil.which("ip") is not None,
        "tun_device": os.path.exists("/dev/net/tun"),
        "root": os.geteuid() == 0 if hasattr(os, "geteuid") else None,
    }
