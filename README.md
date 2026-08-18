# VPN Subscription Gateway

聚合 VPNGate 公共 VPN 节点，自动建立 OpenVPN 隧道并暴露为 SOCKS5/HTTP 代理，生成 Clash / v2rayN 订阅链接。自带 Web 管理面板，支持节点筛选、自选、批量操作、隧道监控和实时日志。

## 功能

- **节点聚合**：自动从 VPNGate API 拉取全球公共 VPN 节点，TCP 探活并计算延迟
- **多隧道并行**：同时建立多条 OpenVPN 隧道（每条独立 tun 设备 + 策略路由 + 代理端口）
- **代理出口**：每条隧道对应一个 SOCKS5/HTTP 代理端口，支持用户名密码认证
- **订阅生成**：一键生成 Clash / v2rayN / Base64 订阅链接，导入客户端即用
- **Web 管理面板**（Vue 3 + Element Plus）：
  - 节点表格（搜索 / 国家筛选 / 分页 / IP 类型标签）
  - 按国家自动挑选延迟最低节点
  - 批量加入 / 取消订阅
  - 隧道状态实时监控
  - 订阅链接一键复制
  - 实时日志面板
  - 配置在线修改（密码 / 端口 / Token）
- **安全**：登录页 + Token 认证（非 Basic Auth 弹窗）

## 快速部署

### Docker 部署（推荐）

```bash
git clone https://github.com/Aaazlj/vpn-subscription-gateway.git
cd vpn-subscription-gateway
docker compose up -d --build
```

访问 `http://服务器IP:8787`，默认账号 `admin / admin123`。

### 裸金属部署

```bash
bash install.sh
```

自动安装依赖（openvpn / iproute2 / nodejs / npm），构建前端，注册 systemd 服务。

## 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VSG_WEB_PORT` | 8787 | Web 面板端口 |
| `VSG_PROXY_HOST` | 0.0.0.0 | 代理监听地址 |
| `VSG_PROXY_PORT_BASE` | 10000 | 代理起始端口 |
| `VSG_MAX_TUNNELS` | 8 | 最大隧道数 |
| `VSG_PROXY_USER` | user | 代理认证用户名 |
| `VSG_PROXY_PASS` | pass1234 | 代理认证密码 |
| `VSG_WEB_USER` | admin | Web 面板用户名 |
| `VSG_WEB_PASS` | admin123 | Web 面板密码 |
| `VSG_DATA_DIR` | /var/lib/vsg | 数据目录 |
| `VSG_SUB_TOKEN` | auto | 订阅 Token |

### Docker Compose

在 `docker-compose.yml` 的 `environment` 段修改后执行：

```bash
docker compose up -d
```

## 使用

1. 登录 Web 面板
2. 点击「拉取节点」从 VPNGate 获取节点列表
3. 按国家自动挑选，或手动勾选节点批量加入
4. 隧道自动建立后，在「订阅链接」页面复制订阅 URL
5. 导入 Clash / v2rayN 等客户端

## 技术架构

- **后端**：Python 3 + OpenVPN + iproute2（策略路由 `oif` 规则，不影响服务器 SSH）
- **前端**：Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router
- **部署**：Docker 多阶段构建（Node 构建前端 → Python 运行后端）

## 端口说明

| 端口 | 用途 |
|------|------|
| 8787 | Web 管理面板 |
| 10000-10007 | SOCKS5/HTTP 代理端口（每条隧道一个） |

## 注意事项

- 服务器需要支持 TUN 设备（`/dev/net/tun`）
- Docker 部署需要 `--privileged` 或 `--cap-add NET_ADMIN,NET_RAW` + `--device /dev/net/tun`
- VPNGate 节点由志愿者提供，稳定性和速度不保证
- 请遵守当地法律法规，仅用于合法用途

## License

MIT
