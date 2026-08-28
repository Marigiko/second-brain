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
  // Try process.env first, then load from env file
  if (process.env[keyVar]) return process.env[keyVar];
  // Fallback: read from awe env file
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
      // Send as plain text for vault operations, JSON for others
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
