# ===== Stage 1: Build Vue frontend =====
FROM node:18-slim AS frontend-builder

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --cache /tmp/npm-cache || npm install --cache /tmp/npm-cache
COPY frontend/ .
RUN npx vite build

# ===== Stage 2: Python runtime =====
FROM python:3.12-slim

# Install OpenVPN + network tools
RUN apt-get update     && apt-get install -y --no-install-recommends openvpn iproute2 iptables curl ca-certificates     && rm -rf /var/lib/apt/lists/*     && mkdir -p /dev/net /data

WORKDIR /opt/vsg

# Copy backend
COPY app /opt/vsg/app

# Copy frontend dist from builder
COPY --from=frontend-builder /build/dist /opt/vsg/frontend/dist

# Runtime config
ENV VSG_DATA_DIR=/data     VSG_WEB_PORT=8787     VSG_PROXY_HOST=0.0.0.0     VSG_PROXY_PORT_BASE=10000     VSG_MAX_TUNNELS=8

VOLUME ["/data"]
EXPOSE 8787 10000-10007

CMD ["python3", "-u", "-m", "app.main"]
