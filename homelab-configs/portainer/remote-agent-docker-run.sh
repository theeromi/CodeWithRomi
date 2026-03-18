#!/usr/bin/env bash
set -euo pipefail

# Run on each remote Docker host to connect it to Portainer.
docker run -d \
  -p 9001:9001 \
  --name portainer_agent \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/lib/docker/volumes:/var/lib/docker/volumes \
  portainer/agent:latest

echo "Portainer agent started on port 9001"
