#!/usr/bin/env bash
set -e

docker compose "$@"

if [[ "$*" == *"up"* ]]; then
    gh codespace ports visibility 8000:public || true
    gh codespace ports visibility 5173:public || true
fi