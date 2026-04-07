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
  from_party_name?: string;
  vehicle_no?: string;
  driver_name?: string;
  date: string;
  reference?: string;
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

  async getReferencesByMsParty(ms_party_id: number) {
    const sql = getDb();
    // Return all unique from_party names linked to this MS Party in past inwards
    return sql`
      SELECT DISTINCT f.id, f.name
      FROM inwards i
      JOIN from_parties f ON i.from_party_id = f.id
      WHERE i.ms_party_id = ${ms_party_id}
      ORDER BY f.name ASC
    `;
  },

  async create(data: Inward) {
    const sql = getDb();
    
    // Resolve or create from_party if name is provided
    let from_party_id = data.from_party_id;
    if (data.from_party_name) {
      const party = await sql`
        INSERT INTO from_parties (name) VALUES (${data.from_party_name})
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
      `;
      from_party_id = party[0].id;
    }

    if (!from_party_id) {
      throw new Error("From Party ID or Name is required");
    }

    // Insert inward record (without numbers initially)
    const inwardRows = await sql`
      INSERT INTO inwards (ms_party_id, from_party_id, vehicle_no, driver_name, date, reference)
      VALUES (${data.ms_party_id}, ${from_party_id}, ${data.vehicle_no || null}, 
              ${data.driver_name || null}, ${data.date}, ${data.reference || null})
      RETURNING id
    `;
    
    const inwardId = inwardRows[0].id;
    
    // Auto-generate numbers based on ID for INW and GP
    const inwardNo = `INW-${String(inwardId).padStart(5, '0')}`;
    const gpNo = `GP-${String(inwardId).padStart(5, '0')}`;
    
    // Auto-generate sr_no per ms_party
    const maxSrRow = await sql`
      SELECT COALESCE(MAX(CAST(NULLIF(regexp_replace(sr_no, '[^0-9]', '', 'g'), '') AS INTEGER)), 0) + 1 AS next_sr_no
      FROM inwards 
      WHERE ms_party_id = ${data.ms_party_id}
    `;
    const srNo = String(maxSrRow[0].next_sr_no);

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
    
    // Check if ms_party_id changed to generate new sr_no
    let newSrNo: string | undefined = undefined;
    if (data.ms_party_id) {
       const existingRow = await sql`SELECT ms_party_id FROM inwards WHERE id = ${id}`;
       if (existingRow.length > 0 && existingRow[0].ms_party_id !== data.ms_party_id) {
           const maxSrRow = await sql`
             SELECT COALESCE(MAX(CAST(NULLIF(regexp_replace(sr_no, '[^0-9]', '', 'g'), '') AS INTEGER)), 0) + 1 AS next_sr_no
             FROM inwards 
             WHERE ms_party_id = ${data.ms_party_id}
           `;
           newSrNo = String(maxSrRow[0].next_sr_no);
       }
    }

    // Resolve or create from_party if name is provided
    let from_party_id = data.from_party_id;
    if (data.from_party_name) {
      const party = await sql`
        INSERT INTO from_parties (name) VALUES (${data.from_party_name})
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
      `;
      from_party_id = party[0].id;
    }

    // Only update core fields if they are provided
    if (data.ms_party_id || from_party_id || typeof data.vehicle_no !== 'undefined' || typeof data.driver_name !== 'undefined' || data.date || newSrNo || typeof data.reference !== 'undefined') {
      await sql`
        UPDATE inwards SET
          ms_party_id = COALESCE(${data.ms_party_id ?? null}, ms_party_id),
          from_party_id = COALESCE(${from_party_id ?? null}, from_party_id),
          vehicle_no = COALESCE(${data.vehicle_no ?? null}, vehicle_no),
          driver_name = COALESCE(${data.driver_name ?? null}, driver_name),
          date = COALESCE(${data.date ?? null}, date),
          sr_no = COALESCE(${newSrNo ?? null}, sr_no),
          reference = COALESCE(${data.reference ?? null}, reference),
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
