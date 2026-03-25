import { getDb } from "../db.js";

export const vouchersService = {
  async list(filters: any = {}) {
    const db = getDb();
    let query = db`
      SELECT v.*, 
        (SELECT json_agg(ve.*) FROM voucher_entries ve WHERE ve.voucher_id = v.id) as entries
      FROM vouchers v
      WHERE 1=1
    `;

    if (filters.type) {
      query = db`${query} AND v.type = ${filters.type}`;
    }
    if (filters.from_date) {
      query = db`${query} AND v.date >= ${filters.from_date}`;
    }
    if (filters.to_date) {
      query = db`${query} AND v.date <= ${filters.to_date}`;
    }
    if (filters.search && filters.search.trim() !== "") {
      const s = `%${filters.search}%`;
      query = db`${query} AND (v.voucher_no ILIKE ${s} OR v.description ILIKE ${s})`;
    }

    return await db`${query} ORDER BY v.date DESC, v.id DESC`;
  },

  async create(data: any) {
    const db = getDb();
    
    // Generate Voucher No
    const prefix = data.type; // CRV, CPV, JV
    const [lastVoucher] = await db`
      SELECT voucher_no FROM vouchers 
      WHERE type = ${data.type} 
      ORDER BY id DESC LIMIT 1
    `;
    
    let nextNum = 1;
    if (lastVoucher && lastVoucher.voucher_no) {
       const parts = lastVoucher.voucher_no.split('-');
       nextNum = parseInt(parts[1]) + 1;
    }
    const voucherNo = `${prefix}-${String(nextNum).padStart(4, '0')}`;

    // Use transaction for consistency
    // Note: neon serverless doesn't support traditional BEGIN/COMMIT in one go via db tag safely without a pool/client,
    // but we can execute multiple statements.

    const [voucher] = await db`
      INSERT INTO vouchers (
        voucher_no, type, date, ref_no, description, total_amount, status, created_by
      ) VALUES (
        ${voucherNo}, ${data.type}, ${data.date}, ${data.ref_no || null}, 
        ${data.description || null}, ${data.total_amount}, ${data.status || 'posted'}, ${data.created_by || 'system'}
      ) RETURNING *
    `;

    if (data.entries && data.entries.length > 0) {
      for (const entry of data.entries) {
        await db`
          INSERT INTO voucher_entries (
            voucher_id, account_type, account_id, debit, credit, description
          ) VALUES (
            ${voucher.id}, ${entry.account_type}, ${entry.account_id}, 
            ${entry.debit || 0}, ${entry.credit || 0}, ${entry.description || null}
          )
        `;

        // Update Account Balances
        await this.updateAccountBalance(entry);
      }
    }

    return voucher;
  },

  async updateAccountBalance(entry: any, isReversal = false) {
    const db = getDb();
    const multiplier = isReversal ? -1 : 1;
    const debit = (entry.debit || 0) * multiplier;
    const credit = (entry.credit || 0) * multiplier;

    switch (entry.account_type) {
      case 'MS Party':
        await db`
          UPDATE ms_parties SET 
            debit = debit + ${debit}, 
            credit = credit + ${credit},
            updated_at = NOW()
          WHERE id = ${entry.account_id}
        `;
        break;
      case 'Vendor':
        await db`
          UPDATE vendors SET 
            debit = debit + ${debit}, 
            credit = credit + ${credit},
            updated_at = NOW()
          WHERE id = ${entry.account_id}
        `;
        break;
      case 'Account': {
        const diff = debit - credit;
        await db`
          UPDATE accounts SET 
            current_balance = current_balance + ${diff},
            updated_at = NOW()
          WHERE id = ${entry.account_id}
        `;
        break;
      }
      case 'Asset': {
        const diff = debit - credit;
        await db`
          UPDATE assets SET 
            value = value + ${diff},
            updated_at = NOW()
          WHERE id = ${entry.account_id}
        `;
        break;
      }
      // Expenses usually don't track a running balance in this simple schema, 
      // but we record them in voucher_entries for reports.
    }
  },

  async delete(id: number) {
    const db = getDb();
    const entries = await db`SELECT * FROM voucher_entries WHERE voucher_id = ${id}`;
    
    // Reverse balances
    for (const entry of entries) {
      await this.updateAccountBalance(entry, true);
    }

    await db`DELETE FROM vouchers WHERE id = ${id}`;
    return { success: true };
  }
};
