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
