# Second Brain - Modulo de Memoria Persistente

Sistema de memoria hibrida que captura aprendizajes, decisiones y contexto de
multiples agentes en archivos locales versionables, con sync al vault de Obsidian.

La memoria local (`.second-brain/` de cada proyecto) es **la fuente de verdad**.
Obsidian es la capa de visualizacion y de conexion entre proyectos.

---

## Como se mapea al vault

El vault `Main` tiene tres areas de primer nivel, y la regla que decide en cual va
una nota esta escrita en `Main/00 - Indice.md`:

> Si la nota deja de importar cuando el proyecto termina, va a **Proyectos**.
> Si sirve para el *proximo* trabajo parecido, va a **Conocimiento**.

```
Main/
├── Proyectos/<Vault Folder>/<Subcarpeta>/nota.md    <- default de todo lo que escribe un agente
├── Conocimiento/<Dominio>/Bandeja de entrada/       <- opt-in explicito por proyecto
└── Archivo/
```

**Un agente no puede tomar esa decision de forma confiable nota por nota**, asi que
el default es siempre `Proyectos`. Para que un proyecto mande alguna categoria a
`Conocimiento`, se declara explicito en `config.json`:

```json
{
  "name": "scrap",
  "vault_folder": "Magnar Scrap",
  "knowledge_domain": "Scraping Legal",
  "knowledge_categories": ["aprendizajes", "convenciones"]
}
```

Con eso:

| Categoria | Destino |
|---|---|
| `decisiones`, `diario`, `arquitectura` | `Proyectos/Magnar Scrap/{Decisiones,Diario,Arquitectura}/` |
| `aprendizajes`, `convenciones` | `Conocimiento/Scraping Legal/Bandeja de entrada/` |

### Por que una "Bandeja de entrada" y no las carpetas del dominio

La taxonomia de un dominio de Conocimiento (`Problemas/`, `Soluciones/`, `Paises/`…)
es **curada a mano** y no se puede derivar de la categoria que usa el agente. Todo lo
que llega por sync cae en una sola bandeja, sin destilar, para que el automatismo no
contamine la estructura curada.

### `vault_folder`: el nombre del repo no es el nombre en el vault

`ai-workstation`, `terax-ai`, `dotfiles` y `mimo-xp` son cuatro repos y **una sola
carpeta** en el vault (`Ecosistema AI`). El mapeo vive en `config.json`; un proyecto
sin registrar cae a una carpeta con el nombre del repo, sin perder la nota.

---

## Estructura del modulo

```
second-brain/
├── config.json             # Vault, areas, routing y proyectos
├── src/
│   ├── vault-paths.js      # UNICA fuente de verdad del routing
│   ├── obsidian-client.js  # REST API + backend de filesystem
│   ├── sync-engine.js      # Sync cada 15 min
│   ├── write-note.js       # CLI de escritura para agentes
│   ├── read-notes.js       # Lectura para inyectar contexto
│   ├── webhook-server.js   # Receptor de webhooks (n8n)
│   ├── refinement.py       # Consolidacion cada 3 dias
│   └── deduplication.py    # Deteccion de notas similares
├── templates/frontmatter.json
├── hooks/                  # mimo, opencode
├── integrations/           # hermes, openclaw
└── setup-cron.sh
```

---

## Uso

```bash
npm install                     # js-yaml y node-cron son requisitos reales

# Escribir
node src/write-note.js <project> aprendizajes "titulo" "claude" "Contenido..."
node src/write-note.js <project> decisiones   "titulo" "mimo"   "Contenido..."
node src/write-note.js <project> session      "Titulo" "mimo"   "Resumen..."

# Sincronizar
node src/sync-engine.js --dry-run    # muestra los destinos sin escribir nada
node src/sync-engine.js              # sync real
node src/sync-engine.js --daemon     # cada 15 min

# Leer
node src/read-notes.js <project> "query"
```

Tipos validos: `session` (append al diario del dia), `decisiones`, `aprendizajes`,
`convenciones`, `arquitectura`.

### n8n

`POST http://localhost:9876/webhook/learning`

```json
{ "project": "mi-proyecto", "type": "aprendizajes", "title": "titulo-slug",
  "content": "...", "tags": ["tag1"] }
```

---

## `write_mode`: por que hay un backend de filesystem

La REST API exige que Obsidian este abierto, con el plugin **Local REST API** activo
y `OBSIDIAN_API_KEY` exportada. Historicamente eso fallo: las primeras notas de prueba
quedaron con `sync_status: error` y un **HTTP 401**, y nunca llegaron al vault.

El vault es un directorio normal y desde WSL se alcanza por `vault_path`, asi que
escribir a disco es el camino confiable — Obsidian toma los cambios solo.

| `write_mode` | Comportamiento |
|---|---|
| `auto` (default) | Intenta REST; si falla, escribe a filesystem |
| `rest` | Solo REST. Falla ruidoso |
| `filesystem` | Solo disco. No necesita Obsidian abierto |

---

## MOC automatico

Al sincronizar, si la carpeta contenedora **no tiene ningun indice**, se crea uno
(`00 - Mapa del Proyecto.md` en Proyectos, `00 - Mapa del dominio.md` en Conocimiento).

El chequeo es por **prefijo `00 - `**, no por nombre exacto: los indices que ya existen
en el vault se llaman distinto segun la carpeta (`00 - Mapa del Ecosistema.md`,
`00 - Estado de tickets.md`). Chequear el nombre por default creaba un **segundo indice
compitiendo** con el que ya estaba.

Nunca se pisa un MOC existente.

---

## Frontmatter

Convencion del vault: **`tags` + `created`** (ISO `YYYY-MM-DD`). Los demas campos son
operativos del motor.

> El campo `date` se elimino el 2026-08-27: duplicaba a `created` y produjo el
> frontmatter inconsistente que hubo que normalizar a mano en el vault.
> `read-notes.js` y `refinement.py` leen `created` con fallback a `date` para las notas
> viejas.

---

## Ciclo de vida

1. El agente escribe en `.second-brain/` del proyecto (`sync_status: pending`)
2. El sync engine detecta los pendientes cada 15 min
3. Resuelve el destino con `vault-paths.js` y exporta (REST o filesystem)
4. Marca `synced` en local y **borra el `last_error` viejo**
5. El refinement engine consolida cada 3 dias
6. La deduplicacion detecta notas similares y crea cross-references

---

## Configuracion

1. Editar `config.json`: `obsidian.vault_path`, y los proyectos con su `vault_folder`
2. `npm install`
3. Probar sin escribir: `node src/sync-engine.js --dry-run`
4. Cron: `bash setup-cron.sh`
5. Webhook: `npm run webhook`
