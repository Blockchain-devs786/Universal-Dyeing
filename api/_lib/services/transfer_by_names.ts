import { getDb } from '../db.js';
import { fifoService } from './fifo.js';
import { inwardsService } from './inwards.js';

export interface TransferByNameItem {
  id?: number;
  tbn_id?: number;
  item_id: number;
  measurement: 15 | 22;
  quantity: number;
}

export interface TransferByName {
  id?: number;
  tbn_no?: string;
  gp_no?: string;
  sr_no?: string;
  ms_party_id: number;
  from_party_id: number;
  transfer_to_party_id: number;
  vehicle_no?: string;
  driver_name?: string;
  date: string;
  items?: TransferByNameItem[];
}

export const transferByNamesService = {
  async list(ms_party_id?: number, query_tbn_no?: string, query_gp_no?: string, from_date?: string, to_date?: string) {
    const sql = getDb();
    
    return sql`
      SELECT 
        o.*,
        m.name as ms_party_name,
        f.name as from_party_name,
        t.name as transfer_to_party_name,
        COALESCE(SUM(oi.quantity), 0) as total_qty
      FROM transfer_by_names o
      LEFT JOIN ms_parties m ON o.ms_party_id = m.id
      LEFT JOIN from_parties f ON o.from_party_id = f.id
      LEFT JOIN ms_parties t ON o.transfer_to_party_id = t.id
      LEFT JOIN transfer_bn_items oi ON oi.tbn_id = o.id
      WHERE 
        (${ms_party_id || null}::integer IS NULL OR o.ms_party_id = ${ms_party_id || null}::integer)
        AND (${query_tbn_no || null}::text IS NULL OR o.tbn_no ILIKE ${'%' + (query_tbn_no || '') + '%'})
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
        t.name as transfer_to_party_name
      FROM transfer_by_names o
      LEFT JOIN ms_parties m ON o.ms_party_id = m.id
      LEFT JOIN from_parties f ON o.from_party_id = f.id
      LEFT JOIN ms_parties t ON o.transfer_to_party_id = t.id
      WHERE o.id = ${id}
    `;
    
    if (rows.length === 0) return null;
    
    const items = await sql`
      SELECT oi.*, it.name as item_name 
      FROM transfer_bn_items oi
      LEFT JOIN items it ON oi.item_id = it.id
      WHERE oi.tbn_id = ${id}
    `;
    
    let deductions: any[] = [];
    if (rows[0]) {
      deductions = await fifoService.getTbnDeductions(id);
    }
    
    return { ...rows[0], items, deductions };
  },

  async create(data: TransferByName) {
    const sql = getDb();
    
    if (String(data.ms_party_id) === String(data.transfer_to_party_id)) {
      throw new Error("Cannot transfer to the same MS Party");
    }

    // Insert tbn record
    const tbnRows = await sql`
      INSERT INTO transfer_by_names (ms_party_id, from_party_id, transfer_to_party_id, vehicle_no, driver_name, date)
      VALUES (${data.ms_party_id}, ${data.from_party_id}, ${data.transfer_to_party_id}, ${data.vehicle_no || null}, 
              ${data.driver_name || null}, ${data.date})
      RETURNING id
    `;
    
    const tbnId = tbnRows[0].id;
    
    const tbnNo = `TBN-${String(tbnId).padStart(5, '0')}`;
    const gpNo = `GP-${String(tbnId).padStart(5, '0')}`;
    
    const maxSrRow = await sql`
      SELECT COALESCE(MAX(CAST(NULLIF(regexp_replace(sr_no, '[^0-9]', '', 'g'), '') AS INTEGER)), 0) + 1 AS next_sr_no
      FROM transfer_by_names 
      WHERE ms_party_id = ${data.ms_party_id}
    `;
    const srNo = String(maxSrRow[0].next_sr_no);

    await sql`
      UPDATE transfer_by_names 
      SET tbn_no = ${tbnNo}, gp_no = ${gpNo}, sr_no = ${srNo}
      WHERE id = ${tbnId}
    `;

    // Insert items
    if (data.items && data.items.length > 0) {
      for (const item of data.items) {
        await sql`
          INSERT INTO transfer_bn_items (tbn_id, item_id, measurement, quantity)
          VALUES (${tbnId}, ${item.item_id}, ${item.measurement}, ${item.quantity})
        `;
      }
    }
    
    await fifoService.processTbnFifo(tbnId);

    // Auto-create connected inward record for the receiving party
    const newInward = await inwardsService.create({
      ms_party_id: data.transfer_to_party_id,
      from_party_id: data.from_party_id,
      date: data.date,
      reference: tbnNo,
      vehicle_no: data.vehicle_no,
      driver_name: data.driver_name,
      items: data.items,
    });
    
    if (newInward) {
      await sql`UPDATE inwards SET inward_no = '(TRBN)' || inward_no WHERE id = ${newInward.id}`;
    }
    
    return this.getById(tbnId);
  },

  async update(id: number, data: Partial<TransferByName>) {
    const sql = getDb();
    
    let newSrNo: string | undefined = undefined;
    if (data.ms_party_id) {
       const existingRow = await sql`SELECT ms_party_id FROM transfer_by_names WHERE id = ${id}`;
       if (existingRow.length > 0 && existingRow[0].ms_party_id !== data.ms_party_id) {
           const maxSrRow = await sql`
             SELECT COALESCE(MAX(CAST(NULLIF(regexp_replace(sr_no, '[^0-9]', '', 'g'), '') AS INTEGER)), 0) + 1 AS next_sr_no
             FROM transfer_by_names 
             WHERE ms_party_id = ${data.ms_party_id}
           `;
           newSrNo = String(maxSrRow[0].next_sr_no);
       }
    }

    if (String(data.ms_party_id) === String(data.transfer_to_party_id)) {
      throw new Error("Cannot transfer to the same MS Party");
    }

    if (data.ms_party_id || data.from_party_id || data.transfer_to_party_id || typeof data.vehicle_no !== 'undefined' || typeof data.driver_name !== 'undefined' || data.date || newSrNo) {
      await sql`
        UPDATE transfer_by_names SET
          ms_party_id = COALESCE(${data.ms_party_id ?? null}, ms_party_id),
          from_party_id = COALESCE(${data.from_party_id ?? null}, from_party_id),
          transfer_to_party_id = COALESCE(${data.transfer_to_party_id ?? null}, transfer_to_party_id),
          vehicle_no = COALESCE(${data.vehicle_no ?? null}, vehicle_no),
          driver_name = COALESCE(${data.driver_name ?? null}, driver_name),
          date = COALESCE(${data.date ?? null}, date),
          sr_no = COALESCE(${newSrNo ?? null}, sr_no),
          updated_at = NOW()
        WHERE id = ${id}
      `;
    }

    if (data.items) {
      await sql`DELETE FROM transfer_bn_items WHERE tbn_id = ${id}`;
      for (const item of data.items) {
        await sql`
          INSERT INTO transfer_bn_items (tbn_id, item_id, measurement, quantity)
          VALUES (${id}, ${item.item_id}, ${item.measurement}, ${item.quantity})
        `;
      }
    }
    
    const tbnRec = await this.getById(id);
    if (tbnRec) {
      await fifoService.processTbnFifo(id);
      
      const existingInward = await sql`SELECT id FROM inwards WHERE reference = ${tbnRec.tbn_no}`;
      if (existingInward.length > 0) {
        await inwardsService.update(existingInward[0].id, {
          ms_party_id: data.transfer_to_party_id ?? tbnRec.transfer_to_party_id,
          from_party_id: data.from_party_id ?? tbnRec.from_party_id,
          date: data.date ?? tbnRec.date,
          vehicle_no: typeof data.vehicle_no !== 'undefined' ? data.vehicle_no : tbnRec.vehicle_no,
          driver_name: typeof data.driver_name !== 'undefined' ? data.driver_name : tbnRec.driver_name,
          items: data.items ?? tbnRec.items,
        });
      }
    }

    return tbnRec;
  },

  async delete(id: number) {
    const sql = getDb();
    const tbnRec = await this.getById(id);
    await fifoService.clearTbnDeductions(id);
    if (tbnRec) {
       await sql`DELETE FROM inwards WHERE reference = ${tbnRec.tbn_no}`;
    }
    await sql`DELETE FROM transfer_bn_items WHERE tbn_id = ${id}`;
    const rows = await sql`DELETE FROM transfer_by_names WHERE id = ${id} RETURNING id, tbn_no`;
    if (rows.length === 0) throw new Error('TransferByName not found');
    return { success: true, deleted: rows[0] };
  },
};
