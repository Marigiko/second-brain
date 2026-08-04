#!/bin/bash
# Setup de cron jobs para Second Brain
# Ejecutar una vez: ./setup-cron.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/src/sync-engine.js"
REFINE_SCRIPT="$SCRIPT_DIR/src/refinement.py"
DEDUP_SCRIPT="$SCRIPT_DIR/src/deduplication.py"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"

CRON_SYNC="*/15 * * * * cd $SCRIPT_DIR && node $SYNC_SCRIPT >> $LOG_DIR/sync.log 2>&1"
CRON_REFINE="0 2 */3 * * cd $SCRIPT_DIR && python3 $REFINE_SCRIPT >> $LOG_DIR/refinement.log 2>&1"
CRON_DEDUP="30 2 */3 * * cd $SCRIPT_DIR && python3 $DEDUP_SCRIPT >> $LOG_DIR/dedup.log 2>&1"

(crontab -l 2>/dev/null | grep -v "second-brain"; echo "$CRON_SYNC") | sort -u | crontab -
(crontab -l 2>/dev/null | grep -v "second-brain"; echo "$CRON_REFINE") | sort -u | crontab -
(crontab -l 2>/dev/null | grep -v "second-brain"; echo "$CRON_DEDUP") | sort -u | crontab -

echo "Cron jobs configurados:"
echo "  - Sync: cada 15 minutos"
echo "  - Refinement: cada 3 dias a las 2:00 AM"
echo "  - Deduplicacion: cada 3 dias a las 2:30 AM"
echo ""
echo "Para verificar: crontab -l"
