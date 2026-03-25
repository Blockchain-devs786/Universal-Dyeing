import { getDb } from "../db";

export const accountsService = {
  async list(search = '') {
    const db = getDb();
    if (search) {
      return await db`
        SELECT * FROM accounts 
        WHERE name ILIKE ${'%' + search + '%'} 
           OR bank_name ILIKE ${'%' + search + '%'}
           OR account_number ILIKE ${'%' + search + '%'}
        ORDER BY name ASC
      `;
    }
    return await db`SELECT * FROM accounts ORDER BY name ASC`;
  },

  async getById(id: number) {
    const db = getDb();
    const [account] = await db`SELECT * FROM accounts WHERE id = ${id}`;
    return account;
  },

  async create(data: any) {
    const db = getDb();
    const [account] = await db`
      INSERT INTO accounts (
        name, type, account_number, bank_name, 
        opening_balance, current_balance, status
      ) VALUES (
        ${data.name}, ${data.type}, ${data.account_number || null}, ${data.bank_name || null},
        ${data.opening_balance || 0}, ${data.opening_balance || 0}, ${data.status || 'active'}
      ) RETURNING *
    `;
    return account;
  },

  async update(id: number, data: any) {
    const db = getDb();
    const [account] = await db`
      UPDATE accounts SET
        name = ${data.name},
        type = ${data.type},
        account_number = ${data.account_number || null},
        bank_name = ${data.bank_name || null},
        opening_balance = ${data.opening_balance || 0},
        status = ${data.status || 'active'},
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    return account;
  },

  async delete(id: number) {
    const db = getDb();
    // Check for transactions (if any) before deleting would be good, 
    // but for now we'll just delete.
    await db`DELETE FROM accounts WHERE id = ${id}`;
    return { success: true };
  }
};
