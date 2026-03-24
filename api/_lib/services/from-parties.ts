import { getDb } from '../db.js';

export interface FromParty {
  id?: number;
  name: string;
  phone?: string;
  address?: string;
  city?: string;
  opening_balance?: number;
  status?: string;
  is_default?: boolean;
}

async function logActivity(entityType: string, entityId: number | null, action: string, details: Record<string, unknown> = {}) {
  const sql = getDb();
  await sql`INSERT INTO activity_log (entity_type, entity_id, action, details) VALUES (${entityType}, ${entityId}, ${action}, ${JSON.stringify(details)})`;
}

export const fromPartiesService = {
  async list(search?: string, status?: string) {
    const sql = getDb();
    if (search && status) {
      return sql`
        SELECT * FROM from_parties 
        WHERE (name ILIKE ${'%' + search + '%'} OR city ILIKE ${'%' + search + '%'})
        AND status = ${status}
        ORDER BY name ASC
      `;
    }
    if (search) {
      return sql`
        SELECT * FROM from_parties 
        WHERE name ILIKE ${'%' + search + '%'} OR city ILIKE ${'%' + search + '%'}
        ORDER BY name ASC
      `;
    }
    if (status) {
      return sql`SELECT * FROM from_parties WHERE status = ${status} ORDER BY name ASC`;
    }
    return sql`SELECT * FROM from_parties ORDER BY name ASC`;
  },

  async getById(id: number) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM from_parties WHERE id = ${id}`;
    return rows[0] || null;
  },

  async create(data: FromParty) {
    const sql = getDb();
    const existing = await sql`SELECT id FROM from_parties WHERE LOWER(name) = LOWER(${data.name})`;
    if (existing.length > 0) {
      throw new Error(`From Party with name "${data.name}" already exists`);
    }
    const rows = await sql`
      INSERT INTO from_parties (name, phone, address, city, opening_balance, status)
      VALUES (${data.name}, ${data.phone || null}, ${data.address || null}, 
              ${data.city || null}, ${data.opening_balance || 0}, ${data.status || 'active'})
      RETURNING *
    `;
    await logActivity('from_parties', rows[0].id, 'create', { name: data.name });
    return rows[0];
  },

  async update(id: number, data: Partial<FromParty>) {
    const sql = getDb();
    if (data.name) {
      const existing = await sql`SELECT id FROM from_parties WHERE LOWER(name) = LOWER(${data.name}) AND id != ${id}`;
      if (existing.length > 0) {
        throw new Error(`From Party with name "${data.name}" already exists`);
      }
    }
    
    if (data.status === 'inactive') {
      const checkDefault = await sql`SELECT is_default FROM from_parties WHERE id = ${id}`;
      if (checkDefault[0]?.is_default) {
        throw new Error("The default Dyeing party cannot be disabled.");
      }
    }
    const rows = await sql`
      UPDATE from_parties SET
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
    if (rows.length === 0) throw new Error('From Party not found');
    await logActivity('from_parties', id, 'update', data);
    return rows[0];
  },

  async delete(id: number) {
    const sql = getDb();
    const checkDefault = await sql`SELECT is_default FROM from_parties WHERE id = ${id}`;
    if (checkDefault[0]?.is_default) {
      throw new Error("The default Dyeing party cannot be deleted.");
    }
    let rows;
    try {
      rows = await sql`DELETE FROM from_parties WHERE id = ${id} RETURNING id, name`;
    } catch (err: any) {
      if (err.message?.includes('foreign key constraint')) {
        throw new Error('Cannot delete this party because it is linked to existing Inward/Outward records. Please disable it instead.');
      }
      throw err;
    }
    if (rows.length === 0) throw new Error('From Party not found');
    await logActivity('from_parties', id, 'delete', { name: rows[0].name });
    return { success: true, deleted: rows[0] };
  },
};
