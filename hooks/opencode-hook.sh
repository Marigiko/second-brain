#!/bin/bash
# Hook para OpenCode - Escribe al second-brain tras cada sesion significativa
# Uso: ./opencode-hook.sh <project> <type> <title> <content>

PROJECT="$1"
TYPE="$2"
TITLE="$3"
shift 3
CONTENT="$*"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NODE_SCRIPT="$SCRIPT_DIR/../src/write-note.js"

node "$NODE_SCRIPT" "$PROJECT" "$TYPE" "$TITLE" "opencode" "$CONTENT"
