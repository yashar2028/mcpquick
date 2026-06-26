#!/usr/bin/env bash
set -e

if [[ "$1" == "up" ]]; then
    shift
    docker compose up "$@" -d

    gh codespace ports visibility 8000:public --codespace "$CODESPACE_NAME"
    gh codespace ports visibility 5173:public --codespace "$CODESPACE_NAME"

    docker compose logs -f
else
    docker compose "$@"
fi