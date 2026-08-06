#!/bin/bash
# Instalador de integracion Second Brain para Hermes
# Ejecutar despues de instalar Hermes: bash install-hermes.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_DIR="$HOME/.hermes"

echo "=== Instalacion Second Brain para Hermes ==="

if [ ! -d "$HERMES_DIR" ]; then
  echo "ERROR: Hermes no esta instalado en $HERMES_DIR"
  echo "Instala Hermes primero, luego ejecuta este script."
  exit 1
fi

SOUL_FILE="$HERMES_DIR/SOUL.md"
INSTRUCTIONS="$SCRIPT_DIR/hermes/SOUL-instructions.md"

if [ -f "$SOUL_FILE" ]; then
  if grep -q "Second Brain" "$SOUL_FILE"; then
    echo "Las instrucciones de Second Brain ya existen en SOUL.md"
  else
    echo "" >> "$SOUL_FILE"
    echo "<!-- second-brain:start -->" >> "$SOUL_FILE"
    cat "$INSTRUCTIONS" >> "$SOUL_FILE"
    echo "<!-- second-brain:end -->" >> "$SOUL_FILE"
    echo "Instrucciones agregadas a SOUL.md"
  fi
else
  cat "$INSTRUCTIONS" > "$SOUL_FILE"
  echo "SOUL.md creado con instrucciones de Second Brain"
fi

echo ""
echo "Instalacion completada. Hermes ahora integra con Second Brain."
echo "Para verificar: cat $SOUL_FILE | grep 'Second Brain'"
