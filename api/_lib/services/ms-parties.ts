import { getDb } from '../db.js';

export interface MsParty {
  id?: number;
  name: string;
  phone?: string;
  address?: string;
  city?: string;
  opening_balance?: number;
  status?: string;
  rate_15?: number;
  rate_22?: number;
}

async function logActivity(entityType: string, entityId: number | null, action: string, details: Record<string, unknown> = {}) {
  const sql = getDb();
  await sql`INSERT INTO activity_log (entity_type, entity_id, action, details) VALUES (${entityType}, ${entityId}, ${action}, ${JSON.stringify(details)})`;
}

export const msPartiesService = {
  async list(search?: string, status?: string) {
    const sql = getDb();
    const baseQuery = sql`
      SELECT *, (opening_balance + debit - credit) as balance
      FROM ms_parties
    `;

    if (search && status) {
      return sql`
        ${baseQuery}
        WHERE (name ILIKE ${'%' + search + '%'} OR city ILIKE ${'%' + search + '%'})
        AND status = ${status}
        ORDER BY name ASC
      `;
    }
    if (search) {
      return sql`
        ${baseQuery}
        WHERE name ILIKE ${'%' + search + '%'} OR city ILIKE ${'%' + search + '%'}
        ORDER BY name ASC
      `;
    }
    if (status) {
      return sql`
        ${baseQuery}
        WHERE status = ${status} 
        ORDER BY name ASC
      `;
    }
    return sql`${baseQuery} ORDER BY name ASC`;
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
      INSERT INTO ms_parties (name, phone, address, city, opening_balance, status, rate_15, rate_22)
      VALUES (${data.name}, ${data.phone || null}, ${data.address || null}, 
              ${data.city || null}, ${data.opening_balance || 0}, ${data.status || 'active'},
              ${data.rate_15 || 0}, ${data.rate_22 || 0})
      RETURNING *
    `;
    
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
        rate_15 = COALESCE(${data.rate_15 ?? null}, rate_15),
        rate_22 = COALESCE(${data.rate_22 ?? null}, rate_22),
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    if (rows.length === 0) throw new Error('MS Party not found');

    await logActivity('ms_parties', id, 'update', data);
    return rows[0];
  },

  async delete(id: number) {
    const sql = getDb();
    
    // Protect default Dyeing party
    const target = await sql`SELECT name FROM ms_parties WHERE id = ${id}`;
    if (target.length > 0 && target[0].name.toLowerCase() === 'dyeing') {
      throw new Error('Deletion of the default Dyeing Unit ledger is prohibited.');
    }

    let rows;
    try {
      rows = await sql`DELETE FROM ms_parties WHERE id = ${id} RETURNING id, name`;
    } catch (err: any) {
      if (err.message?.includes('foreign key constraint')) {
        throw new Error('Cannot delete this party because it is linked to existing Inward/Outward records. Please disable it instead.');
      }
      throw err;
    }
    if (rows.length === 0) throw new Error('MS Party not found');
    const deletedName = rows[0].name;

    await logActivity('ms_parties', id, 'delete', { name: deletedName });
    return { success: true, deleted: rows[0] };
  },
};
