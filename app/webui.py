#!/usr/bin/env python3
"""Web UI + REST API for the gateway."""
from __future__ import annotations
import json
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import config, subscriber


def public_ip() -> str:
    cfg = config.load_config()
    if cfg.get("server_host"):
        return cfg["server_host"]
    ip = config.load_state().get("public_ip", "")
    if ip:
        return ip
    from . import node_fetch
    ip = node_fetch.public_ip()
    state = config.load_state()
    state["public_ip"] = ip
    config.save_state(state)
    return ip


class DualStackServer(ThreadingHTTPServer):
    address_family = None  # set dynamically
    daemon_threads = True

    def __init__(self, server_address, handler_cls, bind_and_activate=True):
        host, port = server_address
        if ":" in host or host == "":
            DualStackServer.address_family = __import__("socket").AF_INET6
        else:
            DualStackServer.address_family = __import__("socket").AF_INET
        super().__init__(server_address, handler_cls, bind_and_activate)


class Handler(BaseHTTPRequestHandler):
    server_version = "VPN-Subscription-Gateway/1.0"

    def log_message(self, fmt, *args):
        pass  # quiet

    @property
    def app(self):
        return getattr(self.server, "app", None)

    def _send(self, body: bytes, ctype: str, status: int = 200, extra: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _json(self, data, status: int = 200, extra: dict | None = None):
        self._send(json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status, extra)

    def _text(self, s, ctype="text/plain; charset=utf-8", status: int = 200, extra=None):
        self._send(s.encode("utf-8"), ctype, status, extra)

    def _html(self, s, status: int = 200):
        self._send(s.encode("utf-8"), "text/html; charset=utf-8", status)

    def _read_json_body(self):
        try:
            ln = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(ln) if ln else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def _auth_ok(self) -> bool:
        app = self.app
        if app is None:
            return True
        if not app.web_user:
            return True
        import base64
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
            user, _, pw = decoded.partition(":")
            import hmac
            return hmac.compare_digest(user, app.web_user) and hmac.compare_digest(pw, app.web_pass)
        except Exception:
            return False

    def _token_ok(self) -> bool:
        app = self.app
        if app is None:
            return True
        return subscriber.token_ok(self.headers.get("X-Sub-Token", ""), app.sub_token)

    def _require_web(self) -> bool:
        if not self._auth_ok():
            self._json({"error": "unauthorized"}, 401,
                       extra={"WWW-Authenticate": 'Basic realm="VPN-Gateway"',
                              'Cache-Control': 'no-store'})
            return False
        return True

    # ---------------- routes ----------------

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            if not self._require_web():
                return
            self._html(self.app.render_index())
        elif path == "/api/nodes":
            if not self._require_web():
                return
            app = self.app
            nodes = app.get_nodes()
            cc = qs.get("country", [""])[0]
            reachable = qs.get("reachable", [""])[0] == "1"
            if cc:
                nodes = [n for n in nodes if n.get("country_short") == cc.upper()]
            if reachable:
                nodes = [n for n in nodes if n.get("reachable")]
            self._json({"total": len(nodes), "nodes": nodes})
        elif path == "/api/countries":
            if not self._require_web():
                return
            from . import node_fetch
            self._json(node_fetch.get_countries(self.app.get_nodes()))
        elif path == "/api/status":
            if not self._require_web():
                return
            app = self.app
            selected = config.load_selected()
            self._json({
                "selected": selected,
                "tunnels": app.tunnel_mgr.summary(),
                "public_ip": public_ip(),
                "system": app.system_check,
                "config": app.public_config(),
            })
        elif path == "/api/config":
            if not self._require_web():
                return
            self._json(app.public_config())
        elif path.startswith("/sub/"):
            self._serve_subscription(path)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/api/refresh":
            if not self._require_web():
                return
            app = self.app
            app.refresh_nodes(force=True)
            try:
                app.apply_selection()
            except Exception as e:
                print("[webui] apply_selection after refresh error: " + str(e), flush=True)
            self._json({"ok": True, "total": len(app.get_nodes())})
        elif path == "/api/select":
            if not self._require_web():
                return
            app = self.app
            data = self._read_json_body()
            node_id = data.get("node_id", "")
            action = data.get("action", "toggle")
            country = data.get("country", "")
            limit = int(data.get("limit", 3) or 3)
            if country:
                try:
                    app.select_by_country(country, limit)
                except RuntimeError as e:
                    self._json({"error": str(e)}, 400)
                    return
            elif node_id:
                app.toggle_select(node_id, action)
            else:
                self._json({"error": "node_id or country required"}, 400)
                return
            # 选择变更后立即重建隧道与代理
            try:
                app.apply_selection()
            except Exception as e:
                print("[webui] apply_selection error: " + str(e), flush=True)
            self._json({"ok": True, "selected": config.load_selected()})
        elif path == "/api/config":
            if not self._require_web():
                return
            data = self._read_json_body()
            app = self.app
            app.update_config(data)
            self._json({"ok": True, "config": app.public_config()})
        elif path == "/api/reconnect":
            if not self._require_web():
                return
            app = self.app
            app.reconnect_all()
            self._json({"ok": True})
        else:
            self._json({"error": "not found"}, 404)

    # ---------------- subscription ----------------

    def _serve_subscription(self, path: str):
        app = self.app
        if not self._token_ok():
            return self._text("forbidden", "text/plain", 403)
        fmt = path.split("/")[-1]
        tunnel_list = app.tunnel_mgr.summary().get("tunnels", [])
        entries = subscriber.build_entries(
            public_ip(), tunnel_list, app.proxy_user, app.proxy_pass
        )
        if fmt == "clash":
            data = subscriber.clash_yaml(entries)
            self._text(data, "text/yaml; charset=utf-8",
                       extra={"Content-Disposition": 'attachment; filename="clash.yaml"'})
        elif fmt == "v2ray":
            data = subscriber.v2ray_socks_uris(entries)
            self._text(data, "text/plain; charset=utf-8",
                       extra={"Content-Disposition": 'attachment; filename="v2ray.txt"'})
        elif fmt == "base64":
            data = subscriber.base64_subscription(entries)
            self._text(data, "text/plain; charset=utf-8",
                       extra={"Content-Disposition": 'attachment; filename="sub.txt"'})
        else:
            self._json({"error": "unknown format"}, 404)
