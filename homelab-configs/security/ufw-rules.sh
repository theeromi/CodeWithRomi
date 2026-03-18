#!/usr/bin/env bash
set -euo pipefail

# Baseline UFW profile for the homelab dashboard VM.
# Review ports before enabling in production.

sudo apt update
sudo apt install -y ufw

# IMPORTANT: keep SSH open first.
sudo ufw allow 22/tcp comment 'SSH'

# Tailscale
sudo ufw allow 41641/udp comment 'Tailscale'

# Service ports
sudo ufw allow 9000/tcp comment 'Portainer'
sudo ufw allow 3001/tcp comment 'Grafana'
sudo ufw allow 3002/tcp comment 'Uptime Kuma'
sudo ufw allow 6875/tcp comment 'BookStack'
sudo ufw allow 8888/tcp comment 'Wall Monitor'
sudo ufw allow 9090/tcp comment 'Prometheus'
sudo ufw allow 7575/tcp comment 'Homarr'
sudo ufw allow 80/tcp comment 'Caddy HTTP'
sudo ufw allow 443/tcp comment 'Caddy HTTPS'

sudo ufw default deny incoming
sudo ufw default allow outgoing

sudo ufw enable
sudo ufw status verbose
