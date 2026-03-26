import type { VercelRequest, VercelResponse } from '@vercel/node';
import { getDb, initializeDatabase } from './_lib/db.js';
import { usersService } from './_lib/services/users.js';

let dbInitialized = false;

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
    // Lazy DB init
    if (!dbInitialized) {
        await initializeDatabase();
        dbInitialized = true;
    }

    const action = (req.query.action as string) || (req.body?.action as string);
    if (!action) {
      return res.status(400).json({ success: false, error: 'Missing "action" parameter' });
    }

    const data = req.body?.data || {};
    const baseUrl = req.headers.origin || 'http://localhost:5173'; // Fallback for dev

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

      // 1. Admin creates user
      case 'users.create':
        return res.status(200).json({ success: true, data: await usersService.create(data) });

      case 'users.list':
        return res.status(200).json({ success: true, data: await usersService.list() });

      case 'users.update':
        return res.status(200).json({ success: true, data: await usersService.update(parseInt(data.id), data) });

      case 'users.delete':
        return res.status(200).json({ success: true, data: await usersService.delete(parseInt(data.id)) });

      case 'users.verify_manually':
        return res.status(200).json({ success: true, data: await usersService.verifyManually(parseInt(data.id)) });

      // 2. First-time login / Check email flow
      case 'auth.check_email': {
        const user = await usersService.findByEmail(data.email);
        if (!user) {
          return res.status(404).json({ success: false, error: 'User does not exist.' });
        }
        
        if (user.is_verified) {
          return res.status(200).json({ success: true, data: { verified: true } });
        } else {
          // Send verification email again if returning non-verified user
          await usersService.sendVerificationEmail(user.email, baseUrl);
          return res.status(200).json({ success: true, data: { verified: false, message: 'Verification email sent.' } });
        }
      }

      // 3. Email Verification Process (User clicks link)
      case 'auth.verify_email':
        return res.status(200).json({ success: true, data: await usersService.verifyEmail(data.token) });

      // 4. Login flow
      case 'auth.login':
        return res.status(200).json({ success: true, data: await usersService.login(data.username || data.email, data.password) });

      // 5. Resend verification button
      case 'auth.resend_verification':
        return res.status(200).json({ success: true, data: await usersService.sendVerificationEmail(data.email, baseUrl) });

      default:
        return res.status(400).json({ success: false, error: `Unknown auth action: ${action}` });
    }
  } catch (error: any) {
    console.error('[API Auth Error]', error);
    const status = error.message?.includes('already exists') ? 409
      : error.message?.includes('not found') ? 404
      : 401; // Default to 401 for auth errors
    return res.status(status).json({ success: false, error: error.message || 'Internal server error' });
  }
}
