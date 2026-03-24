import { getDb } from '../db.js';

export interface Item {
  id?: number;
  name: string;
  status?: string;
}

async function logActivity(entityType: string, entityId: number | null, action: string, details: Record<string, unknown> = {}) {
  const sql = getDb();
  await sql`INSERT INTO activity_log (entity_type, entity_id, action, details) VALUES (${entityType}, ${entityId}, ${action}, ${JSON.stringify(details)})`;
}

export const itemsService = {
  async list(search?: string, status?: string) {
    const sql = getDb();
    if (search && status) {
      return sql`
        SELECT * FROM items 
        WHERE name ILIKE ${'%' + search + '%'} AND status = ${status}
        ORDER BY name ASC
      `;
    }
    if (search) {
      return sql`
        SELECT * FROM items 
        WHERE name ILIKE ${'%' + search + '%'}
        ORDER BY name ASC
      `;
    }
    if (status) {
      return sql`SELECT * FROM items WHERE status = ${status} ORDER BY name ASC`;
    }
    return sql`SELECT * FROM items ORDER BY name ASC`;
  },

  async getById(id: number) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM items WHERE id = ${id}`;
    return rows[0] || null;
  },

  async create(data: Item) {
    const sql = getDb();
    const existing = await sql`SELECT id FROM items WHERE LOWER(name) = LOWER(${data.name})`;
    if (existing.length > 0) {
      throw new Error(`Item with name "${data.name}" already exists`);
    }
    const rows = await sql`
      INSERT INTO items (name, status)
      VALUES (${data.name}, ${data.status || 'active'})
      RETURNING *
    `;
    await logActivity('items', rows[0].id, 'create', { name: data.name });
    return rows[0];
  },

  async update(id: number, data: Partial<Item>) {
    const sql = getDb();
    if (data.name) {
      const existing = await sql`SELECT id FROM items WHERE LOWER(name) = LOWER(${data.name}) AND id != ${id}`;
      if (existing.length > 0) {
        throw new Error(`Item with name "${data.name}" already exists`);
      }
    }
    const rows = await sql`
      UPDATE items SET
        name = COALESCE(${data.name ?? null}, name),
        status = COALESCE(${data.status ?? null}, status),
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    if (rows.length === 0) throw new Error('Item not found');
    await logActivity('items', id, 'update', data);
    return rows[0];
  },

  async delete(id: number) {
    const sql = getDb();
    const rows = await sql`DELETE FROM items WHERE id = ${id} RETURNING id, name`;
    if (rows.length === 0) throw new Error('Item not found');
    await logActivity('items', id, 'delete', { name: rows[0].name });
    return { success: true, deleted: rows[0] };
  },
};
