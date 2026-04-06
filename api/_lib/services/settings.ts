import { getDb } from '../db.js';

export interface AppSetting {
  id?: number;
  key: string;
  value: string;
  updated_at?: string;
}

export const settingsService = {
  async list() {
    const sql = getDb();
    const rows = await sql`SELECT * FROM application_settings`;
    return rows;
  },

  async getByKey(key: string) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM application_settings WHERE key = ${key}`;
    return rows[0] || null;
  },

  async updateByKey(key: string, value: string) {
    const sql = getDb();
    const rows = await sql`
      INSERT INTO application_settings (key, value)
      VALUES (${key}, ${value})
      ON CONFLICT (key) DO UPDATE SET
        value = ${value},
        updated_at = NOW()
      RETURNING *
    `;
    return rows[0];
  },

  async updateMultiple(settings: Record<string, string>) {
    const results = [];
    for (const [key, value] of Object.entries(settings)) {
      results.push(await this.updateByKey(key, value));
    }
    return results;
  }
};
