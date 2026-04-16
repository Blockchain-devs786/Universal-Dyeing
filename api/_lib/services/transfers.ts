import { getDb } from '../db.js';
import { fifoService } from './fifo.js';

export interface TransferItem {
  id?: number;
  transfer_id?: number;
  item_id: number;
  measurement: 15 | 22;
  quantity: number;
}

export interface Transfer {
  id?: number;
  transfer_no?: string;
  gp_no?: string;
  sr_no?: string;
  ms_party_id: number;
  from_party_id: number;
  transfer_to_party_id: number;
  vehicle_no?: string;
  driver_name?: string;
  date: string;
  items?: TransferItem[];
}

export const transfersService = {
  async list(ms_party_id?: number, query_transfer_no?: string, query_gp_no?: string, from_date?: string, to_date?: string) {
    const sql = getDb();
    
    return sql`
      SELECT 
        o.*,
        m.name as ms_party_name,
        f.name as from_party_name,
        t.name as transfer_to_party_name,
        COALESCE(SUM(oi.quantity), 0) as total_qty
      FROM transfers o
      LEFT JOIN ms_parties m ON o.ms_party_id = m.id
      LEFT JOIN from_parties f ON o.from_party_id = f.id
      LEFT JOIN from_parties t ON o.transfer_to_party_id = t.id
      LEFT JOIN transfer_items oi ON oi.transfer_id = o.id
      WHERE 
        (${ms_party_id || null}::integer IS NULL OR o.ms_party_id = ${ms_party_id || null}::integer)
        AND (${query_transfer_no || null}::text IS NULL OR o.transfer_no ILIKE ${'%' + (query_transfer_no || '') + '%'})
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
      FROM transfers o
      LEFT JOIN ms_parties m ON o.ms_party_id = m.id
      LEFT JOIN from_parties f ON o.from_party_id = f.id
      LEFT JOIN from_parties t ON o.transfer_to_party_id = t.id
      WHERE o.id = ${id}
    `;
    
    if (rows.length === 0) return null;
    
    const items = await sql`
      SELECT oi.*, it.name as item_name 
      FROM transfer_items oi
      LEFT JOIN items it ON oi.item_id = it.id
      WHERE oi.transfer_id = ${id}
    `;
    
    let deductions: any[] = [];
    if (rows[0]) {
      deductions = await fifoService.getTransferDeductions(id);
    }
    
    return { ...rows[0], items, deductions };
  },

  async create(data: Transfer) {
    const sql = getDb();
    
    // Insert transfer record
    const transferRows = await sql`
      INSERT INTO transfers (ms_party_id, from_party_id, transfer_to_party_id, vehicle_no, driver_name, date)
      VALUES (${data.ms_party_id}, ${data.from_party_id}, ${data.transfer_to_party_id}, ${data.vehicle_no || null}, 
              ${data.driver_name || null}, ${data.date})
      RETURNING id
    `;
    
    const transferId = transferRows[0].id;
    
    const transferNo = `TR-${String(transferId).padStart(5, '0')}`;
    const gpNo = `GP-${String(transferId).padStart(5, '0')}`;
    
    const maxSrRow = await sql`
      SELECT COALESCE(MAX(CAST(NULLIF(regexp_replace(sr_no, '[^0-9]', '', 'g'), '') AS INTEGER)), 0) + 1 AS next_sr_no
      FROM transfers 
      WHERE ms_party_id = ${data.ms_party_id}
    `;
    const srNo = String(maxSrRow[0].next_sr_no);

    await sql`
      UPDATE transfers 
      SET transfer_no = ${transferNo}, gp_no = ${gpNo}, sr_no = ${srNo}
      WHERE id = ${transferId}
    `;

    // Insert items
    if (data.items && data.items.length > 0) {
      for (const item of data.items) {
        await sql`
          INSERT INTO transfer_items (transfer_id, item_id, measurement, quantity)
          VALUES (${transferId}, ${item.item_id}, ${item.measurement}, ${item.quantity})
        `;
      }
    }
    
    await fifoService.processTransferFifo(transferId);
    
    return this.getById(transferId);
  },

  async update(id: number, data: Partial<Transfer>) {
    const sql = getDb();
    
    let newSrNo: string | undefined = undefined;
    if (data.ms_party_id) {
       const existingRow = await sql`SELECT ms_party_id FROM transfers WHERE id = ${id}`;
       if (existingRow.length > 0 && existingRow[0].ms_party_id !== data.ms_party_id) {
           const maxSrRow = await sql`
             SELECT COALESCE(MAX(CAST(NULLIF(regexp_replace(sr_no, '[^0-9]', '', 'g'), '') AS INTEGER)), 0) + 1 AS next_sr_no
             FROM transfers 
             WHERE ms_party_id = ${data.ms_party_id}
           `;
           newSrNo = String(maxSrRow[0].next_sr_no);
       }
    }

    if (data.ms_party_id || data.from_party_id || data.transfer_to_party_id || typeof data.vehicle_no !== 'undefined' || typeof data.driver_name !== 'undefined' || data.date || newSrNo) {
      await sql`
        UPDATE transfers SET
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
      await sql`DELETE FROM transfer_items WHERE transfer_id = ${id}`;
      for (const item of data.items) {
        await sql`
          INSERT INTO transfer_items (transfer_id, item_id, measurement, quantity)
          VALUES (${id}, ${item.item_id}, ${item.measurement}, ${item.quantity})
        `;
      }
    }
    
    await fifoService.processTransferFifo(id);

    return this.getById(id);
  },

  async delete(id: number) {
    const sql = getDb();
    await fifoService.clearTransferDeductions(id);
    await sql`DELETE FROM transfer_items WHERE transfer_id = ${id}`;
    const rows = await sql`DELETE FROM transfers WHERE id = ${id} RETURNING id, transfer_no`;
    if (rows.length === 0) throw new Error('Transfer not found');
    return { success: true, deleted: rows[0] };
  },
};
