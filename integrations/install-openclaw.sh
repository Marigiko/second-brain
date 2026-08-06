#!/bin/bash
# Instalador de integracion Second Brain para OpenClaw
# Ejecutar despues de instalar OpenClaw: bash install-openclaw.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCLAW_DIR="$HOME/.openclaw"

echo "=== Instalacion Second Brain para OpenClaw ==="

if [ ! -d "$OPENCLAW_DIR" ]; then
  echo "ERROR: OpenClaw no esta instalado en $OPENCLAW_DIR"
  echo "Instala OpenClaw primero, luego ejecuta este script."
  exit 1
fi

AGENTS_FILE="$OPENCLAW_DIR/AGENTS.md"
INSTRUCTIONS="$SCRIPT_DIR/openclaw/AGENTS-instructions.md"

if [ -f "$AGENTS_FILE" ]; then
  if grep -q "Second Brain" "$AGENTS_FILE"; then
    echo "Las instrucciones de Second Brain ya existen en AGENTS.md"
  else
    echo "" >> "$AGENTS_FILE"
    echo "<!-- second-brain:start -->" >> "$AGENTS_FILE"
    cat "$INSTRUCTIONS" >> "$AGENTS_FILE"
    echo "<!-- second-brain:end -->" >> "$AGENTS_FILE"
    echo "Instrucciones agregadas a AGENTS.md"
  fi
else
  cat "$INSTRUCTIONS" > "$AGENTS_FILE"
  echo "AGENTS.md creado con instrucciones de Second Brain"
fi

echo ""
echo "Instalacion completada. OpenClaw ahora integra con Second Brain."
echo "Para verificar: cat $AGENTS_FILE | grep 'Second Brain'"
