#!/usr/bin/env bash
set -euo pipefail

echo "[+] Updating repository"
git pull --rebase

echo "[+] Rebuilding container"
docker compose build

echo "[+] Restarting bot"
docker compose up -d
