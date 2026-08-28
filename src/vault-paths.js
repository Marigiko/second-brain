/**
 * vault-paths.js — Unica fuente de verdad del routing hacia el vault de Obsidian.
 *
 * El vault "Main" tiene tres areas de primer nivel:
 *
 *   Main/
 *   ├── Proyectos/<Vault Folder>/<Subcarpeta>/nota.md   <- trabajo con fecha de cierre
 *   ├── Conocimiento/<Dominio>/<Subcarpeta>/nota.md     <- reutilizable entre proyectos
 *   └── Archivo/                                         <- obsoleto, no se borra
 *
 * La regla que decide el area esta escrita en `Main/00 - Indice.md`:
 *   "Si la nota deja de importar cuando el proyecto termina, va a Proyectos.
 *    Si sirve para el *proximo* trabajo parecido, va a Conocimiento."
 *
 * Un agente no puede tomar esa decision de forma confiable nota por nota, asi que
 * el default es SIEMPRE `proyectos`. `conocimiento` es opt-in explicito: el proyecto
 * declara `knowledge_domain` + `knowledge_categories` en config.json.
 */

const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, '..', 'config.json');

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

/** Nombre de carpeta seguro para Obsidian (y para Windows). */
function safeFolderName(name) {
  return String(name).replace(/[\\/:*?"<>|]/g, '-').trim();
}

/**
 * Resuelve la definicion de un proyecto. Si no esta en config.json, infiere
 * una entrada minima para no perder la nota: la carpeta del vault pasa a ser
 * el nombre del repo.
 */
function resolveProject(projectName, config = loadConfig()) {
  const found = config.projects.find(p => p.name === projectName);
  if (found) {
    return { ...found, vault_folder: found.vault_folder || safeFolderName(found.name) };
  }
  return {
    name: projectName,
    path: path.join('/mnt/d/Projects', projectName),
    vault_folder: safeFolderName(projectName),
    enabled: true,
    inferred: true,
  };
}

/**
 * Decide a que area va una categoria para un proyecto dado.
 * @returns {'proyectos'|'conocimiento'}
 */
function resolveArea(project, category, config = loadConfig()) {
  const knowledgeCats = project.knowledge_categories || [];
  if (project.knowledge_domain && knowledgeCats.includes(category)) {
    return 'conocimiento';
  }
  return config.routing.default_area || 'proyectos';
}

/**
 * Ruta destino de una nota dentro del vault, relativa a la raiz del vault.
 *
 * @returns {{area, areaFolder, containerFolder, subfolder, dir, path}}
 */
function resolveTarget(projectName, category, filename, config = loadConfig()) {
  const project = resolveProject(projectName, config);
  const area = resolveArea(project, category, config);

  const areaFolder = config.vault.areas[area];
  const containerFolder =
    area === 'conocimiento'
      ? safeFolderName(project.knowledge_domain)
      : safeFolderName(project.vault_folder);

  // En `conocimiento` todo cae en una unica bandeja: la taxonomia real del
  // dominio (Problemas/, Soluciones/, Paises/...) se cura a mano y no se puede
  // derivar de la categoria del agente. Sin esto, el sync le agregaria carpetas
  // sueltas a una estructura curada.
  const catCfg = (config.routing.categories || {})[category] || {};
  const subfolder =
    area === 'conocimiento'
      ? config.routing.knowledge_inbox || 'Bandeja de entrada'
      : catCfg.subfolder || capitalize(category);

  const dir = [areaFolder, containerFolder, subfolder].filter(Boolean).join('/');

  return {
    area,
    areaFolder,
    containerFolder,
    subfolder,
    dir,
    path: filename ? `${dir}/${filename}` : dir,
  };
}

/**
 * Ruta del MOC de la carpeta contenedora. El nombre depende del area:
 * `00 - Mapa del Proyecto.md` en Proyectos, `00 - Mapa del dominio.md` en
 * Conocimiento — que es como ya se llaman los MOC que existen en el vault.
 */
function resolveMocPath(projectName, category, config = loadConfig()) {
  const t = resolveTarget(projectName, category, null, config);
  const cfg = (config.vault.moc || {}).filename;
  const filename =
    typeof cfg === 'string'
      ? cfg
      : (cfg || {})[t.area] || '00 - Mapa del Proyecto.md';
  return `${t.areaFolder}/${t.containerFolder}/${filename}`;
}

/** Contenido inicial del MOC, siguiendo la convencion del vault. */
function buildMocContent(projectName, category, config = loadConfig()) {
  const project = resolveProject(projectName, config);
  const area = resolveArea(project, category, config);
  const title =
    area === 'conocimiento'
      ? safeFolderName(project.knowledge_domain)
      : safeFolderName(project.vault_folder);
  const today = new Date().toISOString().split('T')[0];

  return [
    '---',
    area === 'conocimiento' ? 'tags: [conocimiento, moc]' : 'tags: [proyecto, indice]',
    `created: ${today}`,
    '---',
    '',
    `# ${title}`,
    '',
    '> Indice creado por el Second Brain porque no existia. **No se vuelve a tocar:**',
    '> el sync solo lo crea la primera vez, asi que lo que escribas aca se conserva.',
    '',
    '## Notas',
    '',
    area === 'conocimiento'
      ? '_Lo que llega por sync cae en `Bandeja de entrada/` sin destilar. La taxonomia del dominio se cura a mano._'
      : '_Las notas sincronizadas aparecen en las subcarpetas de esta carpeta._',
    '',
    '## Relacionado',
    '',
    '- [[00 - Indice]]',
    '',
  ].join('\n');
}

/** Ruta absoluta en disco para una ruta relativa del vault. */
function toAbsolute(vaultRelativePath, config = loadConfig()) {
  return path.join(config.obsidian.vault_path, vaultRelativePath);
}

function capitalize(s) {
  return String(s).charAt(0).toUpperCase() + String(s).slice(1);
}

module.exports = {
  loadConfig,
  resolveProject,
  resolveArea,
  resolveTarget,
  resolveMocPath,
  buildMocContent,
  toAbsolute,
  safeFolderName,
};
