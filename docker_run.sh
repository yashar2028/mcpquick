#!/usr/bin/env bash
set -e

docker compose "$@"

if [[ "$*" == *"up"* ]]; then
    gh codespace ports visibility 8000:public--codespace "$CODESPACE_NAME" || true
    gh codespace ports visibility 5173:public--codespace "$CODESPACE_NAME" || true
fi