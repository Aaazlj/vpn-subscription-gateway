#!/usr/bin/env python3
"""Multi-port HTTP/SOCKS5 proxy server. Each instance binds to one tun device."""
from __future__ import annotations
import base64
import os
import secrets
import select
import socket
import threading
import urllib.parse
import time


def recv_exact(sock: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("Unexpected disconnect.")
        data += chunk
    return data


def parse_host_port(authority: str, default_port: int):
    authority = authority.strip()
    if authority.startswith("["):
        host_part, sep, rest = authority.partition("]")
        host = host_part.lstrip("[")
        port = default_port
        if sep and rest.startswith(":"):
            port = int(rest[1:]) or default_port
        return host, port
    if authority.count(":") == 1:
        host, _, port_text = authority.rpartition(":")
        return host, int(port_text) or default_port
    return authority, default_port


class ProxyInstance:
    """One proxy instance: listen on one port, route outbound via one tun device."""

    def __init__(self, host: str, port: int, tun: str,
                 username: str | None = None, password: str | None = None,
                 max_connections: int = 256):
        self.host = host
        self.port = port
        self.tun = tun
        self.username = username
        self.password = password
        self.max_connections = max_connections
        self.sem = threading.BoundedSemaphore(max_connections)
        self.server = None
        self.thread = None
        self.running = False

    def auth_enabled(self) -> bool:
        return bool(self.username is not None or self.password is not None)

    def check_credentials(self, user: str | None, pw: str | None) -> bool:
        if not self.auth_enabled():
            return True
        return (secrets.compare_digest(user or "", self.username or "")
                and secrets.compare_digest(pw or "", self.password or ""))

    def create_connection(self, address, timeout: float = 20):
        host, port = address
        err = None
        for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)
                sock.settimeout(timeout)
                if self.tun:
                    try:
                        sock.setsockopt(socket.SOL_SOCKET, 25, self.tun.encode("utf-8"))
                    except OSError:
                        pass  # no perm or no device: fall back to default route (debug on non-root)
                sock.connect(sa)
                return sock
            except OSError as e:
                err = e
                if sock is not None:
                    sock.close()
        raise err or OSError("getaddrinfo empty")

    def relay(self, left, right):
        sockets = [left, right]
        while True:
            try:
                readable, _, errored = select.select(sockets, [], sockets, 120)
            except OSError:
                return
            if errored or not readable:
                return
            for source in readable:
                target = right if source is left else left
                try:
                    data = source.recv(65536)
                except OSError:
                    return
                if not data:
                    return
                try:
                    target.sendall(data)
                except OSError:
                    return

    def socks5_client(self, client, first_byte: bytes):
        upstream = None
        try:
            methods_count = recv_exact(client, 1)[0]
            methods = recv_exact(client, methods_count)
            if self.auth_enabled():
                if 2 not in methods:
                    client.sendall(b"\x05\xff")
                    return
                client.sendall(b"\x05\x02")
                auth_version = recv_exact(client, 1)[0]
                if auth_version != 1:
                    client.sendall(b"\x01\x01")
                    return
                username = recv_exact(client, recv_exact(client, 1)[0]).decode("utf-8", errors="replace")
                password = recv_exact(client, recv_exact(client, 1)[0]).decode("utf-8", errors="replace")
                if not self.check_credentials(username, password):
                    client.sendall(b"\x01\x01")
                    return
                client.sendall(b"\x01\x00")
            else:
                client.sendall(b"\x05\x00")
            version, command, _, address_type = recv_exact(client, 4)
            if version != 5 or command != 1:
                client.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
                return
            if address_type == 1:
                host = socket.inet_ntoa(recv_exact(client, 4))
            elif address_type == 3:
                host = recv_exact(client, recv_exact(client, 1)[0]).decode("idna")
            elif address_type == 4:
                host = socket.inet_ntop(socket.AF_INET6, recv_exact(client, 16))
            else:
                client.sendall(b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00")
                return
            port = int.from_bytes(recv_exact(client, 2), "big")
            try:
                upstream = self.create_connection((host, port), timeout=20)
            except Exception:
                try:
                    client.sendall(b"\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00")
                except OSError:
                    pass
                raise
            client.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
            self.relay(client, upstream)
        except Exception:
            pass
        finally:
            try:
                client.close()
            except OSError:
                pass
            if upstream is not None:
                try:
                    upstream.close()
                except OSError:
                    pass

    def read_http_header(self, client, first_byte: bytes) -> bytes:
        data = first_byte
        while b"\r\n\r\n" not in data and len(data) < 65536:
            try:
                chunk = client.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            data += chunk
        return data

    def http_client(self, client, first_byte: bytes):
        upstream = None
        try:
            header = self.read_http_header(client, first_byte)
            if b"\r\n\r\n" not in header:
                client.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
                return
            head, rest = header.split(b"\r\n\r\n", 1)
            lines = head.decode("iso-8859-1", errors="replace").split("\r\n")
            try:
                method, target, version = lines[0].split(" ", 2)
            except ValueError:
                client.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
                return
            if not version.startswith("HTTP/"):
                client.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
                return
            if self.auth_enabled():
                auth_ok = False
                for line in lines[1:]:
                    name, sep, value = line.partition(":")
                    if not sep or name.strip().lower() != "proxy-authorization":
                        continue
                    scheme, _, token = value.strip().partition(" ")
                    if scheme.lower() != "basic" or not token:
                        continue
                    try:
                        decoded = base64.b64decode(token, validate=True).decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    user, sep2, pw = decoded.partition(":")
                    if sep2 and self.check_credentials(user, pw):
                        auth_ok = True
                    break
                if not auth_ok:
                    client.sendall(b"HTTP/1.1 407 Proxy Authentication Required\r\n"
                                   b'Proxy-Authenticate: Basic realm=\"Proxy\"\r\nContent-Length: 0\r\n\r\n')
                    return
            if method.upper() == "CONNECT":
                host, port = parse_host_port(target, 443)
                upstream = self.create_connection((host, port), timeout=20)
                client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                if rest:
                    upstream.sendall(rest)
                self.relay(client, upstream)
                return
            try:
                parsed = urllib.parse.urlsplit(target)
            except ValueError:
                client.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
                return
            hostname = parsed.hostname
            port = parsed.port
            scheme = parsed.scheme
            if not hostname:
                for line in lines[1:]:
                    if line.lower().startswith("host:"):
                        host_val = line.split(":", 1)[1].strip()
                        if "[" in host_val and "]" in host_val:
                            host_part, _, port_part = host_val.rpartition("]")
                            hostname = host_part.lstrip("[")
                            if port_part.startswith(":"):
                                pv = port_part.lstrip(":")
                                port = int(pv) if pv.isdigit() else None
                        else:
                            hostname, p2 = parse_host_port(host_val, 0)
                            port = p2 or None
                        break
            if not hostname:
                client.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
                return
            port = port or (443 if scheme == "https" else 80)
            path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
            headers = [ln for ln in lines[1:]
                       if not ln.lower().startswith(("proxy-connection:", "connection:", "proxy-authorization:"))]
            request = method + " " + path + " " + version + "\r\n" + "\r\n".join(headers)
            request += "\r\nConnection: close\r\n\r\n"
            upstream = self.create_connection((hostname, port), timeout=20)
            upstream.sendall(request.encode("iso-8859-1") + rest)
            self.relay(client, upstream)
        except Exception:
            try:
                client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass
        finally:
            try:
                client.close()
            except OSError:
                pass
            if upstream is not None:
                try:
                    upstream.close()
                except OSError:
                    pass

    def proxy_client(self, client, address):
        try:
            client.settimeout(30)
            first = recv_exact(client, 1)
            if first == b"\x05":
                self.socks5_client(client, first)
            else:
                self.http_client(client, first)
        except Exception:
            pass
        finally:
            try:
                client.close()
            except OSError:
                pass

    def serve(self):
        is_ipv6 = ":" in self.host or self.host == ""
        af = socket.AF_INET6 if is_ipv6 else socket.AF_INET
        server = socket.socket(af, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if is_ipv6:
            try:
                server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except OSError:
                pass
        server.bind((self.host, self.port))
        server.listen(256)
        self.server = server
        self.running = True
        print("[proxy] listening " + self.host + ":" + str(self.port) + " via " + self.tun, flush=True)
        while self.running:
            try:
                client, address = server.accept()
                if not self.sem.acquire(blocking=False):
                    try:
                        client.close()
                    except OSError:
                        pass
                    continue
                def run_client():
                    try:
                        self.proxy_client(client, address)
                    finally:
                        self.sem.release()
                threading.Thread(target=run_client, daemon=True).start()
            except OSError:
                break
        try:
            server.close()
        except OSError:
            pass

    def start(self):
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.running = False
        if self.server is not None:
            try:
                self.server.close()
            except OSError:
                pass
