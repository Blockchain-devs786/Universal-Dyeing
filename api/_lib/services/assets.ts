import { getDb } from '../db.js';

export interface Asset {
  id?: number;
  name: string;
  description?: string;
  category?: string;
  value?: number;
  location?: string;
  status?: string;
  purchase_date?: string;
}

async function logActivity(entityType: string, entityId: number | null, action: string, details: Record<string, unknown> = {}) {
  const sql = getDb();
  await sql`INSERT INTO activity_log (entity_type, entity_id, action, details) VALUES (${entityType}, ${entityId}, ${action}, ${JSON.stringify(details)})`;
}

export const assetsService = {
  async list(search?: string, status?: string, category?: string) {
    const sql = getDb();
    if (search) {
      return sql`
        SELECT * FROM assets 
        WHERE name ILIKE ${'%' + search + '%'} OR category ILIKE ${'%' + search + '%'}
        ORDER BY name ASC
      `;
    }
    if (status) {
      return sql`SELECT * FROM assets WHERE status = ${status} ORDER BY name ASC`;
    }
    if (category) {
      return sql`SELECT * FROM assets WHERE category = ${category} ORDER BY name ASC`;
    }
    return sql`SELECT * FROM assets ORDER BY name ASC`;
  },

  async getById(id: number) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM assets WHERE id = ${id}`;
    return rows[0] || null;
  },

  async create(data: Asset) {
    const sql = getDb();
    const existing = await sql`SELECT id FROM assets WHERE LOWER(name) = LOWER(${data.name})`;
    if (existing.length > 0) {
      throw new Error(`Asset with name "${data.name}" already exists`);
    }
    const rows = await sql`
      INSERT INTO assets (name, description, category, value, location, status, purchase_date)
      VALUES (${data.name}, ${data.description || null}, ${data.category || null}, 
              ${data.value || 0}, ${data.location || null}, ${data.status || 'active'},
              ${data.purchase_date || null})
      RETURNING *
    `;
    await logActivity('assets', rows[0].id, 'create', { name: data.name });
    return rows[0];
  },

  async update(id: number, data: Partial<Asset>) {
    const sql = getDb();
    if (data.name) {
      const existing = await sql`SELECT id FROM assets WHERE LOWER(name) = LOWER(${data.name}) AND id != ${id}`;
      if (existing.length > 0) {
        throw new Error(`Asset with name "${data.name}" already exists`);
      }
    }
    const rows = await sql`
      UPDATE assets SET
        name = COALESCE(${data.name ?? null}, name),
        description = COALESCE(${data.description ?? null}, description),
        category = COALESCE(${data.category ?? null}, category),
        value = COALESCE(${data.value ?? null}, value),
        location = COALESCE(${data.location ?? null}, location),
        status = COALESCE(${data.status ?? null}, status),
        purchase_date = COALESCE(${data.purchase_date ?? null}, purchase_date),
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    if (rows.length === 0) throw new Error('Asset not found');
    await logActivity('assets', id, 'update', data);
    return rows[0];
  },

  async delete(id: number) {
    const sql = getDb();
    const rows = await sql`DELETE FROM assets WHERE id = ${id} RETURNING id, name`;
    if (rows.length === 0) throw new Error('Asset not found');
    await logActivity('assets', id, 'delete', { name: rows[0].name });
    return { success: true, deleted: rows[0] };
  },
};
