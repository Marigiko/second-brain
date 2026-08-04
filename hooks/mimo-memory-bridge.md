# MiMoCode Memory Bridge

Este archivo documenta como MiMoCode se integra con el sistema Second Brain.

## Cuando escribir

Escribir en `.second-brain/` cuando:
1. Se toma una decision tecnica importante
2. Se descubre un bug o solucion relevante
3. Se establece una convencion o estandar
4. Se completa una sesion de trabajo significativa
5. Se aprende algo reusable

## Como escribir

Usar el CLI:
```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  <project> <type> <title> <agent> <content>
```

Tipos disponibles:
- `decisiones` - Decisiones tecnicas permanentes
- `aprendizajes` - Hallazgos y lecciones aprendidas
- `convenciones` - Reglas y estandares
- `arquitectura` - Diseno tecnico
- `session` - Entradas de diario de sesion

## Ejemplos

```bash
# Decision tecnica
node write-note.js gentle-ai decisiones "auth-strategy-jwt" "mimo" \
  "Se eligio JWT sobre session cookies por..."

# Aprendizaje
node write-note.js gentle-ai aprendizajes "redis-race-condition" "mimo" \
  "Se encontro race condition en el cache de Redis cuando..."

# Sesion
node write-note.js gentle-ai session "Implementacion SDD phase" "mimo" \
  "Se completo la fase de diseno del SDD para dark mode..."
```

## Ubicacion

Cada proyecto tiene su `.second-brain/` en la raiz:
- `/mnt/d/Projects/<project>/.second-brain/`

## Sync

El sync a Obsidian ocurre automaticamente cada 15 minutos.
No se necesita intervencion manual.
