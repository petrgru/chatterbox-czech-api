import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 4173;
const API_TARGET = process.env.API_TARGET || 'http://api:8000';

// Proxy API routes to FastAPI service (preserve original path)
const apiProxy = createProxyMiddleware({
  target: API_TARGET,
  changeOrigin: true,
  ws: false,
  logLevel: 'warn',
});

app.use((req, res, next) => {
  if (req.path === '/health' || req.path.startsWith('/v1')) {
    return apiProxy(req, res, next);
  }
  next();
});

// Serve static SPA assets
const distDir = path.join(__dirname, 'dist');
app.use(express.static(distDir));

// SPA fallback to index.html: catch-all middleware
app.use((req, res) => {
  res.sendFile(path.join(distDir, 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Client server listening on http://0.0.0.0:${PORT}`);
  console.log(`Proxying API routes to ${API_TARGET}`);
});
