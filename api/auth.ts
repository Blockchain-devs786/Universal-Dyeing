import type { VercelRequest, VercelResponse } from '@vercel/node';
import { getDb } from './_lib/db';

/**
 * Auth API handler — handles authentication operations
 */
export default async function handler(req: VercelRequest, res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const action = (req.query.action as string) || (req.body?.action as string);
    if (!action) {
      return res.status(400).json({ success: false, error: 'Missing "action" parameter' });
    }

    switch (action) {
      case 'ping':
        return res.status(200).json({ success: true, data: { message: 'Auth service is running' } });

      case 'health': {
        const sql = getDb();
        const result = await sql`SELECT NOW() as server_time`;
        return res.status(200).json({ 
          success: true, 
          data: { status: 'healthy', database: 'connected', server_time: result[0].server_time }
        });
      }

      default:
        return res.status(400).json({ success: false, error: `Unknown auth action: ${action}` });
    }
  } catch (error: any) {
    console.error('[API Auth Error]', error);
    return res.status(500).json({ success: false, error: error.message || 'Internal server error' });
  }
}
