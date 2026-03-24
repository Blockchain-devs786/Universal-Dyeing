import { getDb } from '../db.js';

export interface InwardItem {
  id?: number;
  inward_id?: number;
  item_id: number;
  measurement: 15 | 22;
  quantity: number;
}

export interface Inward {
  id?: number;
  inward_no?: string;
  gp_no?: string;
  sr_no?: string;
  ms_party_id: number;
  from_party_id: number;
  vehicle_no?: string;
  driver_name?: string;
  date: string;
  items?: InwardItem[];
}

export const inwardsService = {
  async list(ms_party_id?: number, query_inward_no?: string, query_gp_no?: string, from_date?: string, to_date?: string) {
    const sql = getDb();
    
    // We construct the query conditionally using neon's proper tagged template nesting 
    // or just fetch all and filter, or a monolithic safe query with COALESCE
    
    // Very safe unified query handling optional params via Postgres logic
    return sql`
      SELECT 
        i.*,
        m.name as ms_party_name,
        f.name as from_party_name,
        COALESCE(SUM(ii.quantity), 0) as total_qty
      FROM inwards i
      LEFT JOIN ms_parties m ON i.ms_party_id = m.id
      LEFT JOIN from_parties f ON i.from_party_id = f.id
      LEFT JOIN inward_items ii ON ii.inward_id = i.id
      WHERE 
        (${ms_party_id || null}::integer IS NULL OR i.ms_party_id = ${ms_party_id || null}::integer)
        AND (${query_inward_no || null}::text IS NULL OR i.inward_no ILIKE ${'%' + (query_inward_no || '') + '%'})
        AND (${query_gp_no || null}::text IS NULL OR i.gp_no ILIKE ${'%' + (query_gp_no || '') + '%'})
        AND (${from_date || null}::date IS NULL OR i.date >= ${from_date || null}::date)
        AND (${to_date || null}::date IS NULL OR i.date <= ${to_date || null}::date)
      GROUP BY i.id, m.name, f.name 
      ORDER BY i.created_at DESC
    `;
  },

  async getById(id: number) {
    const sql = getDb();
    const rows = await sql`
      SELECT 
        i.*,
        m.name as ms_party_name,
        f.name as from_party_name
      FROM inwards i
      LEFT JOIN ms_parties m ON i.ms_party_id = m.id
      LEFT JOIN from_parties f ON i.from_party_id = f.id
      WHERE i.id = ${id}
    `;
    
    if (rows.length === 0) return null;
    
    const items = await sql`
      SELECT ii.*, it.name as item_name 
      FROM inward_items ii
      LEFT JOIN items it ON ii.item_id = it.id
      WHERE ii.inward_id = ${id}
    `;
    
    return { ...rows[0], items };
  },

  async create(data: Inward) {
    const sql = getDb();
    
    // Insert inward record (without numbers initially)
    const inwardRows = await sql`
      INSERT INTO inwards (ms_party_id, from_party_id, vehicle_no, driver_name, date)
      VALUES (${data.ms_party_id}, ${data.from_party_id}, ${data.vehicle_no || null}, 
              ${data.driver_name || null}, ${data.date})
      RETURNING id
    `;
    
    const inwardId = inwardRows[0].id;
    
    // Auto-generate numbers based on ID
    const inwardNo = `INW-${String(inwardId).padStart(5, '0')}`;
    const gpNo = `GP-${String(inwardId).padStart(5, '0')}`;
    const srNo = `${inwardId}`;

    await sql`
      UPDATE inwards 
      SET inward_no = ${inwardNo}, gp_no = ${gpNo}, sr_no = ${srNo}
      WHERE id = ${inwardId}
    `;

    // Insert items
    if (data.items && data.items.length > 0) {
      for (const item of data.items) {
        await sql`
          INSERT INTO inward_items (inward_id, item_id, measurement, quantity)
          VALUES (${inwardId}, ${item.item_id}, ${item.measurement}, ${item.quantity})
        `;
      }
    }
    
    return this.getById(inwardId);
  },

  async update(id: number, data: Partial<Inward>) {
    const sql = getDb();
    
    // Only update core fields if they are provided
    if (data.ms_party_id || data.from_party_id || typeof data.vehicle_no !== 'undefined' || typeof data.driver_name !== 'undefined' || data.date) {
      await sql`
        UPDATE inwards SET
          ms_party_id = COALESCE(${data.ms_party_id ?? null}, ms_party_id),
          from_party_id = COALESCE(${data.from_party_id ?? null}, from_party_id),
          vehicle_no = COALESCE(${data.vehicle_no ?? null}, vehicle_no),
          driver_name = COALESCE(${data.driver_name ?? null}, driver_name),
          date = COALESCE(${data.date ?? null}, date),
          updated_at = NOW()
        WHERE id = ${id}
      `;
    }

    // If items are provided, replace them completely
    if (data.items) {
      await sql`DELETE FROM inward_items WHERE inward_id = ${id}`;
      for (const item of data.items) {
        await sql`
          INSERT INTO inward_items (inward_id, item_id, measurement, quantity)
          VALUES (${id}, ${item.item_id}, ${item.measurement}, ${item.quantity})
        `;
      }
    }

    return this.getById(id);
  },

  async delete(id: number) {
    const sql = getDb();
    // Cascade delete handles items if defined in schema, otherwise we explicitly delete:
    await sql`DELETE FROM inward_items WHERE inward_id = ${id}`;
    const rows = await sql`DELETE FROM inwards WHERE id = ${id} RETURNING id, inward_no`;
    if (rows.length === 0) throw new Error('Inward not found');
    return { success: true, deleted: rows[0] };
  },
};
