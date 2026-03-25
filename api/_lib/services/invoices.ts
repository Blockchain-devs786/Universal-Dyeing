import { getDb } from '../db.js';

export interface Invoice {
  id?: number;
  invoice_no?: string;
  ms_party_id: number;
  date: string;
  sub_total: number;
  discount_percent: number;
  discount_amount: number;
  total_amount: number;
  rate_15: number;
  rate_22: number;
  status?: string;
  created_by?: string;
  edited_by?: string;
  outward_ids: number[];
}

export const invoicesService = {
  async list(search?: string) {
    const sql = getDb();
    const query = sql`
      SELECT i.*, m.name as ms_party_name,
      (SELECT COUNT(*) FROM invoice_items WHERE invoice_id = i.id) as item_count
      FROM invoices i
      JOIN ms_parties m ON i.ms_party_id = m.id
      ${search ? sql`WHERE i.invoice_no ILIKE ${'%' + search + '%'} OR m.name ILIKE ${'%' + search + '%'}` : sql``}
      ORDER BY i.date DESC, i.id DESC
    `;
    return query;
  },

  async getById(id: number) {
    const sql = getDb();
    const rows = await sql`
      SELECT i.*, m.name as ms_party_name
      FROM invoices i
      JOIN ms_parties m ON i.ms_party_id = m.id
      WHERE i.id = ${id}
    `;
    if (rows.length === 0) return null;

    const items = await sql`
      SELECT 
        o.id as outward_id, o.outward_no, o.gp_no, o.sr_no, it.name as item_name,
        oi.measurement, oi.quantity
      FROM invoice_items ii
      JOIN outwards o ON ii.outward_id = o.id
      JOIN outward_items oi ON o.id = oi.outward_id
      JOIN items it ON oi.item_id = it.id
      WHERE ii.invoice_id = ${id}
    `;

    return { ...rows[0], items };
  },

  async getAvailableOutwards(msPartyId: number) {
    const sql = getDb();
    // Get outwards that are NOT linked to any invoice
    return sql`
      SELECT 
        o.id, o.outward_no, o.gp_no, o.sr_no, o.date,
        SUM(oi.quantity) as total_quantity,
        JSON_AGG(JSON_BUILD_OBJECT(
          'item_name', it.name,
          'item_id', oi.item_id,
          'measurement', oi.measurement,
          'quantity', oi.quantity
        )) as items
      FROM outwards o
      JOIN outward_items oi ON o.id = oi.outward_id
      JOIN items it ON oi.item_id = it.id
      LEFT JOIN invoice_items ii ON o.id = ii.outward_id
      WHERE o.ms_party_id = ${msPartyId} AND ii.id IS NULL
      GROUP BY o.id
      ORDER BY o.date DESC
    `;
  },

  async create(data: Invoice) {
    const sql = getDb();
    
    // Auto-generate invoice no
    const last = await sql`SELECT invoice_no FROM invoices ORDER BY id DESC LIMIT 1`;
    let nextNo = "INV-000001";
    if (last.length > 0) {
      const num = parseInt(last[0].invoice_no.split('-')[1]) + 1;
      nextNo = `INV-${num.toString().padStart(6, '0')}`;
    }

    const [invoice] = await sql`
      INSERT INTO invoices (
        invoice_no, ms_party_id, date, sub_total, 
        discount_percent, discount_amount, total_amount, 
        rate_15, rate_22, created_by
      ) VALUES (
        ${nextNo}, ${data.ms_party_id}, ${data.date}, ${data.sub_total},
        ${data.discount_percent}, ${data.discount_amount}, ${data.total_amount},
        ${data.rate_15}, ${data.rate_22}, ${data.created_by || 'system'}
      ) RETURNING *
    `;

    // Add items
    for (const outId of data.outward_ids) {
      await sql`INSERT INTO invoice_items (invoice_id, outward_id) VALUES (${invoice.id}, ${outId})`;
    }

    return this.getById(invoice.id);
  },

  async update(id: number, data: Partial<Invoice>) {
    const sql = getDb();
    
    // Only allow updating internal values as per user requirement
    const [invoice] = await sql`
      UPDATE invoices SET
        sub_total = COALESCE(${data.sub_total ?? null}, sub_total),
        discount_percent = COALESCE(${data.discount_percent ?? null}, discount_percent),
        discount_amount = COALESCE(${data.discount_amount ?? null}, discount_amount),
        total_amount = COALESCE(${data.total_amount ?? null}, total_amount),
        rate_15 = COALESCE(${data.rate_15 ?? null}, rate_15),
        rate_22 = COALESCE(${data.rate_22 ?? null}, rate_22),
        edited_by = ${data.edited_by || 'system'},
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;

    if (!invoice) throw new Error('Invoice not found');
    return this.getById(id);
  },

  async delete(id: number) {
    const sql = getDb();
    // invoice_items will be deleted automatically due to ON DELETE CASCADE
    await sql`DELETE FROM invoices WHERE id = ${id}`;
    return { success: true };
  }
};
