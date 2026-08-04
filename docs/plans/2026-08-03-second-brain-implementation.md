# Second Brain Hibrido con Obsidian - Plan de Implementacion

> **Para agentes:** SUB-SKILL REQUERIDO: Usar compose:subagent o compose:execute para implementar este plan tarea por tarea. Los pasos usan checkbox (`- [ ]`) para tracking.

**Goal:** Construir un sistema de memoria persistente hibrida que captura aprendizajes, decisiones y contexto de multiples agentes (MiMoCode, OpenCode, n8n) en archivos locales versionables, con sync automatico a Obsidian y refinamiento periodico.

**Architecture:** Cada proyecto tiene su propio `.second-brain/` con notas en Markdown organizadas por tipo. Un sync engine cada 15 min exporta a Obsidian via REST API. Un refinement engine cada 3 dias consolida, deduplica y limpia notas de baja relevancia. La memoria local es la fuente de verdad; Obsidian es la capa de visualizacion.

**Tech Stack:** Node.js (sync engine), Python (refinement + deduplication), Shell scripts (hooks), Obsidian Local REST API (MCP), cron (scheduling).

## Global Constraints

- Todo el contenido en español (matching user language)
- Frontmatter YAML obligatorio en cada nota
- Naming: kebab-case para archivos, YYYY-MM-DD para fechas
- Encoding: UTF-8, line endings LF, indentacion 2 espacios
- Obsidian vault path: `D:\Documentos\Bovedas\Main\Second Brain\`
- Obsidian API: `https://127.0.0.1:27124` (HTTPS) o `http://127.0.0.1:27123` (HTTP)
- Sync interval: 15 minutos
- Refinement interval: 3 dias
- Un `.second-brain/` por proyecto

---

## Task 1: Estructura base del modulo second-brain

**Covers:** Arquitectura general, estructura de carpetas

**Files:**
- Create: `/home/keyz/.local/share/mimocode/second-brain/README.md`
- Create: `/home/keyz/.local/share/mimocode/second-brain/config.json`
- Create: `/home/keyz/.local/share/mimocode/second-brain/package.json`
- Create: `/home/keyz/.local/share/mimocode/second-brain/templates/frontmatter.json`

**Interfaces:**
- Produce: `config.json` schema con rutas de proyectos y Obsidian
- Produce: `frontmatter.json` template para nuevas notas

- [ ] **Step 1: Crear directorio base**

```bash
mkdir -p /home/keyz/.local/share/mimocode/second-brain/templates
```

- [ ] **Step 2: Crear config.json**

```json
{
  "obsidian": {
    "vault_path": "D:/Documentos/Bovedas/Main/Second Brain",
    "api_base_url": "https://127.0.0.1:27124",
    "api_key_env": "OBSIDIAN_API_KEY",
    "use_http_fallback": true,
    "http_url": "http://127.0.0.1:27123"
  },
  "sync": {
    "interval_minutes": 15,
    "retry_on_failure": true,
    "max_retries": 3
  },
  "refinement": {
    "interval_days": 3,
    "min_note_age_days": 7,
    "consolidate_threshold": 0.7
  },
  "projects": [
    {
      "name": "gentle-ai",
      "path": "/mnt/d/Projects/gentle-ai",
      "enabled": true
    }
  ],
  "agents": ["mimo", "opencode", "n8n", "manual"]
}
```

- [ ] **Step 3: Crear frontmatter.json template**

```json
{
  "decision": {
    "type": "decision",
    "agent": "",
    "project": "",
    "date": "",
    "tags": [],
    "created": "",
    "sync_status": "pending",
    "refined": false
  },
  "aprendizaje": {
    "type": "aprendizaje",
    "agent": "",
    "project": "",
    "date": "",
    "tags": [],
    "created": "",
    "sync_status": "pending",
    "refined": false
  },
  "convencion": {
    "type": "convencion",
    "agent": "",
    "project": "",
    "date": "",
    "tags": [],
    "created": "",
    "sync_status": "pending",
    "refined": false
  },
  "arquitectura": {
    "type": "arquitectura",
    "agent": "",
    "project": "",
    "date": "",
    "tags": [],
    "created": "",
    "sync_status": "pending",
    "refined": false
  },
  "session": {
    "type": "session",
    "agent": "",
    "project": "",
    "date": "",
    "tags": [],
    "created": "",
    "sync_status": "pending",
    "refined": false
  }
}
```

- [ ] **Step 4: Crear README.md del modulo**

```markdown
# Second Brain - Modulo de Memoria Persistente

Sistema de memoria hibrida que captura aprendizajes, decisiones y contexto
de multiples agentes en archivos locales versionables con sync a Obsidian.

## Estructura

- `config.json` - Configuracion global
- `src/` - Codigo fuente (sync engine, refinement, deduplication)
- `templates/` - Plantillas de frontmatter
- `hooks/` - Scripts de integracion con agentes

## Uso

Los agentes escriben en `.second-brain/` dentro de cada proyecto.
El sync engine exporta a Obsidian cada 15 minutos.
El refinement engine consolida cada 3 dias.
```

- [ ] **Step 5: Crear package.json**

```json
{
  "name": "second-brain",
  "version": "1.0.0",
  "description": "Sistema de memoria persistente hibrida con sync a Obsidian",
  "main": "src/sync-engine.js",
  "scripts": {
    "sync": "node src/sync-engine.js",
    "refine": "python3 src/refinement.py",
    "dedup": "python3 src/deduplication.js",
    "watch": "node src/file-watcher.js"
  },
  "dependencies": {
    "node-cron": "^3.0.3",
    "js-yaml": "^4.1.0"
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat(second-brain): estructura base del modulo"
```

---

## Task 2: CLI de escritura para agentes

**Covers:** Proceso de captura por agente

**Files:**
- Create: `/home/keyz/.local/share/mimocode/second-brain/src/write-note.js`
- Create: `/home/keyz/.local/share/mimocode/second-brain/hooks/mimo-hook.sh`
- Create: `/home/keyz/.local/share/mimocode/second-brain/hooks/opencode-hook.sh`

**Interfaces:**
- Consume: `config.json` (rutas de proyectos)
- Consume: `templates/frontmatter.json` (schema de frontmatter)
- Produce: `write-note.js` funcion `writeNote(project, type, title, content, agent)`

- [ ] **Step 1: Crear write-note.js**

```javascript
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const CONFIG_PATH = path.join(__dirname, '..', 'config.json');
const TEMPLATES_PATH = path.join(__dirname, '..', 'templates', 'frontmatter.json');

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

function loadTemplates() {
  return JSON.parse(fs.readFileSync(TEMPLATES_PATH, 'utf8'));
}

function generateFrontmatter(type, agent, project, tags = []) {
  const templates = loadTemplates();
  const template = templates[type] || templates['aprendizaje'];
  const now = new Date().toISOString();
  return {
    ...template,
    agent,
    project,
    date: now.split('T')[0],
    tags,
    created: now,
    sync_status: 'pending',
    refined: false
  };
}

function frontmatterToYaml(fm) {
  return '---\n' + yaml.dump(fm) + '---\n';
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function writeNote(projectName, type, title, content, agent, tags = []) {
  const config = loadConfig();
  const project = config.projects.find(p => p.name === projectName);
  
  if (!project) {
    // Si el proyecto no esta registrado, usar ruta por defecto
    const projectPath = path.join('/mnt/d/Projects', projectName);
    return writeNoteToPath(projectPath, type, title, content, agent, tags);
  }
  
  return writeNoteToPath(project.path, type, title, content, agent, tags);
}

function writeNoteToPath(projectPath, type, title, content, agent, tags) {
  const sbDir = path.join(projectPath, '.second-brain');
  
  if (type === 'session') {
    const today = new Date().toISOString().split('T')[0];
    const filePath = path.join(sbDir, 'diario', `${today}.md`);
    ensureDir(path.dirname(filePath));
    
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
    const sessionEntry = `\n## [${timestamp}] ${title}\n\nAgente: ${agent}\n\n${content}\n`;
    
    if (fs.existsSync(filePath)) {
      fs.appendFileSync(filePath, sessionEntry, 'utf8');
    } else {
      const fm = generateFrontmatter('session', agent, path.basename(projectPath), tags);
      fs.writeFileSync(filePath, frontmatterToYaml(fm) + `# Sesion ${today}\n${sessionEntry}`, 'utf8');
    }
    
    return filePath;
  } else {
    const slug = slugify(title);
    const filePath = path.join(sbDir, type, `${slug}.md`);
    ensureDir(path.dirname(filePath));
    
    const fm = generateFrontmatter(type, agent, path.basename(projectPath), tags);
    const body = frontmatterToYaml(fm) + `# ${title}\n\n${content}\n`;
    
    fs.writeFileSync(filePath, body, 'utf8');
    return filePath;
  }
}

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2);
  const [projectName, type, title, agent, ...contentParts] = args;
  const content = contentParts.join(' ');
  
  if (!projectName || !type || !title || !agent) {
    console.error('Uso: node write-note.js <project> <type> <title> <agent> <content>');
    console.error('Tipos: session, decisiones, aprendizajes, convenciones, arquitectura');
    process.exit(1);
  }
  
  const filePath = writeNote(projectName, type, title, content, agent);
  console.log(`Nota escrita: ${filePath}`);
}

module.exports = { writeNote, generateFrontmatter };
```

- [ ] **Step 2: Crear hook para MiMoCode (mimo-hook.sh)**

```bash
#!/bin/bash
# Hook para MiMoCode - Escribe al second-brain tras cada sesion significativa
# Uso: ./mimo-hook.sh <project> <type> <title> <content>

PROJECT="$1"
TYPE="$2"
TITLE="$3"
shift 3
CONTENT="$*"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NODE_SCRIPT="$SCRIPT_DIR/../src/write-note.js"

node "$NODE_SCRIPT" "$PROJECT" "$TYPE" "$TITLE" "mimo" "$CONTENT"
```

- [ ] **Step 3: Crear hook para OpenCode (opencode-hook.sh)**

```bash
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
```

- [ ] **Step 4: Dar permisos de ejecucion**

```bash
chmod +x /home/keyz/.local/share/mimocode/second-brain/hooks/mimo-hook.sh
chmod +x /home/keyz/.local/share/mimocode/second-brain/hooks/opencode-hook.sh
```

- [ ] **Step 5: Test - Escribir una nota de prueba**

```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  gentle-ai aprendizajes "test-learning" "mimo" "Esta es una nota de prueba"
```

Expected: `Nota escrita: /mnt/d/Projects/gentle-ai/.second-brain/aprendizajes/test-learning.md`

- [ ] **Step 6: Verificar contenido de la nota**

```bash
cat /mnt/d/Projects/gentle-ai/.second-brain/aprendizajes/test-learning.md
```

Expected: Frontmatter YAML con type, agent, project, date, tags, created, sync_status, refined + contenido

- [ ] **Step 7: Limpiar nota de prueba**

```bash
rm /mnt/d/Projects/gentle-ai/.second-brain/aprendizajes/test-learning.md
```

- [ ] **Step 8: Commit**

```bash
git add /home/keyz/.local/share/mimocode/second-brain/
git commit -m "feat(second-brain): CLI de escritura para agentes"
```

---

## Task 3: Sync Engine (Local -> Obsidian)

**Covers:** Proceso de sync cada 15 minutos

**Files:**
- Create: `/home/keyz/.local/share/mimocode/second-brain/src/sync-engine.js`
- Create: `/home/keyz/.local/share/mimocode/second-brain/src/obsidian-client.js`

**Interfaces:**
- Consume: `config.json` (Obsidian API config)
- Consume: `writeNote` de Task 2 (mismo formato de archivos)
- Produce: `obsidian-client.js` con funciones `patchNote`, `writeNote`, `appendNote`

- [ ] **Step 1: Crear obsidian-client.js**

```javascript
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, '..', 'config.json');

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

function getApiKey() {
  return process.env[loadConfig().obsidian.api_key_env];
}

function makeRequest(method, apiPath, body = null, isHttps = true) {
  return new Promise((resolve, reject) => {
    const config = loadConfig().obsidian;
    const baseUrl = isHttps ? config.api_base_url : config.http_url;
    const url = new URL(apiPath, baseUrl);
    
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      method: method,
      headers: {
        'Authorization': `Bearer ${getApiKey()}`,
        'Content-Type': 'application/json'
      },
      rejectUnauthorized: false
    };
    
    if (body) {
      options.headers['Content-Length'] = Buffer.byteLength(JSON.stringify(body));
    }
    
    const protocol = isHttps ? https : http;
    const req = protocol.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve(data ? JSON.parse(data) : {});
          } catch {
            resolve(data);
          }
        } else if (res.statusCode === 404 && isHttps && config.use_http_fallback) {
          // Fallback a HTTP
          makeRequest(method, apiPath, body, false).then(resolve).catch(reject);
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        }
      });
    });
    
    req.on('error', (err) => {
      if (isHttps && config.use_http_fallback) {
        makeRequest(method, apiPath, body, false).then(resolve).catch(reject);
      } else {
        reject(err);
      }
    });
    
    if (body) {
      req.write(JSON.stringify(body));
    }
    req.end();
  });
}

async function vaultList(dirPath = '') {
  return makeRequest('GET', `/vault/${dirPath}`);
}

async function vaultRead(filePath) {
  return makeRequest('GET', `/vault/${filePath}`);
}

async function vaultWrite(filePath, content) {
  return makeRequest('PUT', `/vault/${filePath}`, content);
}

async function vaultAppend(filePath, content) {
  return makeRequest('POST', `/vault/${filePath}`, content);
}

async function vaultPatch(filePath, patchInstruction) {
  return makeRequest('PATCH', `/vault/${filePath}`, patchInstruction);
}

async function vaultDelete(filePath) {
  return makeRequest('DELETE', `/vault/${filePath}`);
}

async function searchSimple(query) {
  return makeRequest('POST', `/search/simple/?query=${encodeURIComponent(query)}`);
}

async function tagList() {
  return makeRequest('GET', '/tags/');
}

module.exports = {
  vaultList,
  vaultRead,
  vaultWrite,
  vaultAppend,
  vaultPatch,
  vaultDelete,
  searchSimple,
  tagList,
  makeRequest
};
```

- [ ] **Step 2: Crear sync-engine.js**

```javascript
const fs = require('fs');
const path = require('path');
const cron = require('node-cron');
const obsidian = require('./obsidian-client');

const CONFIG_PATH = path.join(__dirname, '..', 'config.json');
const SECOND_BRAIN_DIR = '.second-brain';
const OBSIDIAN_TARGET_DIR = 'Second Brain';

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

function readFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return {};
  try {
    const yaml = require('js-yaml');
    return yaml.load(match[1]) || {};
  } catch {
    return {};
  }
}

function updateFrontmatter(content, updates) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return content;
  
  const yaml = require('js-yaml');
  const fm = yaml.load(match[1]) || {};
  Object.assign(fm, updates);
  
  const newFm = '---\n' + yaml.dump(fm) + '---';
  return content.replace(/^---\n[\s\S]*?\n---/, newFm);
}

function getLocalNotes(projectPath) {
  const sbDir = path.join(projectPath, SECOND_BRAIN_DIR);
  if (!fs.existsSync(sbDir)) return [];
  
  const notes = [];
  const categories = ['diario', 'decisiones', 'aprendizajes', 'convenciones', 'arquitectura'];
  
  for (const category of categories) {
    const catDir = path.join(sbDir, category);
    if (!fs.existsSync(catDir)) continue;
    
    const files = fs.readdirSync(catDir).filter(f => f.endsWith('.md'));
    for (const file of files) {
      const filePath = path.join(catDir, file);
      const content = fs.readFileSync(filePath, 'utf8');
      const fm = readFrontmatter(content);
      
      if (fm.sync_status === 'pending' || fm.sync_status === 'error') {
        notes.push({
          filePath,
          category,
          filename: file,
          content,
          frontmatter: fm
        });
      }
    }
  }
  
  return notes;
}

async function syncNote(projectName, note) {
  const config = loadConfig();
  const targetDir = `${OBSIDIAN_TARGET_DIR}/${note.category.charAt(0).toUpperCase() + note.category.slice(1)}`;
  
  if (note.category === 'diario') {
    // Para diarios: append al archivo del dia
    const targetPath = `${targetDir}/${note.filename}`;
    try {
      // Intentar leer el archivo existente
      let existing = '';
      try {
        existing = await obsidian.vaultRead(targetPath);
      } catch {
        // No existe, se creara
      }
      
      if (existing) {
        // Extraer solo el contenido nuevo (sin frontmatter)
        const bodyMatch = note.content.match(/^---\n[\s\S]*?\n---\n([\s\S]*)/);
        const body = bodyMatch ? bodyMatch[1] : note.content;
        
        await obsidian.vaultPatch(targetPath, {
          targetType: 'heading',
          target: [note.filename.replace('.md', '')],
          operation: 'append',
          content: body
        });
      } else {
        // Crear archivo nuevo
        await obsidian.vaultWrite(targetPath, note.content);
      }
    } catch (err) {
      throw new Error(`Sync diario fallo: ${err.message}`);
    }
  } else {
    // Para permanentes: PUT/POST
    const targetPath = `${targetDir}/${note.filename}`;
    try {
      await obsidian.vaultWrite(targetPath, note.content);
    } catch (err) {
      throw new Error(`Sync permanente fallo: ${err.message}`);
    }
  }
}

async function markAsSynced(notePath) {
  const content = fs.readFileSync(notePath, 'utf8');
  const updated = updateFrontmatter(content, { sync_status: 'synced' });
  fs.writeFileSync(notePath, updated, 'utf8');
}

async function markAsError(notePath, errorMsg) {
  const content = fs.readFileSync(notePath, 'utf8');
  const updated = updateFrontmatter(content, { sync_status: 'error', last_error: errorMsg });
  fs.writeFileSync(notePath, updated, 'utf8');
}

async function runSync() {
  const config = loadConfig();
  console.log(`[${new Date().toISOString()}] Iniciando sync...`);
  
  for (const project of config.projects) {
    if (!project.enabled) continue;
    
    const notes = getLocalNotes(project.path);
    console.log(`  Proyecto "${project.name}": ${notes.length} notas pendientes`);
    
    for (const note of notes) {
      try {
        await syncNote(project.name, note);
        await markAsSynced(note.filePath);
        console.log(`    OK: ${note.category}/${note.filename}`);
      } catch (err) {
        await markAsError(note.filePath, err.message);
        console.log(`    ERROR: ${note.category}/${note.filename} - ${err.message}`);
      }
    }
  }
  
  console.log(`[${new Date().toISOString()}] Sync completado.`);
}

// CLI
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.includes('--daemon')) {
    // Modo daemon con cron
    const config = loadConfig();
    const interval = config.sync.interval_minutes;
    const cronExpr = `*/${interval} * * * *`;
    
    console.log(`Iniciando daemon de sync (cada ${interval} minutos)...`);
    cron.schedule(cronExpr, runSync);
  } else {
    // Ejecucion unica
    runSync().catch(console.error);
  }
}

module.exports = { runSync, getLocalNotes, syncNote };
```

- [ ] **Step 3: Test - Verificar conexion con Obsidian**

```bash
node -e "
const obsidian = require('/home/keyz/.local/share/mimocode/second-brain/src/obsidian-client');
obsidian.vaultList('').then(r => console.log('Conectado:', JSON.stringify(r).slice(0, 200))).catch(e => console.error('Error:', e.message));
"
```

Expected: Lista de archivos del vault o error si Obsidian no esta corriendo

- [ ] **Step 4: Commit**

```bash
git add /home/keyz/.local/share/mimocode/second-brain/src/
git commit -m "feat(second-brain): sync engine con obsidian client"
```

---

## Task 4: Refinement Engine (cada 3 dias)

**Covers:** Proceso de refinamiento cada 3 dias

**Files:**
- Create: `/home/keyz/.local/share/mimocode/second-brain/src/refinement.py`
- Create: `/home/keyz/.local/share/mimocode/second-brain/src/deduplication.py`

**Interfaces:**
- Consume: notas locales con `sync_status: synced` y `refined: false`
- Produce: notas consolidadas y deduplicadas

- [ ] **Step 1: Crear refinement.py**

```python
#!/usr/bin/env python3
"""
Refinement Engine - Consolida y limpia notas cada 3 dias.
Identifica notas de baja relevancia, extrae puntos clave y archiva.
"""

import os
import sys
import json
import yaml
import re
from datetime import datetime, timedelta
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"
SECOND_BRAIN_DIR = ".second-brain"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def read_frontmatter(content):
    match = re.match(r'^---\n([\s\S]*?)\n---', content)
    if not match:
        return {}, content
    try:
        fm = yaml.safe_load(match.group(1)) or {}
        body = content[match.end():]
        return fm, body
    except:
        return {}, content

def write_frontmatter(fm):
    return '---\n' + yaml.dump(fm, allow_unicode=True, default_flow_style=False) + '---\n'

def get_all_notes(project_path):
    sb_dir = Path(project_path) / SECOND_BRAIN_DIR
    if not sb_dir.exists():
        return []
    
    notes = []
    categories = ['diario', 'decisiones', 'aprendizajes', 'convenciones', 'arquitectura']
    
    for category in categories:
        cat_dir = sb_dir / category
        if not cat_dir.exists():
            continue
        
        for md_file in cat_dir.glob('*.md'):
            content = md_file.read_text(encoding='utf-8')
            fm, body = read_frontmatter(content)
            
            notes.append({
                'path': str(md_file),
                'category': category,
                'filename': md_file.name,
                'frontmatter': fm,
                'body': body,
                'content': content
            })
    
    return notes

def calculate_relevance_score(note):
    """Calcula un score de relevancia basado en multiples factores."""
    score = 0.5  # Base
    
    # Tags = mas relevante
    tags = note['frontmatter'].get('tags', [])
    score += min(len(tags) * 0.1, 0.3)
    
    # Notas con contenido sustancial
    body_length = len(note['body'].strip())
    if body_length > 200:
        score += 0.1
    if body_length > 500:
        score += 0.1
    
    # Notas de decisiones y arquitectura son mas relevantes
    if note['category'] in ['decisiones', 'arquitectura']:
        score += 0.2
    
    # Notas recientes son mas relevantes
    created = note['frontmatter'].get('created', '')
    if created:
        try:
            created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
            age_days = (datetime.now() - created_date.replace(tzinfo=None)).days
            if age_days < 7:
                score += 0.1
            elif age_days > 30:
                score -= 0.2
        except:
            pass
    
    return min(max(score, 0.0), 1.0)

def should_refine(note, min_age_days):
    """Determina si una nota debe ser refinada."""
    created = note['frontmatter'].get('created', '')
    if not created:
        return False
    
    try:
        created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
        age_days = (datetime.now() - created_date.replace(tzinfo=None)).days
        return age_days >= min_age_days
    except:
        return False

def consolidate_daily_notes(notes):
    """Consolida notas diarias en resumenes semanales."""
    diario_notes = [n for n in notes if n['category'] == 'diario']
    if len(diario_notes) < 3:
        return notes
    
    # Agrupar por semana
    weeks = {}
    for note in diario_notes:
        date_str = note['frontmatter'].get('date', '')
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                week_key = date.strftime('%Y-W%W')
                if week_key not in weeks:
                    weeks[week_key] = []
                weeks[week_key].append(note)
            except:
                pass
    
    # Consolidar semanas con muchas notas
    consolidated = []
    for week_key, week_notes in weeks.items():
        if len(week_notes) >= 3:
            # Crear resumen consolidado
            summary_content = f"# Resumen Semanal {week_key}\n\n"
            for note in sorted(week_notes, key=lambda n: n['frontmatter'].get('date', '')):
                summary_content += f"\n---\n\n{note['body']}\n"
            
            # Marcar notas originales como refined
            for note in week_notes:
                note['frontmatter']['refined'] = True
                note['frontmatter']['consolidated_into'] = f"semanal-{week_key}"
                Path(note['path']).write_text(
                    write_frontmatter(note['frontmatter']) + note['body'],
                    encoding='utf-8'
                )
            
            # Crear archivo consolidado
            summary_path = Path(week_notes[0]['path']).parent / f"semanal-{week_key}.md"
            summary_fm = {
                'type': 'session',
                'agent': 'refinement-engine',
                'project': week_notes[0]['frontmatter'].get('project', ''),
                'date': week_notes[0]['frontmatter'].get('date', ''),
                'tags': ['consolidado', 'semanal'],
                'created': datetime.now().isoformat(),
                'sync_status': 'pending',
                'refined': True
            }
            summary_path.write_text(
                write_frontmatter(summary_fm) + summary_content,
                encoding='utf-8'
            )
            print(f"  Consolidado: semanal-{week_key}.md ({len(week_notes)} notas)")
        else:
            consolidated.extend(week_notes)
    
    return [n for n in notes if n['category'] != 'diario'] + consolidated

def run_refinement():
    config = load_config()
    min_age = config['refinement']['min_note_age_days']
    
    print(f"[{datetime.now().isoformat()}] Iniciando refinamiento...")
    
    for project in config['projects']:
        if not project.get('enabled', True):
            continue
        
        print(f"\nProyecto: {project['name']}")
        notes = get_all_notes(project['path'])
        
        # Filtrar notas que deben ser refinadas
        to_refine = [n for n in notes if should_refine(n, min_age)]
        print(f"  Notas a evaluar: {len(to_refine)}")
        
        # Calcular relevancia
        low_relevance = []
        high_relevance = []
        
        for note in to_refine:
            score = calculate_relevance_score(note)
            if score < config['refinement']['consolidate_threshold']:
                low_relevance.append(note)
            else:
                high_relevance.append(note)
        
        print(f"  Baja relevancia: {len(low_relevance)}")
        print(f"  Alta relevancia: {len(high_relevance)}")
        
        # Consolidar notas diarias
        remaining = consolidate_daily_notes([n for n in notes if n['category'] == 'diario'])
        
        # Marcar notas de baja relevancia como refined
        for note in low_relevance:
            note['frontmatter']['refined'] = True
            note['frontmatter']['refined_at'] = datetime.now().isoformat()
            note['frontmatter']['relevance_score'] = calculate_relevance_score(note)
            Path(note['path']).write_text(
                write_frontmatter(note['frontmatter']) + note['body'],
                encoding='utf-8'
            )
    
    print(f"\n[{datetime.now().isoformat()}] Refinamiento completado.")

if __name__ == '__main__':
    run_refinement()
```

- [ ] **Step 2: Crear deduplication.py**

```python
#!/usr/bin/env python3
"""
Deduplication Engine - Detecta y mergea notas similares.
Si dos aprendizajes tratan el mismo tema pero en contextos diferentes,
se guardan ambos con cross-references.
"""

import os
import sys
import json
import yaml
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

CONFIG_PATH = Path(__file__).parent.parent / "config.json"
SECOND_BRAIN_DIR = ".second-brain"

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def read_frontmatter(content):
    match = re.match(r'^---\n([\s\S]*?)\n---', content)
    if not match:
        return {}, content
    try:
        fm = yaml.safe_load(match.group(1)) or {}
        body = content[match.end():]
        return fm, body
    except:
        return {}, content

def write_frontmatter(fm):
    return '---\n' + yaml.dump(fm, allow_unicode=True, default_flow_style=False) + '---\n'

def extract_tags(frontmatter):
    return set(frontmatter.get('tags', []))

def jaccard_similarity(set_a, set_b):
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0

def find_similar_notes(notes, threshold=0.5):
    """Encuentra pares de notas similares basado en tags."""
    similar_pairs = []
    
    aprendizajes = [n for n in notes if n['category'] == 'aprendizajes']
    
    for i, note_a in enumerate(aprendizajes):
        for note_b in aprendizajes[i+1:]:
            tags_a = extract_tags(note_a['frontmatter'])
            tags_b = extract_tags(note_b['frontmatter'])
            
            similarity = jaccard_similarity(tags_a, tags_b)
            
            if similarity >= threshold:
                similar_pairs.append((note_a, note_b, similarity))
    
    return similar_pairs

def merge_or_cross_reference(note_a, note_b, similarity):
    """Decide si mergear o crear cross-references."""
    # Si son del mismo proyecto, mergear
    if note_a['frontmatter'].get('project') == note_b['frontmatter'].get('project'):
        return 'merge'
    
    # Si son de proyectos diferentes pero tema similar, cross-reference
    return 'cross-reference'

def add_cross_reference(note, other_note, other_path):
    """Agrega cross-reference a una nota."""
    ref_text = f"\n\n**Ver tambien:** [{other_note['filename'].replace('.md', '')}]({other_path})"
    
    if 'cross_references' not in note['frontmatter']:
        note['frontmatter']['cross_references'] = []
    
    note['frontmatter']['cross_references'].append({
        'file': other_note['filename'],
        'project': other_note['frontmatter'].get('project', '')
    })
    
    # Agregar referencia al body si no existe ya
    if ref_text not in note['body']:
        note['body'] += ref_text
    
    note['frontmatter']['sync_status'] = 'pending'
    note['frontmatter']['refined'] = True

def run_deduplication():
    config = load_config()
    
    print(f"[{datetime.now().isoformat()}] Iniciando deduplicacion...")
    
    all_notes = []
    for project in config['projects']:
        if not project.get('enabled', True):
            continue
        
        sb_dir = Path(project['path']) / SECOND_BRAIN_DIR
        if not sb_dir.exists():
            continue
        
        categories = ['decisiones', 'aprendizajes', 'convenciones', 'arquitectura']
        for category in categories:
            cat_dir = sb_dir / category
            if not cat_dir.exists():
                continue
            
            for md_file in cat_dir.glob('*.md'):
                content = md_file.read_text(encoding='utf-8')
                fm, body = read_frontmatter(content)
                
                all_notes.append({
                    'path': str(md_file),
                    'category': category,
                    'filename': md_file.name,
                    'frontmatter': fm,
                    'body': body,
                    'content': content
                })
    
    similar_pairs = find_similar_notes(all_notes)
    print(f"  Pares similares encontrados: {len(similar_pairs)}")
    
    for note_a, note_b, sim in similar_pairs:
        action = merge_or_cross_reference(note_a, note_b, sim)
        
        if action == 'cross-reference':
            add_cross_reference(note_a, note_b, note_b['path'])
            add_cross_reference(note_b, note_a, note_a['path'])
            
            # Guardar cambios
            Path(note_a['path']).write_text(
                write_frontmatter(note_a['frontmatter']) + note_a['body'],
                encoding='utf-8'
            )
            Path(note_b['path']).write_text(
                write_frontmatter(note_b['frontmatter']) + note_b['body'],
                encoding='utf-8'
            )
            
            print(f"  Cross-ref: {note_a['filename']} <-> {note_b['filename']} (sim={sim:.2f})")
    
    print(f"[{datetime.now().isoformat()}] Deduplicacion completada.")

if __name__ == '__main__':
    run_deduplication()
```

- [ ] **Step 3: Dar permisos de ejecucion**

```bash
chmod +x /home/keyz/.local/share/mimocode/second-brain/src/refinement.py
chmod +x /home/keyz/.local/share/mimocode/second-brain/src/deduplication.py
```

- [ ] **Step 4: Test - Ejecutar refinement en seco**

```bash
python3 /home/keyz/.local/share/mimocode/second-brain/src/refinement.py
```

Expected: Output del proceso de refinamiento

- [ ] **Step 5: Commit**

```bash
git add /home/keyz/.local/share/mimocode/second-brain/src/
git commit -m "feat(second-brain): refinement y deduplication engines"
```

---

## Task 5: Integracion con n8n (webhook receiver)

**Covers:** Proceso de captura por agente (n8n)

**Files:**
- Create: `/home/keyz/.local/share/mimocode/second-brain/src/webhook-server.js`

**Interfaces:**
- Consume: `writeNote` de Task 2
- Produce: HTTP server que recibe eventos de n8n

- [ ] **Step 1: Crear webhook-server.js**

```javascript
const http = require('http');
const url = require('url');
const { writeNote } = require('./write-note');

const PORT = 9876;

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        resolve(JSON.parse(body));
      } catch {
        reject(new Error('Invalid JSON'));
      }
    });
  });
}

const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  if (parsedUrl.pathname === '/webhook/learning' && req.method === 'POST') {
    try {
      const data = await parseBody(req);
      const { project, type, title, content, agent, tags } = data;
      
      if (!project || !type || !title) {
        res.writeHead(400);
        res.end(JSON.stringify({ error: 'Missing required fields: project, type, title' }));
        return;
      }
      
      const filePath = writeNote(project, type, title, content || '', agent || 'n8n', tags || []);
      
      res.writeHead(201);
      res.end(JSON.stringify({ success: true, path: filePath }));
    } catch (err) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: err.message }));
    }
  } else if (parsedUrl.pathname === '/health' && req.method === 'GET') {
    res.writeHead(200);
    res.end(JSON.stringify({ status: 'ok', timestamp: new Date().toISOString() }));
  } else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

if (require.main === module) {
  server.listen(PORT, () => {
    console.log(`Second Brain webhook server corriendo en http://localhost:${PORT}`);
    console.log(`  POST /webhook/learning - Recibe aprendizajes de n8n`);
    console.log(`  GET  /health           - Health check`);
  });
}

module.exports = { server };
```

- [ ] **Step 2: Test - Iniciar servidor y enviar evento**

```bash
# Terminal 1: Iniciar servidor
node /home/keyz/.local/share/mimocode/second-brain/src/webhook-server.js &

# Terminal 2: Enviar evento de prueba
curl -X POST http://localhost:9876/webhook/learning \
  -H "Content-Type: application/json" \
  -d '{"project":"gentle-ai","type":"aprendizajes","title":"n8n-test","content":"Test desde n8n","tags":["test"]}'

# Verificar respuesta
```

Expected: `{"success":true,"path":"..."}`

- [ ] **Step 3: Limpiar nota de prueba**

```bash
rm /mnt/d/Projects/gentle-ai/.second-brain/aprendizajes/n8n-test.md 2>/dev/null
kill %1 2>/dev/null
```

- [ ] **Step 4: Commit**

```bash
git add /home/keyz/.local/share/mimocode/second-brain/src/webhook-server.js
git commit -m "feat(second-brain): webhook server para integracion con n8n"
```

---

## Task 6: Configuracion de cron jobs

**Covers:** Sync cada 15 min, refinement cada 3 dias

**Files:**
- Create: `/home/keyz/.local/share/mimocode/second-brain/setup-cron.sh`
- Modify: crontab del sistema

**Interfaces:**
- Consume: `sync-engine.js` de Task 3
- Consume: `refinement.py` y `deduplication.py` de Task 4

- [ ] **Step 1: Crear setup-cron.sh**

```bash
#!/bin/bash
# Setup de cron jobs para Second Brain
# Ejecutar una vez: ./setup-cron.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/src/sync-engine.js"
REFINE_SCRIPT="$SCRIPT_DIR/src/refinement.py"
DEDUP_SCRIPT="$SCRIPT_DIR/src/deduplication.py"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"

# Crear entries de cron
CRON_SYNC="*/15 * * * * cd $SCRIPT_DIR && node $SYNC_SCRIPT >> $LOG_DIR/sync.log 2>&1"
CRON_REFINE="0 2 */3 * * cd $SCRIPT_DIR && python3 $REFINE_SCRIPT >> $LOG_DIR/refinement.log 2>&1"
CRON_DEDUP="30 2 */3 * * cd $SCRIPT_DIR && python3 $DEDUP_SCRIPT >> $LOG_DIR/dedup.log 2>&1"

# Agregar al crontab (evitando duplicados)
(crontab -l 2>/dev/null | grep -v "second-brain"; echo "$CRON_SYNC") | sort -u | crontab -
(crontab -l 2>/dev/null | grep -v "second-brain"; echo "$CRON_REFINE") | sort -u | crontab -
(crontab -l 2>/dev/null | grep -v "second-brain"; echo "$CRON_DEDUP") | sort -u | crontab -

echo "Cron jobs configurados:"
echo "  - Sync: cada 15 minutos"
echo "  - Refinement: cada 3 dias a las 2:00 AM"
echo "  - Deduplicacion: cada 3 dias a las 2:30 AM"
echo ""
echo "Para verificar: crontab -l"
```

- [ ] **Step 2: Dar permisos**

```bash
chmod +x /home/keyz/.local/share/mimocode/second-brain/setup-cron.sh
```

- [ ] **Step 3: Commit**

```bash
git add /home/keyz/.local/share/mimocode/second-brain/setup-cron.sh
git commit -m "feat(second-brain): configuracion de cron jobs"
```

---

## Task 7: Integracion con MiMoCode Memory System

**Covers:** Proceso de captura por agente (MiMoCode)

**Files:**
- Create: `/home/keyz/.local/share/mimocode/second-brain/hooks/mimo-memory-bridge.md`
- Modify: `/home/keyz/.local/share/mimocode/memory/projects/global/MEMORY.md`

**Interfaces:**
- Consume: `write-note.js` de Task 2
- Produce: Instrucciones para que MiMoCode escriba en `.second-brain/`

- [ ] **Step 1: Crear mimo-memory-bridge.md**

```markdown
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
```

- [ ] **Step 2: Agregar referencia en MEMORY.md global**

```bash
# Leer MEMORY.md actual
cat /home/keyz/.local/share/mimocode/memory/projects/global/MEMORY.md
```

Luego agregar la seccion:

```markdown
## Second Brain Integration

Este proyecto usa un sistema de memoria persistente hibrida.
- Modulo: `/home/keyz/.local/share/mimocode/second-brain/`
- Docs: `hooks/mimo-memory-bridge.md`
- Los aprendizajes se escriben en `.second-brain/` de cada proyecto
- Sync automatico a Obsidian cada 15 minutos
- Refinamiento cada 3 dias
```

- [ ] **Step 3: Commit**

```bash
git add /home/keyz/.local/share/mimocode/second-brain/hooks/
git add /home/keyz/.local/share/mimocode/memory/projects/global/MEMORY.md
git commit -m "feat(second-brain): integracion con MiMoCode memory system"
```

---

## Spec Coverage

| Spec Section | Task(s) |
|-------------|---------|
| Arquitectura general | Task 1, 3 |
| Estructura de carpetas | Task 1, 2 |
| Proceso de captura | Task 2, 5, 7 |
| Sync cada 15 min | Task 3, 6 |
| Refinamiento cada 3 dias | Task 4, 6 |
| Deduplicacion | Task 4 |
| Frontmatter estandar | Task 1, 2 |
