import { getDb } from '../db.js';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { Resend } from 'resend';
import crypto from 'crypto';

const resend = new Resend(process.env.RESEND_API_KEY);
const JWT_SECRET = process.env.JWT_SECRET || 'fallback_secret_change_in_prod';

export interface User {
  id?: number;
  email: string;
  username: string;
  password?: string;
  is_verified?: boolean;
  verification_token?: string;
  token_expiry?: string;
  role?: string;
}

export const usersService = {
  async findByEmail(email: string) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM neon_auth.users WHERE email = ${email}`;
    return rows[0] || null;
  },

  async findByUsername(username: string) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM neon_auth.users WHERE username = ${username}`;
    return rows[0] || null;
  },

  async list() {
    const sql = getDb();
    return await sql`SELECT id, email, username, role, is_verified, module_access, created_at FROM neon_auth.users ORDER BY created_at DESC`;
  },

  async create(data: User & { module_access?: string }) {
    const sql = getDb();
    const hashedPassword = await bcrypt.hash(data.password!, 10);
    const [user] = await sql`
      INSERT INTO neon_auth.users (
        email, username, password, role, module_access
      ) VALUES (
        ${data.email || ''}, 
        ${data.username || ''}, 
        ${hashedPassword}, 
        ${data.role || 'user'}, 
        ${data.module_access || 'all'}
      ) RETURNING id, email, username, role, is_verified, module_access
    `;
    return user;
  },

  async update(id: number, data: Partial<User> & { module_access?: string }) {
    const sql = getDb();
    
    // Hash password if updating
    let hashedPassword = data.password;
    if (hashedPassword) {
      hashedPassword = await bcrypt.hash(hashedPassword, 10);
    }

    const [user] = await sql`
      UPDATE neon_auth.users SET
        email = COALESCE(${data.email || null}, email),
        username = COALESCE(${data.username || null}, username),
        password = COALESCE(${hashedPassword || null}, password),
        role = COALESCE(${data.role || null}, role),
        module_access = COALESCE(${data.module_access || null}, module_access),
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING id, email, username, role, is_verified, module_access
    `;
    return user;
  },

  async delete(id: number) {
    const sql = getDb();
    await sql`DELETE FROM neon_auth.users WHERE id = ${id}`;
    return { success: true };
  },

  async generateVerificationToken(email: string) {
    const sql = getDb();
    const token = crypto.randomBytes(32).toString('hex');
    const expiry = new Date();
    expiry.setHours(expiry.getHours() + 24); // 24 hour expiry

    await sql`
      UPDATE neon_auth.users SET
        verification_token = ${token},
        token_expiry = ${expiry}
      WHERE email = ${email}
    `;
    return token;
  },

  async verifyEmail(token: string) {
    const sql = getDb();
    const rows = await sql`
      SELECT id, email, token_expiry FROM neon_auth.users 
      WHERE verification_token = ${token}
    `;
    
    if (rows.length === 0) throw new Error('Invalid verification link');
    
    const user = rows[0];
    if (new Date() > new Date(user.token_expiry)) {
      throw new Error('Verification link has expired');
    }

    await sql`
      UPDATE neon_auth.users SET
        is_verified = true,
        verification_token = NULL,
        token_expiry = NULL,
        updated_at = NOW()
      WHERE id = ${user.id}
    `;

    return { success: true, user_id: user.id };
  },

  async verifyManually(id: number) {
    const sql = getDb();
    await sql`
      UPDATE neon_auth.users SET
        is_verified = true,
        verification_token = NULL,
        token_expiry = NULL,
        updated_at = NOW()
      WHERE id = ${id}
    `;
    return { success: true };
  },

  async sendVerificationEmail(email: string, baseUrl: string) {
    const user = await this.findByEmail(email);
    if (!user) throw new Error('User not found');

    const token = await this.generateVerificationToken(email);
    const verificationLink = `${baseUrl}/verify-email?token=${token}`;
    const fromEmail = process.env.RESEND_FROM_EMAIL || 'Universal Dyeing <onboarding@resend.dev>';

    const { data, error } = await resend.emails.send({
      from: fromEmail,
      to: email,
      subject: 'Verify your Universal Dyeing account',
      html: `
        <h1>Welcome to Universal Dyeing</h1>
        <p>Please click the link below to verify your email address:</p>
        <a href="${verificationLink}" style="padding: 10px 20px; background-color: #3b82f6; color: white; text-decoration: none; border-radius: 5px;">Verify Email</a>
        <p>This link expires in 24 hours.</p>
      `,
    });

    if (error) {
      console.error('[Resend Error Details]:', JSON.stringify(error, null, 2));
      console.error('[Attempted From Email]:', fromEmail);
      throw new Error(`Failed to send verification email: ${error.message || 'Unknown error'}`);
    }
    return data;
  },

  async login(usernameOrEmail: string, password_raw: string) {
    const sql = getDb();
    const rows = await sql`
      SELECT * FROM neon_auth.users 
      WHERE username = ${usernameOrEmail} OR email = ${usernameOrEmail}
    `;

    if (rows.length === 0) throw new Error('Invalid credentials');
    const user = rows[0];

    if (!user.is_verified) {
      throw new Error('Email not verified. Please check your inbox.');
    }

    const isValid = await bcrypt.compare(password_raw, user.password);
    if (!isValid) throw new Error('Invalid credentials');

    const token = jwt.sign(
      { id: user.id, username: user.username, role: user.role },
      JWT_SECRET,
      { expiresIn: '7d' }
    );

    return {
      token,
      user: {
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        module_access: user.module_access
      }
    };
  }
};
