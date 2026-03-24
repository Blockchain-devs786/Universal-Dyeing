import { getDb } from '../db.js';

export interface ExpenseCategory {
  id?: number;
  name: string;
  description?: string;
  status?: string;
}

export interface Expense {
  id?: number;
  name: string;
  category_id: number;
  description?: string;
  status?: string;
}

async function logActivity(entityType: string, entityId: number | null, action: string, details: Record<string, unknown> = {}) {
  const sql = getDb();
  await sql`INSERT INTO activity_log (entity_type, entity_id, action, details) VALUES (${entityType}, ${entityId}, ${action}, ${JSON.stringify(details)})`;
}

export const expensesService = {
  // ─── Category Operations ───────────────────────────────────────

  async listCategories(search?: string) {
    const sql = getDb();
    if (search) {
      return sql`SELECT * FROM expense_categories WHERE name ILIKE ${'%' + search + '%'} ORDER BY name ASC`;
    }
    return sql`SELECT * FROM expense_categories ORDER BY name ASC`;
  },

  async getCategoryById(id: number) {
    const sql = getDb();
    const rows = await sql`SELECT * FROM expense_categories WHERE id = ${id}`;
    return rows[0] || null;
  },

  async createCategory(data: ExpenseCategory) {
    const sql = getDb();
    const existing = await sql`SELECT id FROM expense_categories WHERE LOWER(name) = LOWER(${data.name})`;
    if (existing.length > 0) {
      throw new Error(`Expense category "${data.name}" already exists`);
    }
    const rows = await sql`
      INSERT INTO expense_categories (name, description, status)
      VALUES (${data.name}, ${data.description || null}, ${data.status || 'active'})
      RETURNING *
    `;
    await logActivity('expense_categories', rows[0].id, 'create', { name: data.name });
    return rows[0];
  },

  async updateCategory(id: number, data: Partial<ExpenseCategory>) {
    const sql = getDb();
    if (data.name) {
      const existing = await sql`SELECT id FROM expense_categories WHERE LOWER(name) = LOWER(${data.name}) AND id != ${id}`;
      if (existing.length > 0) {
        throw new Error(`Expense category "${data.name}" already exists`);
      }
    }
    const rows = await sql`
      UPDATE expense_categories SET
        name = COALESCE(${data.name ?? null}, name),
        description = COALESCE(${data.description ?? null}, description),
        status = COALESCE(${data.status ?? null}, status),
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    if (rows.length === 0) throw new Error('Expense category not found');
    await logActivity('expense_categories', id, 'update', data);
    return rows[0];
  },

  async deleteCategory(id: number) {
    const sql = getDb();
    const rows = await sql`DELETE FROM expense_categories WHERE id = ${id} RETURNING id, name`;
    if (rows.length === 0) throw new Error('Expense category not found');
    await logActivity('expense_categories', id, 'delete', { name: rows[0].name });
    return { success: true, deleted: rows[0] };
  },

  // ─── Expense Operations ───────────────────────────────────────

  async listExpenses(categoryId?: number, search?: string) {
    const sql = getDb();
    if (categoryId && search) {
      return sql`
        SELECT e.*, ec.name as category_name FROM expenses e 
        JOIN expense_categories ec ON e.category_id = ec.id
        WHERE e.category_id = ${categoryId} AND e.name ILIKE ${'%' + search + '%'}
        ORDER BY e.name ASC
      `;
    }
    if (categoryId) {
      return sql`
        SELECT e.*, ec.name as category_name FROM expenses e 
        JOIN expense_categories ec ON e.category_id = ec.id
        WHERE e.category_id = ${categoryId} ORDER BY e.name ASC
      `;
    }
    if (search) {
      return sql`
        SELECT e.*, ec.name as category_name FROM expenses e 
        JOIN expense_categories ec ON e.category_id = ec.id
        WHERE e.name ILIKE ${'%' + search + '%'}
        ORDER BY ec.name ASC, e.name ASC
      `;
    }
    return sql`
      SELECT e.*, ec.name as category_name FROM expenses e 
      JOIN expense_categories ec ON e.category_id = ec.id
      ORDER BY ec.name ASC, e.name ASC
    `;
  },

  async getExpenseById(id: number) {
    const sql = getDb();
    const rows = await sql`
      SELECT e.*, ec.name as category_name FROM expenses e 
      JOIN expense_categories ec ON e.category_id = ec.id WHERE e.id = ${id}
    `;
    return rows[0] || null;
  },

  async createExpense(data: Expense) {
    const sql = getDb();
    const category = await sql`SELECT id FROM expense_categories WHERE id = ${data.category_id}`;
    if (category.length === 0) {
      throw new Error('Expense category not found');
    }
    const existing = await sql`
      SELECT id FROM expenses WHERE LOWER(name) = LOWER(${data.name}) AND category_id = ${data.category_id}
    `;
    if (existing.length > 0) {
      throw new Error(`Expense "${data.name}" already exists in this category`);
    }
    const rows = await sql`
      INSERT INTO expenses (name, category_id, description, status)
      VALUES (${data.name}, ${data.category_id}, ${data.description || null}, ${data.status || 'active'})
      RETURNING *
    `;
    const result = await sql`
      SELECT e.*, ec.name as category_name FROM expenses e 
      JOIN expense_categories ec ON e.category_id = ec.id WHERE e.id = ${rows[0].id}
    `;
    await logActivity('expenses', rows[0].id, 'create', { name: data.name, category_id: data.category_id });
    return result[0];
  },

  async updateExpense(id: number, data: Partial<Expense>) {
    const sql = getDb();
    if (data.name) {
      const current = await sql`SELECT category_id FROM expenses WHERE id = ${id}`;
      const catId = data.category_id || (current.length > 0 ? current[0].category_id : null);
      if (catId) {
        const existing = await sql`
          SELECT id FROM expenses WHERE LOWER(name) = LOWER(${data.name}) AND category_id = ${catId} AND id != ${id}
        `;
        if (existing.length > 0) {
          throw new Error(`Expense "${data.name}" already exists in this category`);
        }
      }
    }
    const rows = await sql`
      UPDATE expenses SET
        name = COALESCE(${data.name ?? null}, name),
        category_id = COALESCE(${data.category_id ?? null}, category_id),
        description = COALESCE(${data.description ?? null}, description),
        status = COALESCE(${data.status ?? null}, status),
        updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `;
    if (rows.length === 0) throw new Error('Expense not found');
    const result = await sql`
      SELECT e.*, ec.name as category_name FROM expenses e 
      JOIN expense_categories ec ON e.category_id = ec.id WHERE e.id = ${id}
    `;
    await logActivity('expenses', id, 'update', data);
    return result[0];
  },

  async deleteExpense(id: number) {
    const sql = getDb();
    const rows = await sql`DELETE FROM expenses WHERE id = ${id} RETURNING id, name`;
    if (rows.length === 0) throw new Error('Expense not found');
    await logActivity('expenses', id, 'delete', { name: rows[0].name });
    return { success: true, deleted: rows[0] };
  },
};
