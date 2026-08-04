const fs = require('fs');
const path = require('path');
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
  const targetDir = `${OBSIDIAN_TARGET_DIR}/${note.category.charAt(0).toUpperCase() + note.category.slice(1)}`;

  if (note.category === 'diario') {
    const targetPath = `${targetDir}/${note.filename}`;
    try {
      let existing = '';
      try {
        existing = await obsidian.vaultRead(targetPath);
      } catch {
        // No existe, se creara
      }

      if (existing) {
        const bodyMatch = note.content.match(/^---\n[\s\S]*?\n---\n([\s\S]*)/);
        const body = bodyMatch ? bodyMatch[1] : note.content;

        await obsidian.vaultPatch(targetPath, {
          targetType: 'heading',
          target: [note.filename.replace('.md', '')],
          operation: 'append',
          content: body
        });
      } else {
        await obsidian.vaultWrite(targetPath, note.content);
      }
    } catch (err) {
      throw new Error(`Sync diario fallo: ${err.message}`);
    }
  } else {
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

if (require.main === module) {
  const args = process.argv.slice(2);

  if (args.includes('--daemon')) {
    const config = loadConfig();
    const interval = config.sync.interval_minutes;
    const cronExpr = `*/${interval} * * * *`;

    const cron = require('node-cron');
    console.log(`Iniciando daemon de sync (cada ${interval} minutos)...`);
    cron.schedule(cronExpr, runSync);
  } else {
    runSync().catch(console.error);
  }
}

module.exports = { runSync, getLocalNotes, syncNote };
