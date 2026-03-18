#!/usr/bin/env bash
set -euo pipefail

echo "Cleaning up Docker..."

docker container prune -f
docker image prune -a -f
docker volume prune -f
docker builder prune -a -f

echo "Cleanup complete"
df -h / | tail -1
