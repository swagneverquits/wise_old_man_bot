#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

compose() {
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

git pull --ff-only
compose down
compose up -d --build
compose ps
compose logs --tail 80
