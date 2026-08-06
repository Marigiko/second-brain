const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const CONFIG_PATH = path.join(__dirname, '..', 'config.json');

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

function readFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return {};
  try {
    return yaml.load(match[1]) || {};
  } catch {
    return {};
  }
}

function searchInContent(content, query) {
  if (!query) return true;
  const lower = content.toLowerCase();
  const terms = query.toLowerCase().split(/\s+/);
  return terms.every(term => lower.includes(term));
}

function readNotes(projectName, query = '', options = {}) {
  const config = loadConfig();
  const { type = null, limit = 10, since = null } = options;

  let projectPath = null;
  const project = config.projects.find(p => p.name === projectName);
  if (project) {
    projectPath = project.path;
  } else {
    projectPath = path.join('/mnt/d/Projects', projectName);
  }

  const sbDir = path.join(projectPath, '.second-brain');
  if (!fs.existsSync(sbDir)) {
    return { found: 0, notes: [], message: `No existe .second-brain en ${projectName}` };
  }

  const categories = type ? [type] : ['decisiones', 'aprendizajes', 'convenciones', 'arquitectura', 'diario'];
  const results = [];

  for (const category of categories) {
    const catDir = path.join(sbDir, category);
    if (!fs.existsSync(catDir)) continue;

    const files = fs.readdirSync(catDir).filter(f => f.endsWith('.md'));
    for (const file of files) {
      const filePath = path.join(catDir, file);
      const content = fs.readFileSync(filePath, 'utf8');
      const fm = readFrontmatter(content);

      if (since && fm.date && fm.date < since) continue;
      if (!searchInContent(content, query)) continue;

      const bodyMatch = content.match(/^---\n[\s\S]*?\n---\n([\s\S]*)/);
      const body = bodyMatch ? bodyMatch[1].trim() : content;

      results.push({
        category,
        filename: file,
        title: fm.title || file.replace('.md', ''),
        date: fm.date,
        tags: fm.tags || [],
        agent: fm.agent,
        body: body.slice(0, 500),
        path: filePath
      });
    }
  }

  const limited = results.slice(0, limit);
  return {
    found: results.length,
    returned: limited.length,
    notes: limited
  };
}

function formatForContext(notesResult) {
  if (notesResult.found === 0) {
    return 'No hay notas previas en el Second Brain para este proyecto.';
  }

  let output = `## Contexto del Second Brain (${notesResult.found} notas)\n\n`;

  const byCategory = {};
  for (const note of notesResult.notes) {
    if (!byCategory[note.category]) byCategory[note.category] = [];
    byCategory[note.category].push(note);
  }

  for (const [category, notes] of Object.entries(byCategory)) {
    output += `### ${category.charAt(0).toUpperCase() + category.slice(1)}\n\n`;
    for (const note of notes) {
      output += `**${note.title}** (${note.date || 'sin fecha'})\n`;
      output += `${note.body.slice(0, 200)}...\n\n`;
    }
  }

  return output;
}

if (require.main === module) {
  const args = process.argv.slice(2);
  const [projectName, ...queryParts] = args;
  const query = queryParts.join(' ');

  if (!projectName) {
    console.error('Uso: node read-notes.js <project> [query] [--type <type>] [--limit <n>]');
    process.exit(1);
  }

  const result = readNotes(projectName, query);
  console.log(formatForContext(result));
}

module.exports = { readNotes, formatForContext };
