import { getDb } from "../db";

export const accountsService = {
  async list(search?: string) {
    const db = getDb();
    if (search) {
      return db`
        SELECT * FROM accounts 
        WHERE name ILIKE ${'%' + search + '%'} OR (bank_name ILIKE ${'%' + search + '%'})
        ORDER BY name ASC
      `;
    }
    return db`SELECT * FROM accounts ORDER BY name ASC`;
  },

  async getById(id: number) {
    const db = getDb();
    const results = await db`SELECT * FROM accounts WHERE id = ${id}`;
    return results[0];
  },

  async create(data: any) {
    const db = getDb();
    const results = await db`
      INSERT INTO accounts (
        name, type, account_no, bank_name, opening_balance, current_balance
      ) VALUES (
        ${data.name}, ${data.type}, ${data.account_no || null}, ${data.bank_name || null}, 
        ${data.opening_balance || 0}, ${data.opening_balance || 0}
      )
      RETURNING *
    `;
    return results[0];
  },

  async update(id: number, data: any) {
    const db = getDb();
    const results = await db`
      UPDATE accounts SET
        name = ${data.name},
        type = ${data.type},
        account_no = ${data.account_no || null},
        bank_name = ${data.bank_name || null},
        opening_balance = ${data.opening_balance || 0},
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    return results[0];
  },

  async delete(id: number) {
    const db = getDb();
    return db`DELETE FROM accounts WHERE id = ${id}`;
  }
};
