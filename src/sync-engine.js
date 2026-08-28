/**
 * sync-engine.js — Exporta las notas locales de `.second-brain/` al vault de Obsidian.
 *
 * El routing NO vive aca: lo resuelve `vault-paths.js` desde `config.json`.
 * Antes este archivo tenia `OBSIDIAN_TARGET_DIR = 'Second Brain'` hardcodeado,
 * que apuntaba a una carpeta que ya no existe en el vault.
 */

const fs = require('fs');
const path = require('path');
const obsidian = require('./obsidian-client');
const vaultPaths = require('./vault-paths');

const SECOND_BRAIN_DIR = '.second-brain';
const CATEGORIES = ['diario', 'decisiones', 'aprendizajes', 'convenciones', 'arquitectura'];

function loadConfig() {
  return vaultPaths.loadConfig();
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

  // Un sync exitoso borra el error viejo; si no, queda pegado para siempre
  // y confunde al que lea la nota en Obsidian.
  if (updates.sync_status === 'synced') delete fm.last_error;

  const newFm = '---\n' + yaml.dump(fm) + '---';
  return content.replace(/^---\n[\s\S]*?\n---/, newFm);
}

function stripFrontmatter(content) {
  const m = content.match(/^---\n[\s\S]*?\n---\n([\s\S]*)/);
  return m ? m[1] : content;
}

function getLocalNotes(projectPath) {
  const sbDir = path.join(projectPath, SECOND_BRAIN_DIR);
  if (!fs.existsSync(sbDir)) return [];

  const notes = [];

  for (const category of CATEGORIES) {
    const catDir = path.join(sbDir, category);
    if (!fs.existsSync(catDir)) continue;

    for (const file of fs.readdirSync(catDir).filter(f => f.endsWith('.md'))) {
      const filePath = path.join(catDir, file);
      const content = fs.readFileSync(filePath, 'utf8');
      const fm = readFrontmatter(content);

      if (fm.sync_status === 'pending' || fm.sync_status === 'error') {
        notes.push({ filePath, category, filename: file, content, frontmatter: fm });
      }
    }
  }

  return notes;
}

/**
 * Crea el MOC de la carpeta contenedora si NO hay ninguno.
 *
 * No alcanza con chequear el nombre exacto: en el vault los MOC existentes se
 * llaman distinto segun la carpeta (`00 - Mapa del Ecosistema.md`,
 * `00 - Estado de tickets.md`, `00 - Mapa del dominio.md`). Chequear solo el
 * nombre por default crea un segundo indice que compite con el que ya estaba.
 * La convencion del vault es que el indice de una carpeta es cualquier `00 - *`.
 */
async function ensureMoc(projectName, category, config) {
  if (!config.vault.moc || !config.vault.moc.auto_create) return null;

  const mocPath = vaultPaths.resolveMocPath(projectName, category, config);
  const containerDir = mocPath.split('/').slice(0, -1).join('/');

  const existing = await obsidian.noteListDir(containerDir);
  if (existing.some(f => f.startsWith('00 - '))) return null;

  await obsidian.noteWrite(mocPath, vaultPaths.buildMocContent(projectName, category, config));
  return mocPath;
}

async function syncNote(projectName, note, config) {
  const target = vaultPaths.resolveTarget(projectName, note.category, note.filename, config);

  // La copia del vault se marca `synced` de entrada: la fuente de verdad del
  // estado es el archivo local, y una nota que dice `pending` dentro de Obsidian
  // es ruido que confunde a quien la lee ahi.
  const exported = updateFrontmatter(note.content, { sync_status: 'synced' });

  if (note.category === 'diario') {
    // El diario es acumulativo: si la nota del dia ya existe en el vault,
    // se le appendea el cuerpo en vez de reemplazarla.
    const existing = await obsidian.noteRead(target.path);
    if (existing) {
      await obsidian.noteAppend(target.path, '\n' + stripFrontmatter(exported).trim() + '\n');
    } else {
      await obsidian.noteWrite(target.path, exported);
    }
  } else {
    await obsidian.noteWrite(target.path, exported);
  }

  return target;
}

function markAsSynced(notePath) {
  const content = fs.readFileSync(notePath, 'utf8');
  fs.writeFileSync(notePath, updateFrontmatter(content, { sync_status: 'synced' }), 'utf8');
}

function markAsError(notePath, errorMsg) {
  const content = fs.readFileSync(notePath, 'utf8');
  fs.writeFileSync(
    notePath,
    updateFrontmatter(content, { sync_status: 'error', last_error: errorMsg }),
    'utf8'
  );
}

async function runSync({ dryRun = false } = {}) {
  const config = loadConfig();
  const stamp = new Date().toISOString();
  console.log(`[${stamp}] Iniciando sync${dryRun ? ' (DRY RUN — no escribe nada)' : ''}...`);
  console.log(`  Vault: ${config.obsidian.vault_path}  ·  write_mode: ${obsidian.writeMode()}`);

  let ok = 0;
  let failed = 0;
  let pending = 0;

  for (const project of config.projects) {
    if (!project.enabled) continue;

    const notes = getLocalNotes(project.path);
    if (notes.length === 0) continue;

    pending += notes.length;
    console.log(`\n  ${project.name} → ${project.vault_folder}: ${notes.length} pendiente(s)`);

    for (const note of notes) {
      const target = vaultPaths.resolveTarget(project.name, note.category, note.filename, config);

      if (dryRun) {
        console.log(`    [${target.area}] ${note.category}/${note.filename}`);
        console.log(`        → ${target.path}`);
        continue;
      }

      try {
        const moc = await ensureMoc(project.name, note.category, config);
        if (moc) console.log(`    MOC creado: ${moc}`);

        await syncNote(project.name, note, config);
        markAsSynced(note.filePath);
        ok++;
        console.log(`    OK  → ${target.path}`);
      } catch (err) {
        markAsError(note.filePath, err.message);
        failed++;
        console.log(`    ERR → ${target.path}\n         ${err.message}`);
      }
    }
  }

  if (pending === 0) {
    console.log('\n  Nada pendiente.');
  } else if (!dryRun) {
    console.log(`\n[${new Date().toISOString()}] Sync completado: ${ok} ok, ${failed} con error.`);
  }

  return { ok, failed, pending };
}

if (require.main === module) {
  const args = process.argv.slice(2);

  if (args.includes('--daemon')) {
    const config = loadConfig();
    const interval = config.sync.interval_minutes;
    const cron = require('node-cron');
    console.log(`Iniciando daemon de sync (cada ${interval} minutos)...`);
    cron.schedule(`*/${interval} * * * *`, () => runSync());
  } else {
    runSync({ dryRun: args.includes('--dry-run') }).catch(err => {
      console.error(err);
      process.exit(1);
    });
  }
}

module.exports = { runSync, getLocalNotes, syncNote, ensureMoc };
