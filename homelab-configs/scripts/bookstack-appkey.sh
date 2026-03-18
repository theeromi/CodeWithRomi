#!/usr/bin/env bash
set -euo pipefail

# Generates BookStack APP_KEY using the BookStack image.
docker run -it --rm --entrypoint /bin/bash \
  lscr.io/linuxserver/bookstack:latest -c "appkey"
