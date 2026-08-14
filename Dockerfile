FROM python:3.12-slim

# Install OpenVPN + network tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends openvpn iproute2 iptables curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /dev/net

WORKDIR /opt/vsg
COPY app /opt/vsg/app

# Runtime data
ENV VSG_DATA_DIR=/data \
    VSG_WEB_PORT=8787 \
    VSG_PROXY_HOST=0.0.0.0 \
    VSG_PROXY_PORT_BASE=10000 \
    VSG_MAX_TUNNELS=8

VOLUME ["/data"]
EXPOSE 8787 10000-10007

# Ensure tun device exists (the container must be started with --device /dev/net/tun)
RUN mkdir -p /dev/net

CMD ["python3", "-u", "-m", "app.main"]

