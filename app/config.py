#!/usr/bin/env python3
"""vpn-subscription-gateway 配置模块"""
from __future__ import annotations
import os
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("VSG_DATA_DIR", ROOT_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "config.json"
NODES_CACHE = DATA_DIR / "nodes_cache.json"
SELECTED_FILE = DATA_DIR / "selected_nodes.json"
STATE_FILE = DATA_DIR / "state.json"

VPNGATE_API = "https://www.vpngate.net/api/iphone/"
FETCH_INTERVAL = int(os.environ.get("VSG_FETCH_INTERVAL", "1800"))
CHECK_INTERVAL = int(os.environ.get("VSG_CHECK_INTERVAL", "30"))

PROXY_HOST = os.environ.get("VSG_PROXY_HOST", "0.0.0.0")
PROXY_PORT_BASE = int(os.environ.get("VSG_PROXY_PORT_BASE", "10000"))
MAX_TUNNELS = int(os.environ.get("VSG_MAX_TUNNELS", "8"))

TUN_PREFIX = "tun"
ROUTE_TABLE_BASE = 101

PROXY_USER = os.environ.get("VSG_PROXY_USER", "user")
PROXY_PASS = os.environ.get("VSG_PROXY_PASS", "pass1234")
WEB_USER = os.environ.get("VSG_WEB_USER", "admin")
WEB_PASS = os.environ.get("VSG_WEB_PASS", "admin123")
SUB_TOKEN = os.environ.get("VSG_SUB_TOKEN", "")
SERVER_HOST = os.environ.get("VSG_SERVER_HOST", "")

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "proxy_user": PROXY_USER,
        "proxy_pass": PROXY_PASS,
        "web_user": WEB_USER,
        "web_pass": WEB_PASS,
        "sub_token": SUB_TOKEN or "auto",
        "server_host": SERVER_HOST,
        "proxy_port_base": PROXY_PORT_BASE,
        "max_tunnels": MAX_TUNNELS,
    }

def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def load_selected() -> list:
    if SELECTED_FILE.exists():
        try:
            return json.loads(SELECTED_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

def save_selected(ids: list) -> None:
    SELECTED_FILE.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")
