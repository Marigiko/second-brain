# Second Brain Hibrido con Obsidian - Diseno

**Fecha:** 2026-08-03
**Estado:** Aprobado

## [S1] Problema

Los agentes de IA (MiMoCode, OpenCode, n8n) generan conocimiento valioso durante sesiones de trabajo, pero no existe un sistema centralizado y persistente para capturar, organizar y consultar ese conocimiento. Se pierde contexto entre sesiones y no hay un "Second Brain" que acumule aprendizaje reusable.

## [S2] Solution Overview

Sistema de memoria hibrida: cada proyecto tiene su propio `.second-brain/` con notas en Markdown organizadas por tipo de conocimiento. Un sync engine exporta a Obsidian cada 15 minutos. Un refinement engine consolida y deduplica cada 3 dias.

**Principios:**
- Memoria local como fuente de verdad
- Obsidian como capa de visualizacion/consulta
- Versionable con git (portable entre maquinas)
- Funciona sin Obsidian corriendo (sync reintenta)

## [S3] Estructura de Carpetas

Cada proyecto: `<root>/.second-brain/`
- `diario/` - Sesiones diarias (YYYY-MM-DD.md)
- `decisiones/` - Decisiones tecnicas permanentes
- `aprendizajes/` - Hallazgos y lecciones
- `convenciones/` - Reglas y estandares
- `arquitectura/` - Diseno tecnico

Obsidian: `Second Brain/{Tipo}/{archivo}.md`

## [S4] Frontmatter Estandar

```yaml
type: decision | aprendizaje | convencion | arquitectura | session
agent: mimo | opencode | n8n | manual
project: nombre-del-proyecto
date: YYYY-MM-DD
tags: [...]
created: ISO-8601
sync_status: pending | synced | error
refined: boolean
```

## [S5] Proceso de Captura

| Evento | Destino | Agentes |
|--------|---------|---------|
| Fin sesion | diario/YYYY-MM-DD.md | mimo, opencode |
| Decision | decisiones/{slug}.md | mimo, opencode |
| Hallazgo | aprendizajes/{slug}.md | todos |
| Convencion | convenciones/{slug}.md | mimo, opencode |
| Arquitectura | arquitectura/{slug}.md | mimo, opencode |
| Evento automatico | aprendizajes/{slug}.md | n8n |

## [S6] Sync Engine (15 min)

1. Detectar notas con sync_status: pending/error
2. Diarios -> PATCH append en Obsidian
3. Permanentes -> PUT/POST en Obsidian via REST API
4. Marcar sync_status: synced tras exito
5. Reintentar si Obsidian no disponible

## [S7] Refinement Engine (3 dias)

1. Evaluar relevancia de notas (score: tags, contenido, antiguedad)
2. Consolidar notas diarias en resumenes semanales
3. Marcar notas de baja relevancia como refined
4. Deduplicar: si mismo tema, mergear o cross-referenciar segun contexto
5. Actualizar Obsidian con version refinada

## [S8] Deduplicacion

- Calcular similitud por tags (Jaccard)
- Mismo proyecto + mismo tema -> merge
- Diferentes proyectos + temas similares -> cross-references
- Mantener contexto especifico de cada caso
