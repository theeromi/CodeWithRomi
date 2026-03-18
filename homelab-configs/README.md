# Homelab Config Pack

This folder contains a sanitized, copy-paste-ready baseline for the homelab stack from the members guide.

## Included services

- Portainer
- Prometheus + Node Exporter
- Grafana
- Uptime Kuma
- Vaultwarden + Caddy (Tailscale cert flow)
- BookStack + MariaDB
- Wall Monitor (nginx static host)
- UFW baseline rules
- Docker cleanup script

## Security first

All sensitive values are placeholders in this repository.

Replace placeholders before running any stack:

- `CHANGE_ME_*`
- `your-domain.ts.net`
- `192.168.1.X`
- `yourusername`

## Quick start

1. Copy one service directory to your server (or clone this repo).
2. Edit environment values and domains.
3. Start with `docker compose up -d` in each directory.
4. Validate with `docker compose ps` and service health checks.

## Recommended deployment order

1. `portainer`
2. `monitoring/prometheus`
3. `monitoring/grafana`
4. `monitoring/uptime-kuma`
5. `vaultwarden`
6. `bookstack`
7. `wall-monitor`
8. `security/ufw-rules.sh`

## Notes

- Use strong random values for all admin tokens and passwords.
- Do not expose private services publicly unless you understand the threat model.
- Keep backups of volumes before major upgrades.
