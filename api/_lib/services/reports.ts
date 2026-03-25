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

export interface StockLedgerRow {
  id: number;
  date: string;
  type: string;
  ref_no: string;
  ms_party_id: number;
  ms_party_name: string;
  particulars: string;
  item_id: number;
  item_name: string;
  measurement: number;
  debit: number;
  credit: number;
  description: string;
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
  },

  async getStockLedger(filters: {
    ms_party_id?: number;
    item_id?: number;
    from_date?: string;
    to_date?: string;
    transaction_type?: string;
    particulars?: string;
    measurement?: number;
    amount_type?: 'debit' | 'credit';
  }) {
    const sql = getDb();
    const { ms_party_id, item_id, from_date, to_date } = filters;

    const query = await sql`
      WITH ledger_entries AS (
        -- INWARDS (Debit)
        SELECT 
          i.id, i.date, 'Inward' as type, i.inward_no as ref_no, i.ms_party_id,
          fp.name as particulars, ii.item_id, it.name as item_name, ii.measurement,
          ii.quantity as debit, 0 as credit,
          COALESCE(i.gp_no, '') || ' ' || COALESCE(i.sr_no, '') as description,
          i.created_at
        FROM inwards i
        JOIN inward_items ii ON i.id = ii.inward_id
        JOIN items it ON ii.item_id = it.id
        LEFT JOIN from_parties fp ON i.from_party_id = fp.id
        
        UNION ALL
        
        -- OUTWARDS (Credit)
        SELECT 
          o.id, o.date, 'Outward' as type, o.outward_no as ref_no, o.ms_party_id,
          fp_to.name as particulars, oi.item_id, it.name as item_name, oi.measurement,
          0 as debit, oi.quantity as credit,
          COALESCE(o.gp_no, '') || ' ' || COALESCE(o.sr_no, '') as description,
          o.created_at
        FROM outwards o
        JOIN outward_items oi ON o.id = oi.outward_id
        JOIN items it ON oi.item_id = it.id
        LEFT JOIN from_parties fp_to ON o.outward_to_party_id = fp_to.id

        UNION ALL
        
        -- TRANSFERS (Credit)
        SELECT 
          t.id, t.date, 'Transfer' as type, t.transfer_no as ref_no, t.ms_party_id,
          fp_to.name as particulars, ti.item_id, it.name as item_name, ti.measurement,
          0 as debit, ti.quantity as credit,
          COALESCE(t.gp_no, '') || ' ' || COALESCE(t.sr_no, '') as description,
          t.created_at
        FROM transfers t
        JOIN transfer_items ti ON t.id = ti.transfer_id
        JOIN items it ON ti.item_id = it.id
        LEFT JOIN from_parties fp_to ON t.transfer_to_party_id = fp_to.id

        UNION ALL
        
        -- TBN (OUT/Credit)
        SELECT 
          tbn.id, tbn.date, 'Transfer BN OUT' as type, tbn.tbn_no as ref_no, tbn.ms_party_id,
          mp_receive.name as particulars, ti.item_id, it.name as item_name, ti.measurement,
          0 as debit, ti.quantity as credit,
          COALESCE(tbn.gp_no, '') || ' ' || COALESCE(tbn.sr_no, '') as description,
          tbn.created_at
        FROM transfer_by_names tbn
        JOIN transfer_bn_items ti ON tbn.id = ti.tbn_id
        JOIN items it ON ti.item_id = it.id
        LEFT JOIN ms_parties mp_receive ON tbn.transfer_to_party_id = mp_receive.id

        UNION ALL
        
        -- TBN (IN/Debit)
        SELECT 
          tbn.id, tbn.date, 'Transfer BN IN' as type, tbn.tbn_no as ref_no, tbn.transfer_to_party_id as ms_party_id,
          mp_sender.name as particulars, ti.item_id, it.name as item_name, ti.measurement,
          ti.quantity as debit, 0 as credit,
          COALESCE(tbn.gp_no, '') || ' ' || COALESCE(tbn.sr_no, '') as description,
          tbn.created_at
        FROM transfer_by_names tbn
        JOIN transfer_bn_items ti ON tbn.id = ti.tbn_id
        JOIN items it ON ti.item_id = it.id
        LEFT JOIN ms_parties mp_sender ON tbn.ms_party_id = mp_sender.id
      )
      SELECT 
        l.*,
        m.name as ms_party_name
      FROM ledger_entries l
      JOIN ms_parties m ON l.ms_party_id = m.id
      JOIN ms_parties m_target ON l.ms_party_id = m_target.id
      WHERE 
        (
          (${ms_party_id || null}::integer IS NULL) 
          OR 
          (
            EXISTS (SELECT 1 FROM ms_parties WHERE id = ${ms_party_id || null}::integer AND name = 'Dyeing')
            -- If Dyeing is selected, we show EVERYTHING (it is the central pool)
            OR l.ms_party_id = ${ms_party_id || null}::integer
          )
        )
        AND (${item_id || null}::integer IS NULL OR l.item_id = ${item_id || null}::integer)
        AND (${from_date || null}::date IS NULL OR l.date >= ${from_date || null}::date)
        AND (${to_date || null}::date IS NULL OR l.date <= ${to_date || null}::date)
        AND (${filters.transaction_type || null}::text IS NULL OR l.type = ${filters.transaction_type || null}::text)
        AND (${filters.particulars || null}::text IS NULL OR l.particulars = ${filters.particulars || null}::text)
        AND (${filters.measurement || null}::integer IS NULL OR l.measurement = ${filters.measurement || null}::integer)
        AND (${filters.amount_type === 'debit' ? 1 : null}::integer IS NULL OR l.debit > 0)
        AND (${filters.amount_type === 'credit' ? 1 : null}::integer IS NULL OR l.credit > 0)
      ORDER BY l.date ASC, l.created_at ASC
    `;

    return query.map(row => ({
      ...row,
      debit: Number(row.debit || 0),
      credit: Number(row.credit || 0)
    }));
  }
};
