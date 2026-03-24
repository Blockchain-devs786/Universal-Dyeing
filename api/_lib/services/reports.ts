import { getDb } from '../db.js';

export interface StockReportRow {
  item_id: number;
  item_name: string;
  msr: number;
  ms_party_id: number;
  ms_party_name: string;
  total_inward: number;
  total_outward: number;
  total_transfer: number;
  transfer_in: number;
  transfer_out: number;
  remaining: number;
}

export const reportsService = {
  async getStockReport(ms_party_id?: number, item_id?: number) {
    const sql = getDb();
    
    // For now, Outward, Transfer, Transfer IN, Transfer OUT are stubbed to 0
    // since those modules don't exist yet, but the aggregation structure is ready.
    const query = await sql`
      SELECT 
        it.id as item_id,
        it.name as item_name, 
        ii.measurement as msr, 
        i.ms_party_id as ms_party_id,
        m.name as ms_party_name,
        SUM(ii.quantity) as total_inward,
        0 as total_outward,
        0 as total_transfer,
        0 as transfer_in,
        0 as transfer_out,
        SUM(ii.quantity) as remaining
      FROM inward_items ii
      JOIN inwards i ON ii.inward_id = i.id
      JOIN items it ON ii.item_id = it.id
      JOIN ms_parties m ON i.ms_party_id = m.id
      WHERE 
        (${ms_party_id || null}::integer IS NULL OR i.ms_party_id = ${ms_party_id || null}::integer)
        AND (${item_id || null}::integer IS NULL OR ii.item_id = ${item_id || null}::integer)
      GROUP BY ii.item_id, it.id, it.name, ii.measurement, i.ms_party_id, m.name
      ORDER BY it.name ASC, m.name ASC
    `;

    return query.map(row => ({
      ...row,
      total_inward: Number(row.total_inward || 0),
      total_outward: Number(row.total_outward || 0),
      total_transfer: Number(row.total_transfer || 0),
      transfer_in: Number(row.transfer_in || 0),
      transfer_out: Number(row.transfer_out || 0),
      remaining: Number(row.remaining || 0)
    }));
  }
};
