import { getDb } from '../db.js';

export interface AssetCategory {
  id?: number;
  name: string;
  description?: string;
  status?: string;
}

export interface Asset {
  id?: number;
  name: string;
  category_id: number;
  description?: string;
  value?: number;
  location?: string;
  status?: string;
  purchase_date?: string;
}

async function logActivity(entityType: string, entityId: number | null, action: string, details: Record<string, unknown> = {}) {
  const sql = getDb();
  await sql`INSERT INTO activity_log (entity_type, entity_id, action, details) VALUES (${entityType}, ${entityId}, ${action}, ${JSON.stringify(details)})`;
}

export const assetsService = {
  // ─── Category Operations ───────────────────────────────────────

  async listCategories(search?: string) {
    const sql = getDb();
    if (search) {
      return sql`SELECT * FROM asset_categories WHERE name ILIKE ${'%' + search + '%'} ORDER BY name ASC`;
    }
    return sql`SELECT * FROM asset_categories ORDER BY name ASC`;
  },

  async getCategoryById(id: number) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM asset_categories WHERE id = ${id}`;
    return rows[0] || null;
  },

  async createCategory(data: AssetCategory) {
    const sql = getDb();
    const existing = await sql`SELECT id FROM asset_categories WHERE LOWER(name) = LOWER(${data.name})`;
    if (existing.length > 0) {
      throw new Error(`Asset category "${data.name}" already exists`);
    }
    const rows = await sql`
      INSERT INTO asset_categories (name, description, status)
      VALUES (${data.name}, ${data.description || null}, ${data.status || 'active'})
      RETURNING *
    `;
    await logActivity('asset_categories', rows[0].id, 'create', { name: data.name });
    return rows[0];
  },

  async updateCategory(id: number, data: Partial<AssetCategory>) {
    const sql = getDb();
    if (data.name) {
      const existing = await sql`SELECT id FROM asset_categories WHERE LOWER(name) = LOWER(${data.name}) AND id != ${id}`;
      if (existing.length > 0) {
        throw new Error(`Asset category "${data.name}" already exists`);
      }
    }
    const rows = await sql`
      UPDATE asset_categories SET
        name = COALESCE(${data.name ?? null}, name),
        description = COALESCE(${data.description ?? null}, description),
        status = COALESCE(${data.status ?? null}, status),
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    if (rows.length === 0) throw new Error('Asset category not found');
    await logActivity('asset_categories', id, 'update', data);
    return rows[0];
  },

  async deleteCategory(id: number) {
    const sql = getDb();
    const rows = await sql`DELETE FROM asset_categories WHERE id = ${id} RETURNING id, name`;
    if (rows.length === 0) throw new Error('Asset category not found');
    await logActivity('asset_categories', id, 'delete', { name: rows[0].name });
    return { success: true, deleted: rows[0] };
  },

  // ─── Asset Operations ──────────────────────────────────────────

  async listAssets(categoryId?: number, search?: string) {
    const sql = getDb();
    if (categoryId && search) {
      return sql`
        SELECT a.*, ac.name as category_name FROM assets a 
        LEFT JOIN asset_categories ac ON a.category_id = ac.id
        WHERE a.category_id = ${categoryId} AND a.name ILIKE ${'%' + search + '%'}
        ORDER BY a.name ASC
      `;
    }
    if (categoryId) {
      return sql`
        SELECT a.*, ac.name as category_name FROM assets a 
        LEFT JOIN asset_categories ac ON a.category_id = ac.id
        WHERE a.category_id = ${categoryId} ORDER BY a.name ASC
      `;
    }
    if (search) {
      return sql`
        SELECT a.*, ac.name as category_name FROM assets a 
        LEFT JOIN asset_categories ac ON a.category_id = ac.id
        WHERE a.name ILIKE ${'%' + search + '%'}
        ORDER BY ac.name ASC, a.name ASC
      `;
    }
    return sql`
      SELECT a.*, ac.name as category_name FROM assets a 
      LEFT JOIN asset_categories ac ON a.category_id = ac.id
      ORDER BY ac.name ASC, a.name ASC
    `;
  },

  async getAssetById(id: number) {
    const sql = getDb();
    const rows = await sql`
      SELECT a.*, ac.name as category_name FROM assets a 
      LEFT JOIN asset_categories ac ON a.category_id = ac.id WHERE a.id = ${id}
    `;
    return rows[0] || null;
  },

  async createAsset(data: Asset) {
    const sql = getDb();
    // Verify category exists if provided
    if (data.category_id) {
      const category = await sql`SELECT id FROM asset_categories WHERE id = ${data.category_id}`;
      if (category.length === 0) {
        throw new Error('Asset category not found');
      }
    }
    
    // Check for duplicate name in same category
    const existing = await sql`
      SELECT id FROM assets WHERE LOWER(name) = LOWER(${data.name}) 
      ${data.category_id ? sql`AND category_id = ${data.category_id}` : sql`AND category_id IS NULL`}
    `;
    if (existing.length > 0) {
      throw new Error(`Asset "${data.name}" already exists in this category`);
    }

    const rows = await sql`
      INSERT INTO assets (name, category_id, description, value, location, status, purchase_date)
      VALUES (${data.name}, ${data.category_id || null}, ${data.description || null}, 
              ${data.value || 0}, ${data.location || null}, ${data.status || 'active'},
              ${data.purchase_date || null})
      RETURNING *
    `;
    
    const result = await sql`
      SELECT a.*, ac.name as category_name FROM assets a 
      LEFT JOIN asset_categories ac ON a.category_id = ac.id WHERE a.id = ${rows[0].id}
    `;
    await logActivity('assets', rows[0].id, 'create', { name: data.name, category_id: data.category_id });
    return result[0];
  },

  async updateAsset(id: number, data: Partial<Asset>) {
    const sql = getDb();
    if (data.name) {
      const current = await sql`SELECT category_id FROM assets WHERE id = ${id}`;
      const catId = data.category_id !== undefined ? data.category_id : (current.length > 0 ? current[0].category_id : null);
      
      const existing = await sql`
        SELECT id FROM assets WHERE LOWER(name) = LOWER(${data.name}) 
        ${catId ? sql`AND category_id = ${catId}` : sql`AND category_id IS NULL`} 
        AND id != ${id}
      `;
      if (existing.length > 0) {
        throw new Error(`Asset "${data.name}" already exists in this category`);
      }
    }
    const rows = await sql`
      UPDATE assets SET
        name = COALESCE(${data.name ?? null}, name),
        category_id = COALESCE(${data.category_id ?? null}, category_id),
        description = COALESCE(${data.description ?? null}, description),
        value = COALESCE(${data.value ?? null}, value),
        location = COALESCE(${data.location ?? null}, location),
        status = COALESCE(${data.status ?? null}, status),
        purchase_date = COALESCE(${data.purchase_date ?? null}, purchase_date),
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    if (rows.length === 0) throw new Error('Asset not found');
    
    const result = await sql`
      SELECT a.*, ac.name as category_name FROM assets a 
      LEFT JOIN asset_categories ac ON a.category_id = ac.id WHERE a.id = ${id}
    `;
    await logActivity('assets', id, 'update', data);
    return result[0];
  },

  async deleteAsset(id: number) {
    const sql = getDb();
    const rows = await sql`DELETE FROM assets WHERE id = ${id} RETURNING id, name`;
    if (rows.length === 0) throw new Error('Asset not found');
    await logActivity('assets', id, 'delete', { name: rows[0].name });
    return { success: true, deleted: rows[0] };
  },
};
