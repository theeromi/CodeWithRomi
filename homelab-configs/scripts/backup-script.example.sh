#!/usr/bin/env bash
set -euo pipefail

# Example NAS backup script for Linux/macOS.
# Replace values before use.

SRC="user@10.0.0.40:/volume1/docker/"
DEST="/Users/yourusername/Backups/NAS/"

rsync -avz --delete "$SRC" "$DEST"
