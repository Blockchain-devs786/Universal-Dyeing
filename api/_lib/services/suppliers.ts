import { getDb } from '../db.js';

export interface Supplier {
  id?: number;
  name: string;
  phone?: string;
  address?: string;
  city?: string;
  opening_balance?: number;
  status?: string;
}

async function logActivity(entityType: string, entityId: number | null, action: string, details: Record<string, unknown> = {}) {
  const sql = getDb();
  await sql`INSERT INTO activity_log (entity_type, entity_id, action, details) VALUES (${entityType}, ${entityId}, ${action}, ${JSON.stringify(details)})`;
}

export const suppliersService = {
  async list(search?: string, status?: string) {
    const sql = getDb();
    if (search && status) {
      return sql`
        SELECT * FROM suppliers 
        WHERE (name ILIKE ${'%' + search + '%'} OR city ILIKE ${'%' + search + '%'})
        AND status = ${status}
        ORDER BY name ASC
      `;
    }
    if (search) {
      return sql`
        SELECT * FROM suppliers 
        WHERE name ILIKE ${'%' + search + '%'} OR city ILIKE ${'%' + search + '%'}
        ORDER BY name ASC
      `;
    }
    if (status) {
      return sql`SELECT * FROM suppliers WHERE status = ${status} ORDER BY name ASC`;
    }
    return sql`SELECT * FROM suppliers ORDER BY name ASC`;
  },

  async getById(id: number) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM suppliers WHERE id = ${id}`;
    return rows[0] || null;
  },

  async create(data: Supplier) {
    const sql = getDb();
    const existing = await sql`SELECT id FROM suppliers WHERE LOWER(name) = LOWER(${data.name})`;
    if (existing.length > 0) {
      throw new Error(`Supplier with name "${data.name}" already exists`);
    }
    const rows = await sql`
      INSERT INTO suppliers (name, phone, address, city, opening_balance, status)
      VALUES (${data.name}, ${data.phone || null}, ${data.address || null}, 
              ${data.city || null}, ${data.opening_balance || 0}, ${data.status || 'active'})
      RETURNING *
    `;
    await logActivity('suppliers', rows[0].id, 'create', { name: data.name });
    return rows[0];
  },

  async update(id: number, data: Partial<Supplier>) {
    const sql = getDb();
    if (data.name) {
      const existing = await sql`SELECT id FROM suppliers WHERE LOWER(name) = LOWER(${data.name}) AND id != ${id}`;
      if (existing.length > 0) {
        throw new Error(`Supplier with name "${data.name}" already exists`);
      }
    }
    const rows = await sql`
      UPDATE suppliers SET
        name = COALESCE(${data.name ?? null}, name),
        phone = COALESCE(${data.phone ?? null}, phone),
        address = COALESCE(${data.address ?? null}, address),
        city = COALESCE(${data.city ?? null}, city),
        opening_balance = COALESCE(${data.opening_balance ?? null}, opening_balance),
        status = COALESCE(${data.status ?? null}, status),
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    if (rows.length === 0) throw new Error('Supplier not found');
    await logActivity('suppliers', id, 'update', data);
    return rows[0];
  },

  async delete(id: number) {
    const sql = getDb();
    const rows = await sql`DELETE FROM suppliers WHERE id = ${id} RETURNING id, name`;
    if (rows.length === 0) throw new Error('Supplier not found');
    await logActivity('suppliers', id, 'delete', { name: rows[0].name });
    return { success: true, deleted: rows[0] };
  },
};
