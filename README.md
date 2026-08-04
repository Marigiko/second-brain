# Second Brain - Modulo de Memoria Persistente

Sistema de memoria hibrida que captura aprendizajes, decisiones y contexto
de multiples agentes en archivos locales versionables con sync a Obsidian.

## Estructura

```
second-brain/
├── config.json          # Configuracion global
├── package.json         # Dependencias Node.js
├── src/                 # Codigo fuente
│   ├── write-note.js    # CLI de escritura para agentes
│   ├── sync-engine.js   # Sync cada 15 min a Obsidian
│   ├── obsidian-client.js  # Cliente REST API de Obsidian
│   ├── webhook-server.js   # Receptor de webhooks (n8n)
│   ├── refinement.py    # Refinamiento cada 3 dias
│   └── deduplication.py # Deduplicacion de notas similares
├── templates/           # Plantillas
│   └── frontmatter.json # Schema de frontmatter por tipo
├── hooks/               # Scripts de integracion
│   ├── mimo-hook.sh
│   ├── opencode-hook.sh
│   └── mimo-memory-bridge.md
└── setup-cron.sh        # Configuracion de cron jobs
```

## Uso por Agente

### MiMoCode / OpenCode

```bash
# Escribir un aprendizaje
node src/write-note.js <project> aprendizajes "titulo" "mimo" "Contenido..."

# Escribir una decision
node src/write-note.js <project> decisiones "titulo" "mimo" "Contenido..."

# Sesion diaria (append automatico)
node src/write-note.js <project> session "Titulo sesion" "mimo" "Resumen..."
```

### n8n

Enviar POST a `http://localhost:9876/webhook/learning`:
```json
{
  "project": "mi-proyecto",
  "type": "aprendizajes",
  "title": "titulo-slug",
  "content": "Contenido del aprendizaje",
  "tags": ["tag1", "tag2"]
}
```

## Configuracion

1. Editar `config.json` con tus proyectos y ruta de Obsidian
2. Instalar dependencias: `npm install`
3. Configurar cron: `bash setup-cron.sh`
4. Iniciar webhook: `npm run webhook`

## Ciclo de Vida

1. Agente escribe en `.second-brain/` del proyecto
2. Sync engine detecta cambios cada 15 min
3. Exporta a Obsidian via REST API
4. Refinement engine consolida cada 3 dias
5. Deduplication detecta notas similares y crea cross-references
