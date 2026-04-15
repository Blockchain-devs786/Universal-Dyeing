import express from 'express';
import cors from 'cors';
import path from 'path';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config({ path: path.join(__dirname, '.env') });

// We are using tsx which can load these .ts files seamlessly
import coreHandler from './api/core.ts';
import authHandler from './api/auth.ts';

const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
// Parse JSON bodies (as Vercel would)
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Vercel compatibility wrapper
const adaptHandler = (handler: any) => {
  return async (req: express.Request, res: express.Response) => {
    try {
      await handler(req, res);
    } catch (err) {
      console.error('[Express Adapter Error]', err);
      if (!res.headersSent) {
        res.status(500).json({ success: false, error: 'Internal Server Error' });
      }
    }
  };
};

// Map Vercel routes
app.all('/api/core', adaptHandler(coreHandler));
app.all('/api/auth', adaptHandler(authHandler));

// Serve Vite frontend distribution
const distPath = path.join(__dirname, 'dist');
app.use(express.static(distPath));

// For React Router single-page application fallback
app.use((req, res) => {
  res.sendFile(path.join(distPath, 'index.html'));
});

app.listen(port, () => {
  console.log(`[Server] App running locally on http://localhost:${port}`);
  console.log(`[Server] Serving frontend and Vercel-style API functions`);
});
