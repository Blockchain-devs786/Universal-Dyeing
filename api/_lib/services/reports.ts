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
    
    // Calculate total inward per item/msr/party
    const query = await sql`
      WITH inward_totals AS (
        SELECT 
          ii.item_id,
          ii.measurement as msr, 
          i.ms_party_id,
          SUM(ii.quantity) as total_inward
        FROM inward_items ii
        JOIN inwards i ON ii.inward_id = i.id
        GROUP BY ii.item_id, ii.measurement, i.ms_party_id
      ),
      outward_totals AS (
        SELECT 
          oi.item_id,
          oi.measurement as msr, 
          o.ms_party_id,
          SUM(oi.quantity) as total_outward
        FROM outward_items oi
        JOIN outwards o ON oi.outward_id = o.id
        GROUP BY oi.item_id, oi.measurement, o.ms_party_id
      ),
      transfer_out_totals AS (
        SELECT 
          ti.item_id,
          ti.measurement as msr, 
          t.ms_party_id,
          SUM(ti.quantity) as transfer_out
        FROM transfer_items ti
        JOIN transfers t ON ti.transfer_id = t.id
        GROUP BY ti.item_id, ti.measurement, t.ms_party_id
      ),
      tbn_out_totals AS (
        SELECT 
          ti.item_id,
          ti.measurement as msr, 
          t.ms_party_id,
          SUM(ti.quantity) as transfer_out
        FROM transfer_bn_items ti
        JOIN transfer_by_names t ON ti.tbn_id = t.id
        GROUP BY ti.item_id, ti.measurement, t.ms_party_id
      ),
      transfer_in_totals AS (
        SELECT 
          ti.item_id,
          ti.measurement as msr, 
          t.transfer_to_party_id as ms_party_id,
          SUM(ti.quantity) as transfer_in
        FROM transfer_bn_items ti
        JOIN transfer_by_names t ON ti.tbn_id = t.id
        GROUP BY ti.item_id, ti.measurement, t.transfer_to_party_id
      ),
      all_keys AS (
        SELECT item_id, msr, ms_party_id FROM inward_totals
        UNION
        SELECT item_id, msr, ms_party_id FROM outward_totals
        UNION
        SELECT item_id, msr, ms_party_id FROM transfer_out_totals
        UNION
        SELECT item_id, msr, ms_party_id FROM tbn_out_totals
        UNION
        SELECT item_id, msr, ms_party_id FROM transfer_in_totals
      ),
      combined AS (
        SELECT 
          k.item_id,
          k.msr,
          k.ms_party_id,
          COALESCE(i.total_inward, 0) as total_inward,
          COALESCE(o.total_outward, 0) as total_outward,
          COALESCE(tout.transfer_out, 0) as total_transfer,
          COALESCE(tbnout.transfer_out, 0) as transfer_out,
          COALESCE(tin.transfer_in, 0) as transfer_in
        FROM all_keys k
        LEFT JOIN inward_totals i ON k.item_id = i.item_id AND k.msr = i.msr AND k.ms_party_id = i.ms_party_id
        LEFT JOIN outward_totals o ON k.item_id = o.item_id AND k.msr = o.msr AND k.ms_party_id = o.ms_party_id
        LEFT JOIN transfer_out_totals tout ON k.item_id = tout.item_id AND k.msr = tout.msr AND k.ms_party_id = tout.ms_party_id
        LEFT JOIN tbn_out_totals tbnout ON k.item_id = tbnout.item_id AND k.msr = tbnout.msr AND k.ms_party_id = tbnout.ms_party_id
        LEFT JOIN transfer_in_totals tin ON k.item_id = tin.item_id AND k.msr = tin.msr AND k.ms_party_id = tin.ms_party_id
      )
      SELECT 
        it.id as item_id,
        it.name as item_name, 
        c.msr, 
        c.ms_party_id as ms_party_id,
        m.name as ms_party_name,
        c.total_inward,
        c.total_outward,
        c.total_transfer,
        c.transfer_in,
        c.transfer_out,
        (c.total_inward + c.transfer_in - c.total_outward - c.total_transfer - c.transfer_out) as remaining
      FROM combined c
      JOIN items it ON c.item_id = it.id
      JOIN ms_parties m ON c.ms_party_id = m.id
      WHERE 
        (${ms_party_id || null}::integer IS NULL OR c.ms_party_id = ${ms_party_id || null}::integer)
        AND (${item_id || null}::integer IS NULL OR c.item_id = ${item_id || null}::integer)
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
