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
