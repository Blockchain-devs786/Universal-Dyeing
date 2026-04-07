import { getDb } from '../db.js';

export interface OutwardItem {
  id?: number;
  outward_id?: number;
  item_id: number;
  measurement: 15 | 22;
  quantity: number;
}

export interface Outward {
  id?: number;
  outward_no?: string;
  gp_no?: string;
  sr_no?: string;
  ms_party_id: number;
  from_party_id: number;
  outward_to_party_id: number;
  outward_to_party_name?: string;
  vehicle_no?: string;
  driver_name?: string;
  date: string;
  items?: OutwardItem[];
}

export const outwardsService = {
  async list(ms_party_id?: number, query_outward_no?: string, query_gp_no?: string, from_date?: string, to_date?: string) {
    const sql = getDb();
    
    return sql`
      SELECT 
        o.*,
        m.name as ms_party_name,
        f.name as from_party_name,
        t.name as outward_to_party_name,
        COALESCE(SUM(oi.quantity), 0) as total_qty
      FROM outwards o
      LEFT JOIN ms_parties m ON o.ms_party_id = m.id
      LEFT JOIN from_parties f ON o.from_party_id = f.id
      LEFT JOIN outward_parties t ON o.outward_to_party_id = t.id
      LEFT JOIN outward_items oi ON oi.outward_id = o.id
      WHERE 
        (${ms_party_id || null}::integer IS NULL OR o.ms_party_id = ${ms_party_id || null}::integer)
        AND (${query_outward_no || null}::text IS NULL OR o.outward_no ILIKE ${'%' + (query_outward_no || '') + '%'})
        AND (${query_gp_no || null}::text IS NULL OR o.gp_no ILIKE ${'%' + (query_gp_no || '') + '%'})
        AND (${from_date || null}::date IS NULL OR o.date >= ${from_date || null}::date)
        AND (${to_date || null}::date IS NULL OR o.date <= ${to_date || null}::date)
      GROUP BY o.id, m.name, f.name, t.name
      ORDER BY o.created_at DESC
    `;
  },

  async getById(id: number) {
    const sql = getDb();
    const rows = await sql`
      SELECT 
        o.*,
        m.name as ms_party_name,
        f.name as from_party_name,
        t.name as outward_to_party_name
      FROM outwards o
      LEFT JOIN ms_parties m ON o.ms_party_id = m.id
      LEFT JOIN from_parties f ON o.from_party_id = f.id
      LEFT JOIN outward_parties t ON o.outward_to_party_id = t.id
      WHERE o.id = ${id}
    `;
    
    if (rows.length === 0) return null;
    
    const items = await sql`
      SELECT oi.*, it.name as item_name 
      FROM outward_items oi
      LEFT JOIN items it ON oi.item_id = it.id
      WHERE oi.outward_id = ${id}
    `;
    
    return { ...rows[0], items };
  },

  async create(data: Outward) {
    const sql = getDb();
    
    // Resolve or create outward_to_party if name is provided
    let outward_to_party_id = data.outward_to_party_id;
    if (data.outward_to_party_name) {
      const party = await sql`
        INSERT INTO outward_parties (name) VALUES (${data.outward_to_party_name})
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
      `;
      outward_to_party_id = party[0].id;
    }

    if (!outward_to_party_id) {
      throw new Error("Outward To Party ID or Name is required");
    }

    // Insert outward record
    const outwardRows = await sql`
      INSERT INTO outwards (ms_party_id, from_party_id, outward_to_party_id, vehicle_no, driver_name, date)
      VALUES (${data.ms_party_id}, ${data.from_party_id}, ${outward_to_party_id}, ${data.vehicle_no || null}, 
              ${data.driver_name || null}, ${data.date})
      RETURNING id
    `;
    
    const outwardId = outwardRows[0].id;
    
    const outwardNo = `OUT-${String(outwardId).padStart(5, '0')}`;
    const gpNo = `GP-${String(outwardId).padStart(5, '0')}`;
    
    const maxSrRow = await sql`
      SELECT COALESCE(MAX(CAST(NULLIF(regexp_replace(sr_no, '[^0-9]', '', 'g'), '') AS INTEGER)), 0) + 1 AS next_sr_no
      FROM outwards 
      WHERE ms_party_id = ${data.ms_party_id}
    `;
    const srNo = String(maxSrRow[0].next_sr_no);

    await sql`
      UPDATE outwards 
      SET outward_no = ${outwardNo}, gp_no = ${gpNo}, sr_no = ${srNo}
      WHERE id = ${outwardId}
    `;

    // Insert items
    if (data.items && data.items.length > 0) {
      for (const item of data.items) {
        await sql`
          INSERT INTO outward_items (outward_id, item_id, measurement, quantity)
          VALUES (${outwardId}, ${item.item_id}, ${item.measurement}, ${item.quantity})
        `;
      }
    }
    
    return this.getById(outwardId);
  },

  async update(id: number, data: Partial<Outward>) {
    const sql = getDb();
    
    let newSrNo: string | undefined = undefined;
    if (data.ms_party_id) {
       const existingRow = await sql`SELECT ms_party_id FROM outwards WHERE id = ${id}`;
       if (existingRow.length > 0 && existingRow[0].ms_party_id !== data.ms_party_id) {
           const maxSrRow = await sql`
             SELECT COALESCE(MAX(CAST(NULLIF(regexp_replace(sr_no, '[^0-9]', '', 'g'), '') AS INTEGER)), 0) + 1 AS next_sr_no
             FROM outwards 
             WHERE ms_party_id = ${data.ms_party_id}
           `;
           newSrNo = String(maxSrRow[0].next_sr_no);
       }
    }

    // Resolve or create outward_to_party if name is provided
    let outward_to_party_id = data.outward_to_party_id;
    if (data.outward_to_party_name) {
      const party = await sql`
        INSERT INTO outward_parties (name) VALUES (${data.outward_to_party_name})
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
      `;
      outward_to_party_id = party[0].id;
    }

    if (data.ms_party_id || data.from_party_id || outward_to_party_id || typeof data.vehicle_no !== 'undefined' || typeof data.driver_name !== 'undefined' || data.date || newSrNo) {
      await sql`
        UPDATE outwards SET
          ms_party_id = COALESCE(${data.ms_party_id ?? null}, ms_party_id),
          from_party_id = COALESCE(${data.from_party_id ?? null}, from_party_id),
          outward_to_party_id = COALESCE(${outward_to_party_id ?? null}, outward_to_party_id),
          vehicle_no = COALESCE(${data.vehicle_no ?? null}, vehicle_no),
          driver_name = COALESCE(${data.driver_name ?? null}, driver_name),
          date = COALESCE(${data.date ?? null}, date),
          sr_no = COALESCE(${newSrNo ?? null}, sr_no),
          updated_at = NOW()
        WHERE id = ${id}
      `;
    }

    if (data.items) {
      await sql`DELETE FROM outward_items WHERE outward_id = ${id}`;
      for (const item of data.items) {
        await sql`
          INSERT INTO outward_items (outward_id, item_id, measurement, quantity)
          VALUES (${id}, ${item.item_id}, ${item.measurement}, ${item.quantity})
        `;
      }
    }

    return this.getById(id);
  },

  async delete(id: number) {
    const sql = getDb();
    await sql`DELETE FROM outward_items WHERE outward_id = ${id}`;
    const rows = await sql`DELETE FROM outwards WHERE id = ${id} RETURNING id, outward_no`;
    if (rows.length === 0) throw new Error('Outward not found');
    return { success: true, deleted: rows[0] };
  },
};
