import { getDb } from '../db.js';

/**
 * FIFO Deduction Service
 * 
 * Tracks which outward quantities were deducted from which inward entries.
 * Uses First-In-First-Out logic: oldest inward stock is consumed first.
 * 
 * The fifo_deductions table is the single source of truth for:
 *   - How much of each outward came from each inward
 *   - Remaining qty per inward item = original qty - SUM(deductions)
 */

export interface FifoDeduction {
  id?: number;
  outward_id: number;
  outward_item_id: number;
  inward_id: number;
  inward_item_id: number;
  item_id: number;
  measurement: number;
  ms_party_id: number;
  deducted_qty: number;
  created_at?: string;
}

export interface InwardItemBreakdown {
  inward_item_id: number;
  item_id: number;
  item_name: string;
  measurement: number;
  original_qty: number;
  deducted_qty: number;
  remaining_qty: number;
}

export interface OutwardDeductionDetail {
  id: number;
  outward_id: number;
  outward_item_id: number;
  inward_id: number;
  inward_item_id: number;
  item_id: number;
  measurement: number;
  ms_party_id: number;
  deducted_qty: number;
  inward_no: string;
  inward_gp_no: string;
  inward_ms_party_gp_no: string;
  from_party_name: string;
  item_name: string;
}

export const fifoService = {
  /**
   * Process FIFO deductions for a single outward entry.
   * For each outward item, finds matching inward items (same ms_party, item, measurement)
   * sorted by inward date ASC (FIFO), and deducts quantities.
   */
  async processOutwardFifo(outwardId: number) {
    const sql = getDb();

    // Get the outward record with its items
    const outwardRows = await sql`
      SELECT o.id, o.ms_party_id, o.date
      FROM outwards o WHERE o.id = ${outwardId}
    `;
    if (outwardRows.length === 0) return [];

    const outward = outwardRows[0];

    const outwardItems = await sql`
      SELECT oi.id as outward_item_id, oi.item_id, oi.measurement, oi.quantity
      FROM outward_items oi
      WHERE oi.outward_id = ${outwardId}
    `;

    // Clear any existing deductions for this outward (idempotent re-processing)
    await sql`DELETE FROM fifo_deductions WHERE outward_id = ${outwardId}`;

    const deductions: FifoDeduction[] = [];

    for (const oi of outwardItems) {
      let remainingToDeduct = Number(oi.quantity);
      if (remainingToDeduct <= 0) continue;

      // Find all matching inward items for this MS Party + Item + Measurement
      // sorted by inward date ASC (FIFO order), then by inward ID ASC
      const matchingInwardItems = await sql`
        SELECT 
          ii.id as inward_item_id, 
          ii.inward_id,
          ii.item_id,
          ii.measurement,
          ii.quantity as original_qty,
          COALESCE(
            (SELECT SUM(fd.deducted_qty) FROM fifo_deductions fd WHERE fd.inward_item_id = ii.id),
            0
          ) as already_deducted
        FROM inward_items ii
        JOIN inwards i ON ii.inward_id = i.id
        WHERE i.ms_party_id = ${outward.ms_party_id}
          AND ii.item_id = ${oi.item_id}
          AND ii.measurement = ${oi.measurement}
        ORDER BY i.date ASC, i.id ASC
      `;

      for (const inItem of matchingInwardItems) {
        if (remainingToDeduct <= 0) break;

        const available = Number(inItem.original_qty) - Number(inItem.already_deducted);
        if (available <= 0) continue;

        const deductAmount = Math.min(remainingToDeduct, available);

        await sql`
          INSERT INTO fifo_deductions (
            outward_id, outward_item_id, inward_id, inward_item_id,
            item_id, measurement, ms_party_id, deducted_qty
          ) VALUES (
            ${outwardId}, ${oi.outward_item_id}, ${inItem.inward_id}, ${inItem.inward_item_id},
            ${oi.item_id}, ${oi.measurement}, ${outward.ms_party_id}, ${deductAmount}
          )
        `;

        deductions.push({
          outward_id: outwardId,
          outward_item_id: oi.outward_item_id,
          inward_id: inItem.inward_id,
          inward_item_id: inItem.inward_item_id,
          item_id: oi.item_id,
          measurement: oi.measurement,
          ms_party_id: outward.ms_party_id,
          deducted_qty: deductAmount,
        });

        remainingToDeduct -= deductAmount;
      }

      // If remainingToDeduct > 0, there's a deficit (outward exceeds available inward stock)
      // We don't block this — we just won't have a full deduction log for it.
      // The UI will show the deficit.
    }

    return deductions;
  },

  async processTransferFifo(transferId: number) {
    const sql = getDb();

    const rows = await sql`
      SELECT id, ms_party_id, date FROM transfers WHERE id = ${transferId}
    `;
    if (rows.length === 0) return [];

    const transfer = rows[0];

    const transferItems = await sql`
      SELECT id as transfer_item_id, item_id, measurement, quantity
      FROM transfer_items WHERE transfer_id = ${transferId}
    `;

    await sql`DELETE FROM fifo_deductions WHERE transfer_id = ${transferId}`;

    const deductions: FifoDeduction[] = [];

    for (const ti of transferItems) {
      let remainingToDeduct = Number(ti.quantity);
      if (remainingToDeduct <= 0) continue;

      const matchingInwardItems = await sql`
        SELECT 
          ii.id as inward_item_id, 
          ii.inward_id,
          ii.item_id,
          ii.measurement,
          ii.quantity as original_qty,
          COALESCE(
            (SELECT SUM(fd.deducted_qty) FROM fifo_deductions fd WHERE fd.inward_item_id = ii.id),
            0
          ) as already_deducted
        FROM inward_items ii
        JOIN inwards i ON ii.inward_id = i.id
        WHERE i.ms_party_id = ${transfer.ms_party_id}
          AND ii.item_id = ${ti.item_id}
          AND ii.measurement = ${ti.measurement}
        ORDER BY i.date ASC, i.id ASC
      `;

      for (const inItem of matchingInwardItems) {
        if (remainingToDeduct <= 0) break;

        const available = Number(inItem.original_qty) - Number(inItem.already_deducted);
        if (available <= 0) continue;

        const deductAmount = Math.min(remainingToDeduct, available);

        await sql`
          INSERT INTO fifo_deductions (
            transfer_id, transfer_item_id, inward_id, inward_item_id,
            item_id, measurement, ms_party_id, deducted_qty
          ) VALUES (
            ${transferId}, ${ti.transfer_item_id}, ${inItem.inward_id}, ${inItem.inward_item_id},
            ${ti.item_id}, ${ti.measurement}, ${transfer.ms_party_id}, ${deductAmount}
          )
        `;

        deductions.push({
          transfer_id: transferId,
          transfer_item_id: ti.transfer_item_id,
          inward_id: inItem.inward_id,
          inward_item_id: inItem.inward_item_id,
          item_id: ti.item_id,
          measurement: ti.measurement,
          ms_party_id: transfer.ms_party_id,
          deducted_qty: deductAmount,
        });

        remainingToDeduct -= deductAmount;
      }
    }

    return deductions;
  },

  /**
   * Remove all FIFO deductions for an outward (called before delete/update).
   */
  async clearOutwardDeductions(outwardId: number) {
    const sql = getDb();
    await sql`DELETE FROM fifo_deductions WHERE outward_id = ${outwardId}`;
  },

  async clearTransferDeductions(transferId: number) {
    const sql = getDb();
    await sql`DELETE FROM fifo_deductions WHERE transfer_id = ${transferId}`;
  },

  /**
   * Get per-item breakdown for a specific inward entry.
   * Shows: item name, original qty, total deducted qty, remaining qty.
   */
  async getInwardItemBreakdown(inwardId: number): Promise<InwardItemBreakdown[]> {
    const sql = getDb();
    
    const rows = await sql`
      SELECT 
        ii.id as inward_item_id,
        ii.item_id,
        it.name as item_name,
        ii.measurement,
        ii.quantity as original_qty,
        COALESCE(SUM(CASE WHEN fd.outward_id IS NOT NULL THEN fd.deducted_qty ELSE 0 END), 0) as outward_qty,
        COALESCE(SUM(CASE WHEN fd.transfer_id IS NOT NULL OR fd.tbn_id IS NOT NULL THEN fd.deducted_qty ELSE 0 END), 0) as transfer_qty,
        COALESCE(SUM(fd.deducted_qty), 0) as total_deducted_qty
      FROM inward_items ii
      JOIN items it ON ii.item_id = it.id
      LEFT JOIN fifo_deductions fd ON fd.inward_item_id = ii.id
      WHERE ii.inward_id = ${inwardId}
      GROUP BY ii.id, ii.item_id, it.name, ii.measurement, ii.quantity
      ORDER BY it.name ASC, ii.measurement ASC
    `;

    return rows.map(r => ({
      inward_item_id: r.inward_item_id,
      item_id: r.item_id,
      item_name: r.item_name,
      measurement: Number(r.measurement),
      original_qty: Number(r.original_qty),
      deducted_qty: Number(r.total_deducted_qty),
      outward_qty: Number(r.outward_qty),
      transfer_qty: Number(r.transfer_qty),
      remaining_qty: Number(r.original_qty) - Number(r.total_deducted_qty),
    }));
  },

  /**
   * Get FIFO breakdown for ALL inwards of a given MS Party (bulk query for list view).
   * Returns a map: inward_id -> InwardItemBreakdown[]
   */
  async getInwardBreakdownsByParty(msPartyId?: number): Promise<Record<number, InwardItemBreakdown[]>> {
    const sql = getDb();
    
    const rows = await sql`
      SELECT 
        ii.inward_id,
        ii.id as inward_item_id,
        ii.item_id,
        it.name as item_name,
        ii.measurement,
        ii.quantity as original_qty,
        COALESCE(SUM(CASE WHEN fd.outward_id IS NOT NULL THEN fd.deducted_qty ELSE 0 END), 0) as outward_qty,
        COALESCE(SUM(CASE WHEN fd.transfer_id IS NOT NULL OR fd.tbn_id IS NOT NULL THEN fd.deducted_qty ELSE 0 END), 0) as transfer_qty,
        COALESCE(SUM(fd.deducted_qty), 0) as total_deducted_qty
      FROM inward_items ii
      JOIN items it ON ii.item_id = it.id
      JOIN inwards i ON ii.inward_id = i.id
      LEFT JOIN fifo_deductions fd ON fd.inward_item_id = ii.id
      WHERE (${msPartyId || null}::integer IS NULL OR i.ms_party_id = ${msPartyId || null}::integer)
      GROUP BY ii.inward_id, ii.id, ii.item_id, it.name, ii.measurement, ii.quantity
      ORDER BY it.name ASC, ii.measurement ASC
    `;

    const result: Record<number, InwardItemBreakdown[]> = {};
    for (const r of rows) {
      const inwardId = r.inward_id;
      if (!result[inwardId]) result[inwardId] = [];
      result[inwardId].push({
        inward_item_id: r.inward_item_id,
        item_id: r.item_id,
        item_name: r.item_name,
        measurement: Number(r.measurement),
        original_qty: Number(r.original_qty),
        deducted_qty: Number(r.total_deducted_qty),
        outward_qty: Number(r.outward_qty),
        transfer_qty: Number(r.transfer_qty),
        remaining_qty: Number(r.original_qty) - Number(r.total_deducted_qty),
      });
    }
    return result;
  },

  /**
   * Run the full FIFO migration for ALL existing outwards.
   * Processes outwards in chronological order (oldest first).
   * This is idempotent — it clears and re-creates all deductions.
   */
  async runFullMigration(): Promise<{ processed: number; totalDeductions: number }> {
    const sql = getDb();
    
    // Clear ALL existing deductions first for clean slate
    await sql`DELETE FROM fifo_deductions`;

    const allOutwards = await sql`SELECT id, date, 'outward' as type FROM outwards`;
    const allTransfers = await sql`SELECT id, date, 'transfer' as type FROM transfers`;
    const allTbns = await sql`SELECT id, date, 'tbn' as type FROM transfer_by_names`;
    
    const combined = [...allOutwards, ...allTransfers, ...allTbns].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime() || a.id - b.id
    );

    let totalDeductions = 0;

    for (const doc of combined) {
      if (doc.type === 'outward') {
        const deductions = await this.processOutwardFifo(doc.id);
        totalDeductions += deductions.length;
      } else if (doc.type === 'transfer') {
        const deductions = await this.processTransferFifo(doc.id);
        totalDeductions += deductions.length;
      } else {
        const deductions = await this.processTbnFifo(doc.id);
        totalDeductions += deductions.length;
      }
    }

    return { processed: combined.length, totalDeductions };
  },

  /**
   * Get deduction details for a specific outward (which inwards were consumed).
   */
  async getOutwardDeductions(outwardId: number): Promise<OutwardDeductionDetail[]> {
    const sql = getDb();
    const rows = await sql`
      SELECT 
        fd.*,
        i.inward_no,
        i.gp_no as inward_gp_no,
        i.ms_party_gp_no as inward_ms_party_gp_no,
        fp.name as from_party_name,
        it.name as item_name
      FROM fifo_deductions fd
      JOIN inwards i ON fd.inward_id = i.id
      JOIN items it ON fd.item_id = it.id
      LEFT JOIN from_parties fp ON i.from_party_id = fp.id
      WHERE fd.outward_id = ${outwardId}
      ORDER BY i.date ASC
    `;
    return rows.map(r => ({
      ...r,
      deducted_qty: Number(r.deducted_qty),
      measurement: Number(r.measurement)
    })) as OutwardDeductionDetail[];
  },

  /**
   * Get deduction details for ALL outwards of a given MS Party (bulk query for list view).
   * Returns a map: outward_id -> OutwardDeductionDetail[]
   */
  async getOutwardDeductionsByParty(msPartyId?: number): Promise<Record<number, OutwardDeductionDetail[]>> {
    const sql = getDb();
    const rows = await sql`
      SELECT 
        fd.*,
        i.inward_no,
        i.gp_no as inward_gp_no,
        i.ms_party_gp_no as inward_ms_party_gp_no,
        fp.name as from_party_name,
        it.name as item_name
      FROM fifo_deductions fd
      JOIN inwards i ON fd.inward_id = i.id
      JOIN items it ON fd.item_id = it.id
      LEFT JOIN from_parties fp ON i.from_party_id = fp.id
      JOIN outwards o ON fd.outward_id = o.id
      WHERE (${msPartyId || null}::integer IS NULL OR o.ms_party_id = ${msPartyId || null}::integer)
      ORDER BY i.date ASC
    `;

    const result: Record<number, OutwardDeductionDetail[]> = {};
    for (const r of rows) {
      const outId = r.outward_id;
      if (!result[outId]) result[outId] = [];
      result[outId].push({
        ...r,
        deducted_qty: Number(r.deducted_qty),
        measurement: Number(r.measurement)
      } as OutwardDeductionDetail);
    }
    return result;
  },

  async getTransferDeductions(transferId: number): Promise<OutwardDeductionDetail[]> {
    const sql = getDb();
    const rows = await sql`
      SELECT 
        fd.*,
        i.inward_no,
        i.gp_no as inward_gp_no,
        i.ms_party_gp_no as inward_ms_party_gp_no,
        fp.name as from_party_name,
        it.name as item_name
      FROM fifo_deductions fd
      JOIN inwards i ON fd.inward_id = i.id
      JOIN items it ON fd.item_id = it.id
      LEFT JOIN from_parties fp ON i.from_party_id = fp.id
      WHERE fd.transfer_id = ${transferId}
      ORDER BY i.date ASC
    `;
    return rows.map(r => ({
      ...r,
      deducted_qty: Number(r.deducted_qty),
      measurement: Number(r.measurement)
    })) as OutwardDeductionDetail[];
  },

  async getTransferDeductionsByParty(msPartyId?: number): Promise<Record<number, OutwardDeductionDetail[]>> {
    const sql = getDb();
    const rows = await sql`
      SELECT 
        fd.*,
        i.inward_no,
        i.gp_no as inward_gp_no,
        i.ms_party_gp_no as inward_ms_party_gp_no,
        fp.name as from_party_name,
        it.name as item_name
      FROM fifo_deductions fd
      JOIN inwards i ON fd.inward_id = i.id
      JOIN items it ON fd.item_id = it.id
      LEFT JOIN from_parties fp ON i.from_party_id = fp.id
      JOIN transfers t ON fd.transfer_id = t.id
      WHERE (${msPartyId || null}::integer IS NULL OR t.ms_party_id = ${msPartyId || null}::integer)
      ORDER BY i.date ASC
    `;

    const result: Record<number, OutwardDeductionDetail[]> = {};
    for (const r of rows) {
      const transId = r.transfer_id;
      if (!result[transId]) result[transId] = [];
      result[transId].push({
        ...r,
        deducted_qty: Number(r.deducted_qty),
        measurement: Number(r.measurement)
      } as OutwardDeductionDetail);
    }
    return result;
  },

  async processTbnFifo(tbnId: number) {
    const sql = getDb();

    const rows = await sql`
      SELECT id, ms_party_id, date FROM transfer_by_names WHERE id = ${tbnId}
    `;
    if (rows.length === 0) return [];

    const tbn = rows[0];

    const tbnItems = await sql`
      SELECT id as tbn_item_id, item_id, measurement, quantity
      FROM transfer_bn_items WHERE tbn_id = ${tbnId}
    `;

    await sql`DELETE FROM fifo_deductions WHERE tbn_id = ${tbnId}`;

    const deductions: FifoDeduction[] = [];

    for (const ti of tbnItems) {
      let remainingToDeduct = Number(ti.quantity);
      if (remainingToDeduct <= 0) continue;

      const matchingInwardItems = await sql`
        SELECT 
          ii.id as inward_item_id, 
          ii.inward_id,
          ii.item_id,
          ii.measurement,
          ii.quantity as original_qty,
          COALESCE(
            (SELECT SUM(fd.deducted_qty) FROM fifo_deductions fd WHERE fd.inward_item_id = ii.id),
            0
          ) as already_deducted
        FROM inward_items ii
        JOIN inwards i ON ii.inward_id = i.id
        WHERE i.ms_party_id = ${tbn.ms_party_id}
          AND ii.item_id = ${ti.item_id}
          AND ii.measurement = ${ti.measurement}
        ORDER BY i.date ASC, i.id ASC
      `;

      for (const inItem of matchingInwardItems) {
        if (remainingToDeduct <= 0) break;

        const available = Number(inItem.original_qty) - Number(inItem.already_deducted);
        if (available <= 0) continue;

        const deductAmount = Math.min(remainingToDeduct, available);

        await sql`
          INSERT INTO fifo_deductions (
            tbn_id, tbn_item_id, inward_id, inward_item_id,
            item_id, measurement, ms_party_id, deducted_qty
          ) VALUES (
            ${tbnId}, ${ti.tbn_item_id}, ${inItem.inward_id}, ${inItem.inward_item_id},
            ${ti.item_id}, ${ti.measurement}, ${tbn.ms_party_id}, ${deductAmount}
          )
        `;

        deductions.push({
          tbn_id: tbnId,
          tbn_item_id: ti.tbn_item_id,
          inward_id: inItem.inward_id,
          inward_item_id: inItem.inward_item_id,
          item_id: ti.item_id,
          measurement: ti.measurement,
          ms_party_id: tbn.ms_party_id,
          deducted_qty: deductAmount,
        });

        remainingToDeduct -= deductAmount;
      }
    }

    return deductions;
  },

  async clearTbnDeductions(tbnId: number) {
    const sql = getDb();
    await sql`DELETE FROM fifo_deductions WHERE tbn_id = ${tbnId}`;
  },

  async getTbnDeductions(tbnId: number): Promise<OutwardDeductionDetail[]> {
    const sql = getDb();
    const rows = await sql`
      SELECT 
        fd.*,
        i.inward_no,
        i.gp_no as inward_gp_no,
        i.ms_party_gp_no as inward_ms_party_gp_no,
        fp.name as from_party_name,
        it.name as item_name
      FROM fifo_deductions fd
      JOIN inwards i ON fd.inward_id = i.id
      JOIN items it ON fd.item_id = it.id
      LEFT JOIN from_parties fp ON i.from_party_id = fp.id
      WHERE fd.tbn_id = ${tbnId}
      ORDER BY i.date ASC
    `;
    return rows.map(r => ({
      ...r,
      deducted_qty: Number(r.deducted_qty),
      measurement: Number(r.measurement)
    })) as OutwardDeductionDetail[];
  },

  async getTbnDeductionsByParty(msPartyId?: number): Promise<Record<number, OutwardDeductionDetail[]>> {
    const sql = getDb();
    const rows = await sql`
      SELECT 
        fd.*,
        i.inward_no,
        i.gp_no as inward_gp_no,
        i.ms_party_gp_no as inward_ms_party_gp_no,
        fp.name as from_party_name,
        it.name as item_name
      FROM fifo_deductions fd
      JOIN inwards i ON fd.inward_id = i.id
      JOIN items it ON fd.item_id = it.id
      LEFT JOIN from_parties fp ON i.from_party_id = fp.id
      JOIN transfer_by_names t ON fd.tbn_id = t.id
      WHERE (${msPartyId || null}::integer IS NULL OR t.ms_party_id = ${msPartyId || null}::integer)
      ORDER BY i.date ASC
    `;

    const result: Record<number, OutwardDeductionDetail[]> = {};
    for (const r of rows) {
      const tId = r.tbn_id;
      if (!result[tId]) result[tId] = [];
      result[tId].push({
        ...r,
        deducted_qty: Number(r.deducted_qty),
        measurement: Number(r.measurement)
      } as OutwardDeductionDetail);
    }
    return result;
  },
};
