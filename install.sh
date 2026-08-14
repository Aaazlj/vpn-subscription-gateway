#!/usr/bin/env bash
# VPN Subscription Gateway - bare-metal installer (Debian/Ubuntu, root)
set -e

if [ "$(id -u)" != "0" ]; then
  echo "请用 root 用户运行此脚本: sudo bash install.sh"
  exit 1
fi

APP_DIR=/opt/vsg
DATA_DIR=/var/lib/vsg

echo "=============================================="
echo " VPN Subscription Gateway Installer"
echo "=============================================="

# 1. system deps
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q openvpn iproute2 iptables curl python3 ca-certificates || {
  echo "安装依赖失败,请检查网络或 apt 源"; exit 1;
}

# 2. tun device
mkdir -p /dev/net
if [ ! -e /dev/net/tun ]; then
  mknod /dev/net/tun c 10 200 2>/dev/null || echo "警告: /dev/net/tun 创建失败,请确认已启用 TUN"
fi

# 3. copy code
mkdir -p "$APP_DIR" "$DATA_DIR"
rm -rf "$APP_DIR/app"
cp -r "$(dirname "$0")/app" "$APP_DIR/app"
chmod -R 755 "$APP_DIR"

# 4. config defaults
cat > /etc/default/vsg <<'ENVF'
VSG_WEB_PORT=8787
VSG_PROXY_HOST=0.0.0.0
VSG_PROXY_PORT_BASE=10000
VSG_MAX_TUNNELS=8
VSG_PROXY_USER=user
VSG_PROXY_PASS=pass1234
VSG_WEB_USER=admin
VSG_WEB_PASS=admin123
VSG_DATA_DIR=/var/lib/vsg
ENVF

# 5. systemd unit
cat > /etc/systemd/system/vsg.service <<'UNIT'
[Unit]
Description=VPN Subscription Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/default/vsg
ExecStart=/usr/bin/python3 -u -m app.main
WorkingDirectory=/opt/vsg
Restart=always
RestartSec=5
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable vsg
systemctl restart vsg

echo ""
echo "部署完成!"
echo "   Web UI:      http://<你的服务器IP>:8787  (admin / admin123)"
echo "   订阅链接:    http://<你的服务器IP>:8787/sub/clash"
echo "               http://<你的服务器IP>:8787/sub/v2ray"
echo "               http://<你的服务器IP>:8787/sub/base64"
echo "   代理端口:    10000-10007"
echo "   请尽快登录面板修改默认密码!"
