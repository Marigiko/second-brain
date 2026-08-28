const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, '..', 'config.json');

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

function getApiKey() {
  const keyVar = loadConfig().obsidian.api_key_env;
  if (process.env[keyVar]) return process.env[keyVar];
  // Fallback al env de awe: el cron corre sin el entorno de la shell interactiva,
  // asi que sin esto la key no aparece y toda escritura via API falla.
  try {
    const fs = require('fs');
    const path = require('path');
    const envPath = path.join(process.env.HOME || '/home/keyz', '.config/awe/env/mcp.env');
    const content = fs.readFileSync(envPath, 'utf8');
    const match = content.match(new RegExp(`^${keyVar}=(.+)$`, 'm'));
    if (match) return match[1].trim();
  } catch (e) {}
  return null;
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
      // La Local REST API espera el cuerpo de una nota como texto plano; solo las
      // operaciones de control viajan como JSON.
      const isJson = typeof body === 'object' && !body._isRawString;
      if (!isJson) {
        options.headers['Content-Type'] = 'text/plain';
        options.headers['Content-Length'] = Buffer.byteLength(String(body));
      } else {
        options.headers['Content-Length'] = Buffer.byteLength(JSON.stringify(body));
      }
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
      const isJson = typeof body === 'object' && !body._isRawString;
      req.write(isJson ? JSON.stringify(body) : String(body));
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

// ---------------------------------------------------------------------------
// Backend de filesystem
//
// La REST API exige que Obsidian este abierto, con el plugin Local REST API
// activo y la API key exportada. Historicamente eso fallo: las primeras notas
// de prueba quedaron con `sync_status: error` y un HTTP 401.
//
// El vault es un directorio normal y desde WSL se alcanza por `vault_path`, asi
// que escribir a disco es el camino confiable. Obsidian toma los cambios solo.
// `write_mode` en config.json: 'auto' (REST y si falla FS) | 'rest' | 'filesystem'.
// ---------------------------------------------------------------------------

function vaultAbsolutePath(vaultRelativePath) {
  const base = loadConfig().obsidian.vault_path;
  if (!base) throw new Error('config.obsidian.vault_path no esta definido');
  return path.join(base, vaultRelativePath);
}

function fsEnsureDir(dirPath) {
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
}

function fsWrite(vaultRelativePath, content) {
  const abs = vaultAbsolutePath(vaultRelativePath);
  fsEnsureDir(path.dirname(abs));
  fs.writeFileSync(abs, content, 'utf8');
  return abs;
}

function fsRead(vaultRelativePath) {
  return fs.readFileSync(vaultAbsolutePath(vaultRelativePath), 'utf8');
}

function fsExists(vaultRelativePath) {
  return fs.existsSync(vaultAbsolutePath(vaultRelativePath));
}

function fsAppend(vaultRelativePath, content) {
  const abs = vaultAbsolutePath(vaultRelativePath);
  fsEnsureDir(path.dirname(abs));
  fs.appendFileSync(abs, content, 'utf8');
  return abs;
}

// --- API unificada: la que deben usar sync-engine y el resto ---------------

function writeMode() {
  return loadConfig().obsidian.write_mode || 'auto';
}

/** Escribe (o reemplaza) una nota. Devuelve el backend que la escribio. */
async function noteWrite(vaultRelativePath, content) {
  const mode = writeMode();

  if (mode === 'filesystem') {
    fsWrite(vaultRelativePath, content);
    return 'filesystem';
  }

  try {
    await vaultWrite(vaultRelativePath, content);
    return 'rest';
  } catch (err) {
    if (mode === 'rest') throw err;
    fsWrite(vaultRelativePath, content);
    return 'filesystem';
  }
}

/** Appendea al final de una nota, creandola si no existe. */
async function noteAppend(vaultRelativePath, content) {
  const mode = writeMode();

  if (mode === 'filesystem') {
    fsAppend(vaultRelativePath, content);
    return 'filesystem';
  }

  try {
    await vaultAppend(vaultRelativePath, content);
    return 'rest';
  } catch (err) {
    if (mode === 'rest') throw err;
    fsAppend(vaultRelativePath, content);
    return 'filesystem';
  }
}

/** Lee una nota; null si no existe (en cualquiera de los dos backends). */
async function noteRead(vaultRelativePath) {
  const mode = writeMode();

  if (mode !== 'filesystem') {
    try {
      return await vaultRead(vaultRelativePath);
    } catch {
      if (mode === 'rest') return null;
    }
  }
  return fsExists(vaultRelativePath) ? fsRead(vaultRelativePath) : null;
}

/** Existe la nota. Con REST caido cae a filesystem. */
async function noteExists(vaultRelativePath) {
  return (await noteRead(vaultRelativePath)) !== null;
}

/** Lista los .md de un directorio del vault. [] si no existe. */
async function noteListDir(vaultRelativeDir) {
  const mode = writeMode();

  if (mode !== 'filesystem') {
    try {
      const res = await vaultList(vaultRelativeDir.replace(/\/?$/, '/'));
      const files = res && res.files ? res.files : [];
      return files.filter(f => f.endsWith('.md'));
    } catch {
      if (mode === 'rest') return [];
    }
  }

  const abs = vaultAbsolutePath(vaultRelativeDir);
  if (!fs.existsSync(abs)) return [];
  return fs.readdirSync(abs).filter(f => f.endsWith('.md'));
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
  makeRequest,
  // API unificada (REST + filesystem)
  noteWrite,
  noteAppend,
  noteRead,
  noteExists,
  noteListDir,
  vaultAbsolutePath,
  writeMode
};
