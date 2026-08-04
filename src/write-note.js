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

function writeNote(projectName, type, title, content, agent, tags = []) {
  const config = loadConfig();
  const project = config.projects.find(p => p.name === projectName);

  if (!project) {
    const projectPath = path.join('/mnt/d/Projects', projectName);
    return writeNoteToPath(projectPath, type, title, content, agent, tags);
  }

  return writeNoteToPath(project.path, type, title, content, agent, tags);
}

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
