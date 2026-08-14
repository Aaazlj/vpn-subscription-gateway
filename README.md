# VPN Subscription Gateway (VPN 订阅网关)

把 VPNGate 免费 OpenVPN 节点聚合到自己的服务器,自选节点,一键生成 Clash / v2rayN / Base64 订阅链接。

> 灵感来自 aimili-vpngate 与 Free-Residential-IP-Proxy-Controller:
> 复用 VPNGate 节点源 + 多隧道策略路由 + 双协议代理,新增多节点并行与订阅生成。

## 工作原理

VPNGate API -> 节点池(拉取 + 并发测速 + 国家/延迟排序)
  -> Web UI + API(节点列表 / 自选 / 按国家挑选)
  -> 选中的 N 个节点 -> tun0+路由表101, tun1+路由表102...
  -> 每个隧道一个代理端口(10000, 10001...),HTTP/SOCKS5 双协议带认证
  -> 订阅生成:每个节点 = socks5://user:pass@服务器IP:端口
  -> 输出 Clash YAML / v2rayN socks URI / Base64

## 特性

- 节点源: VPNGate 免费公共 OpenVPN 服务器(自动解析 + 解码配置 + 并发测速)
- 多隧道: 每个选中节点一条独立 OpenVPN 隧道(tun0/tun1/...),独立策略路由表(101/102/...)
- 多端口代理: 每个隧道一个 HTTP/SOCKS5 双协议端口(默认 10000 起),带用户名密码认证
- 订阅: 每个隧道一个 socks5://user:pass@IP:端口 条目,Clash / v2rayN / NekoBox 可直接导入
- 健康检查: 隧道掉线自动重连

## 快速部署

### 方式一: Docker (推荐)

git clone <your-repo> && cd vpn-subscription-gateway
docker compose up -d --build

> 需要 privileged: true 或 --device /dev/net/tun --cap-add NET_ADMIN NET_RAW(compose 已配置)

### 方式二: 裸机 (Debian/Ubuntu)

sudo bash install.sh

自动安装 openvpn/iproute2、创建 /dev/net/tun、注册 systemd 服务。

## 使用

1. 打开 Web UI: http://服务器IP:8787 (默认 admin/admin123,请立即修改)
2. 面板会自动拉取并测速节点,按国家/延迟筛选
3. 自选: 点击节点"选择"加入订阅;或"自动挑选"按国家选 N 个
4. 复制订阅链接到客户端:
   - Clash: http://服务器IP:8787/sub/clash
   - v2rayN/NekoBox: http://服务器IP:8787/sub/v2ray
   - 通用: http://服务器IP:8787/sub/base64
5. 客户端导入后,每个条目对应一个隧道出口

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | / | Web 面板 |
| GET | /api/nodes?country=JP&reachable=1 | 节点列表 |
| GET | /api/countries | 国家聚合 |
| GET | /api/status | 状态(选中/隧道/公网IP) |
| POST | /api/refresh | 强制拉取+测速 |
| POST | /api/select | {node_id, action} 或 {country, limit} |
| POST | /api/reconnect | 全部隧道重连 |
| GET | /sub/clash | Clash 订阅 |
| GET | /sub/v2ray | v2rayN 订阅 |
| GET | /sub/base64 | Base64 订阅 |

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| VSG_WEB_PORT | 8787 | Web UI 端口 |
| VSG_PROXY_HOST | 0.0.0.0 | 代理监听地址 |
| VSG_PROXY_PORT_BASE | 10000 | 代理起始端口 |
| VSG_MAX_TUNNELS | 8 | 最大并发隧道数 |
| VSG_PROXY_USER / PASS | user / pass1234 | 代理认证 |
| VSG_WEB_USER / PASS | admin / admin123 | 面板认证 |
| VSG_SUB_TOKEN | (空) | 订阅访问令牌 |
| VSG_SERVER_HOST | (空) | 公网 IP,留空自动探测 |
| VSG_DATA_DIR | ./data | 数据目录 |

## 目录结构

vpn-subscription-gateway/
- Dockerfile / docker-compose.yml / install.sh
- README.md
- app/
  - main.py            # 入口 + App 编排
  - config.py          # 配置
  - node_fetch.py      # VPNGate 拉取 + 解析 + 并发测速
  - tunnel_manager.py  # 多隧道 OpenVPN + 策略路由 + 健康检查
  - proxy.py           # 多端口 HTTP/SOCKS5 代理(按 tun 绑定)
  - subscriber.py      # Clash / v2rayN / Base64 订阅生成
  - webui.py           # HTTP API 服务
  - html_page.py       # 管理面板前端

## 注意事项

- 需要 Linux + root(OpenVPN tun + 策略路由);macOS 本地只能跑节点拉取/订阅生成
- 默认代理端口绑定 0.0.0.0,若只自用建议改 127.0.0.1 并在面板/防火墙限制
- VPNGate 节点是公共免费资源,稳定性不保证;仅供学习与测试
- 请遵守当地法律法规,勿用于违法用途
