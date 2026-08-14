#!/usr/bin/env python3
"""VPN Subscription Gateway - entry point."""
from __future__ import annotations
import json
import os
import threading
import time

from . import config, node_fetch, tunnel_manager, proxy as proxy_mod
from .webui import DualStackServer, Handler, public_ip
from .html_page import render_index

try:
    from . import subscriber
except Exception:
    subscriber = None


class App:
    def __init__(self):
        cfg = config.load_config()
        self.proxy_user = cfg.get("proxy_user", "user")
        self.proxy_pass = cfg.get("proxy_pass", "pass1234")
        self.web_user = cfg.get("web_user", "admin")
        self.web_pass = cfg.get("web_pass", "admin123")
        self.sub_token = cfg.get("sub_token", "auto")
        self.proxy_port_base = int(cfg.get("proxy_port_base", config.PROXY_PORT_BASE))
        self.max_tunnels = int(cfg.get("max_tunnels", config.MAX_TUNNELS))
        self.port_base = config.PROXY_PORT_BASE
        self.host = config.PROXY_HOST

        self._nodes: list = []
        self._nodes_lock = threading.Lock()
        self.tunnel_mgr = tunnel_manager.TunnelManager()
        self.system_check = tunnel_manager.system_check()
        self._proxy: dict[int, proxy_mod.ProxyInstance] = {}
        self._exit_ips: dict[int, str] = {}
        self.running = True

    # ---- node pool ----

    def get_nodes(self) -> list:
        with self._nodes_lock:
            return self._nodes

    def refresh_nodes(self, force: bool = False):
        nodes = node_fetch.refresh_nodes(force=force)
        with self._nodes_lock:
            self._nodes = nodes

    # ---- selection ----

    def toggle_select(self, node_id: str, action: str = "toggle"):
        selected = config.load_selected()
        if action == "add" and node_id not in selected:
            selected.append(node_id)
        elif action == "remove" and node_id in selected:
            selected.remove(node_id)
        else:
            if node_id in selected:
                selected.remove(node_id)
            else:
                selected.append(node_id)
        config.save_selected(selected[:self.max_tunnels])

    def select_by_country(self, country: str, limit: int = 3):
        nodes = self.get_nodes()
        if not nodes:
            raise RuntimeError("节点池尚未就绪,请稍候重试(正在后台拉取节点)")
        candidates = [n for n in nodes
                      if n.get("country_short") == country.upper() and n.get("reachable")]
        candidates.sort(key=lambda n: n.get("latency_ms") if n.get("latency_ms") is not None else 10**9)
        if not candidates:
            raise RuntimeError("未找到该国家的可达节点: " + country)
        selected = [n["id"] for n in candidates[:limit]]
        config.save_selected(selected[:self.max_tunnels])

    # ---- config ----

    def public_config(self) -> dict:
        cfg = config.load_config()
        return {
            "proxy_user": self.proxy_user,
            "proxy_pass": self.proxy_pass,
            "web_user": self.web_user,
            "sub_token": self.sub_token,
            "server_host": public_ip(),
            "proxy_port_base": self.proxy_port_base,
            "max_tunnels": self.max_tunnels,
            "env": {
                "openvpn": self.system_check.get("openvpn"),
                "iproute2": self.system_check.get("iproute2"),
                "tun_device": self.system_check.get("tun_device"),
                "root": self.system_check.get("root"),
            },
        }

    def update_config(self, data: dict):
        if "proxy_user" in data:
            self.proxy_user = str(data["proxy_user"])
        if "proxy_pass" in data:
            self.proxy_pass = str(data["proxy_pass"])
        if "web_user" in data:
            self.web_user = str(data["web_user"])
        if "web_pass" in data:
            self.web_pass = str(data["web_pass"])
        if "sub_token" in data:
            self.sub_token = str(data["sub_token"])
        cfg = config.load_config()
        cfg.update({
            "proxy_user": self.proxy_user,
            "proxy_pass": self.proxy_pass,
            "web_user": self.web_user,
            "web_pass": self.web_pass,
            "sub_token": self.sub_token,
        })
        config.save_config(cfg)

    # ---- tunnels & proxies sync ----

    def _sync_proxies(self):
        """为每个存活隧道建/停对应端口的代理实例。"""
        alive = [t for t in self.tunnel_mgr.summary().get("tunnels", []) if t.get("alive")]
        wanted_ports = {int(t["port"]) for t in alive}
        # stop proxies whose tunnel died
        for port in list(self._proxy.keys()):
            if port not in wanted_ports:
                try:
                    self._proxy[port].stop()
                except Exception:
                    pass
                self._proxy.pop(port, None)
        # start proxies for new tunnels
        for t in alive:
            port = int(t["port"])
            if port in self._proxy:
                continue
            inst = proxy_mod.ProxyInstance(
                self.host, port, t["tun"],
                username=self.proxy_user, password=self.proxy_pass,
            )
            try:
                inst.start()
                self._proxy[port] = inst
            except Exception as e:
                print("[proxy] start failed on " + str(port) + ": " + str(e), flush=True)

    def apply_selection(self):
        nodes = self.get_nodes()
        selected = config.load_selected()
        self.tunnel_mgr.apply_nodes(nodes, selected)
        self._sync_proxies()

    def reconnect_all(self):
        for t in self.tunnel_mgr.tunnels:
            if t is not None:
                t.disconnect(cleanup=True)
                t.connect()
        self._sync_proxies()

    # ---- web ----

    def render_index(self) -> str:
        return render_index(self)

    # ---- lifecycle ----

    def _boot(self):
        """后台初始化:拉节点 -> 建隧道。"""
        try:
            self.refresh_nodes(force=True)
            self.apply_selection()
        except Exception as e:
            print("[boot] init error: " + str(e), flush=True)

    def _maintainer(self):
        """后台循环:定时刷新节点并同步隧道/代理。"""
        while self.running:
            time.sleep(config.FETCH_INTERVAL)
            try:
                self.refresh_nodes(force=False)
                self.apply_selection()
            except Exception as e:
                print("[maintain] error: " + str(e), flush=True)

    def start(self):
        # Web 服务立即可用;节点拉取与隧道同步放后台,避免冷启动等待
        threading.Thread(target=self._boot, daemon=True).start()
        self.tunnel_mgr.start_health_checker()
        threading.Thread(target=self._maintainer, daemon=True).start()

        host = config.load_config().get("web_host", "0.0.0.0")
        port = int(os.environ.get("VSG_WEB_PORT", "8787"))
        server = DualStackServer((host, port), Handler)
        server.app = self
        print("=" * 50, flush=True)
        print("[gateway] Web UI: http://" + host + ":" + str(port) + "/", flush=True)
        print("[gateway] Public IP: " + public_ip(), flush=True)
        print("[gateway] Subscriptions: /sub/clash  /sub/v2ray  /sub/base64", flush=True)
        print("[gateway] Proxy ports: " + str(self.port_base) + " ... " + str(self.port_base + self.max_tunnels - 1), flush=True)
        print("=" * 50, flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            self.tunnel_mgr.stop_all()
            for p in self._proxy.values():
                try:
                    p.stop()
                except Exception:
                    pass


def main():
    app = App()
    app.start()


if __name__ == "__main__":
    main()
