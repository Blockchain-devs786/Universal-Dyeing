import { getDb } from '../db.js';

export interface OutwardParty {
  id?: number;
  name: string;
  phone?: string;
  address?: string;
  city?: string;
  status?: string;
}

async function logActivity(entityType: string, entityId: number | null, action: string, details: Record<string, unknown> = {}) {
  const sql = getDb();
  await sql`INSERT INTO activity_log (entity_type, entity_id, action, details) VALUES (${entityType}, ${entityId}, ${action}, ${JSON.stringify(details)})`;
}

export const outwardPartiesService = {
  async list(search?: string, status?: string) {
    const sql = getDb();
    if (search && status) {
      return sql`
        SELECT * FROM outward_parties 
        WHERE (name ILIKE ${'%' + search + '%'} OR city ILIKE ${'%' + search + '%'})
        AND status = ${status}
        ORDER BY name ASC
      `;
    }
    if (search) {
      return sql`
        SELECT * FROM outward_parties 
        WHERE name ILIKE ${'%' + search + '%'} OR city ILIKE ${'%' + search + '%'}
        ORDER BY name ASC
      `;
    }
    if (status) {
      return sql`SELECT * FROM outward_parties WHERE status = ${status} ORDER BY name ASC`;
    }
    return sql`SELECT * FROM outward_parties ORDER BY name ASC`;
  },

  async getById(id: number) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM outward_parties WHERE id = ${id}`;
    return rows[0] || null;
  },

  async create(data: OutwardParty) {
    const sql = getDb();
    const existing = await sql`SELECT id FROM outward_parties WHERE LOWER(name) = LOWER(${data.name})`;
    if (existing.length > 0) {
      throw new Error(`Outward Party with name "${data.name}" already exists`);
    }
    const rows = await sql`
      INSERT INTO outward_parties (name, phone, address, city, status)
      VALUES (${data.name}, ${data.phone || null}, ${data.address || null}, 
              ${data.city || null}, ${data.status || 'active'})
      RETURNING *
    `;
    
    await logActivity('outward_parties', rows[0].id, 'create', { name: data.name });
    return rows[0];
  },

  async update(id: number, data: Partial<OutwardParty>) {
    const sql = getDb();

    if (data.name) {
      const existing = await sql`SELECT id FROM outward_parties WHERE LOWER(name) = LOWER(${data.name}) AND id != ${id}`;
      if (existing.length > 0) {
        throw new Error(`Outward Party with name "${data.name}" already exists`);
      }
    }
    const rows = await sql`
      UPDATE outward_parties SET
        name = COALESCE(${data.name ?? null}, name),
        phone = COALESCE(${data.phone ?? null}, phone),
        address = COALESCE(${data.address ?? null}, address),
        city = COALESCE(${data.city ?? null}, city),
        status = COALESCE(${data.status ?? null}, status),
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    if (rows.length === 0) throw new Error('Outward Party not found');

    await logActivity('outward_parties', id, 'update', data);
    return rows[0];
  },

  async delete(id: number) {
    const sql = getDb();
    
    let rows;
    try {
      rows = await sql`DELETE FROM outward_parties WHERE id = ${id} RETURNING id, name`;
    } catch (err: any) {
      if (err.message?.includes('foreign key constraint')) {
        throw new Error('Cannot delete this party because it is linked to existing Outward records. Please disable it instead.');
      }
      throw err;
    }
    if (rows.length === 0) throw new Error('Outward Party not found');

    await logActivity('outward_parties', id, 'delete', { name: rows[0].name });
    return { success: true, deleted: rows[0] };
  },
};
