import { getDb } from '../db.js';

export interface MsParty {
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

export const msPartiesService = {
  async list(search?: string, status?: string) {
    const sql = getDb();
    if (search && status) {
      return sql`
        SELECT * FROM ms_parties 
        WHERE (name ILIKE ${'%' + search + '%'} OR city ILIKE ${'%' + search + '%'})
        AND status = ${status}
        ORDER BY name ASC
      `;
    }
    if (search) {
      return sql`
        SELECT * FROM ms_parties 
        WHERE name ILIKE ${'%' + search + '%'} OR city ILIKE ${'%' + search + '%'}
        ORDER BY name ASC
      `;
    }
    if (status) {
      return sql`SELECT * FROM ms_parties WHERE status = ${status} ORDER BY name ASC`;
    }
    return sql`SELECT * FROM ms_parties ORDER BY name ASC`;
  },

  async getById(id: number) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM ms_parties WHERE id = ${id}`;
    return rows[0] || null;
  },

  async create(data: MsParty) {
    const sql = getDb();
    const existing = await sql`SELECT id FROM ms_parties WHERE LOWER(name) = LOWER(${data.name})`;
    if (existing.length > 0) {
      throw new Error(`MS Party with name "${data.name}" already exists`);
    }
    const rows = await sql`
      INSERT INTO ms_parties (name, phone, address, city, opening_balance, status)
      VALUES (${data.name}, ${data.phone || null}, ${data.address || null}, 
              ${data.city || null}, ${data.opening_balance || 0}, ${data.status || 'active'})
      RETURNING *
    `;
    
    // Automatically sync to from_parties module
    try {
      await sql`
        INSERT INTO from_parties (name, phone, address, city, opening_balance, status)
        VALUES (${data.name}, ${data.phone || null}, ${data.address || null}, 
                ${data.city || null}, ${data.opening_balance || 0}, ${data.status || 'active'})
        ON CONFLICT (name) DO NOTHING
      `;
    } catch (e) {
      console.error('[Sync Error] Failed to auto-sync ms_party to from_parties', e);
    }

    await logActivity('ms_parties', rows[0].id, 'create', { name: data.name });
    return rows[0];
  },

  async update(id: number, data: Partial<MsParty>) {
    const sql = getDb();

    // Get old name for syncing
    const oldRecord = await sql`SELECT name FROM ms_parties WHERE id = ${id}`;
    const oldName = oldRecord.length > 0 ? oldRecord[0].name : null;

    if (data.name) {
      const existing = await sql`SELECT id FROM ms_parties WHERE LOWER(name) = LOWER(${data.name}) AND id != ${id}`;
      if (existing.length > 0) {
        throw new Error(`MS Party with name "${data.name}" already exists`);
      }
    }
    const rows = await sql`
      UPDATE ms_parties SET
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
    if (rows.length === 0) throw new Error('MS Party not found');

    // Automatically sync updates to from_parties based on exact old name match
    if (oldName) {
      try {
        await sql`
          UPDATE from_parties SET
            name = COALESCE(${data.name ?? null}, name),
            phone = COALESCE(${data.phone ?? null}, phone),
            address = COALESCE(${data.address ?? null}, address),
            city = COALESCE(${data.city ?? null}, city),
            opening_balance = COALESCE(${data.opening_balance ?? null}, opening_balance),
            status = COALESCE(${data.status ?? null}, status),
            updated_at = NOW()
          WHERE name = ${oldName}
        `;
      } catch (e) {
        console.error('[Sync Error] Failed to update from_parties sync', e);
      }
    }

    await logActivity('ms_parties', id, 'update', data);
    return rows[0];
  },

  async delete(id: number) {
    const sql = getDb();
    const rows = await sql`DELETE FROM ms_parties WHERE id = ${id} RETURNING id, name`;
    if (rows.length === 0) throw new Error('MS Party not found');

    // Automatically sync delete to from_parties based on exact name match
    const deletedName = rows[0].name;
    try {
      await sql`DELETE FROM from_parties WHERE name = ${deletedName}`;
    } catch (e) {
      console.error('[Sync Error] Failed to delete from_parties sync', e);
    }

    await logActivity('ms_parties', id, 'delete', { name: deletedName });
    return { success: true, deleted: rows[0] };
  },
};
