import type { VercelRequest, VercelResponse } from '@vercel/node';
import { initializeDatabase } from './_lib/db.js';
import { msPartiesService, type MsParty } from './_lib/services/ms-parties.js';
import { vendorsService, type Vendor } from './_lib/services/vendors.js';
import { assetsService, type Asset } from './_lib/services/assets.js';
import { expensesService, type ExpenseCategory, type Expense } from './_lib/services/expenses.js';

let dbInitialized = false;

/**
 * Core API handler — single serverless function that routes all CRUD operations
 * via the `action` parameter. This keeps the function count minimal on Vercel free tier.
 * 
 * Usage: POST /api/core { action: "ms_parties.list", data: {...} }
 * Usage: GET  /api/core?action=ms_parties.list&search=xxx
 */
export default async function handler(req: VercelRequest, res: VercelResponse) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    // Lazy DB init
    if (!dbInitialized) {
      await initializeDatabase();
      dbInitialized = true;
    }

    // Extract action from query or body
    const action = (req.query.action as string) || (req.body?.action as string);
    if (!action) {
      return res.status(400).json({ 
        success: false, 
        error: 'Missing "action" parameter. Format: entity.operation (e.g., ms_parties.list)' 
      });
    }

    const data = req.body?.data || {};
    const query = req.query;

    const result = await routeAction(action, data, query);
    return res.status(200).json({ success: true, data: result });
  } catch (error: any) {
    console.error('[API Core Error]', error);
    const status = error.message?.includes('already exists') ? 409
      : error.message?.includes('not found') ? 404
      : 500;
    return res.status(status).json({ 
      success: false, 
      error: error.message || 'Internal server error' 
    });
  }
}

/**
 * Internal router — maps action strings to service methods
 */
async function routeAction(
  action: string, 
  data: Record<string, any>, 
  query: Record<string, string | string[] | undefined>
) {
  const [entity, operation] = action.split('.');

  switch (entity) {
    // ─── MS Parties ────────────────────────────────────────────
    case 'ms_parties':
      switch (operation) {
        case 'list':
          return msPartiesService.list(
            (query.search as string) || data.search,
            (query.status as string) || data.status
          );
        case 'get':
          return msPartiesService.getById(Number(query.id || data.id));
        case 'create':
          return msPartiesService.create(data as MsParty);
        case 'update':
          return msPartiesService.update(Number(data.id), data);
        case 'delete':
          return msPartiesService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for ms_parties`);
      }

    // ─── Vendors ───────────────────────────────────────────────
    case 'vendors':
      switch (operation) {
        case 'list':
          return vendorsService.list(
            (query.search as string) || data.search,
            (query.status as string) || data.status
          );
        case 'get':
          return vendorsService.getById(Number(query.id || data.id));
        case 'create':
          return vendorsService.create(data as Vendor);
        case 'update':
          return vendorsService.update(Number(data.id), data);
        case 'delete':
          return vendorsService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for vendors`);
      }

    // ─── Assets ────────────────────────────────────────────────
    case 'assets':
      switch (operation) {
        case 'list':
          return assetsService.list(
            (query.search as string) || data.search,
            (query.status as string) || data.status,
            (query.category as string) || data.category
          );
        case 'get':
          return assetsService.getById(Number(query.id || data.id));
        case 'create':
          return assetsService.create(data as Asset);
        case 'update':
          return assetsService.update(Number(data.id), data);
        case 'delete':
          return assetsService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for assets`);
      }

    // ─── Expense Categories ────────────────────────────────────
    case 'expense_categories':
      switch (operation) {
        case 'list':
          return expensesService.listCategories(
            (query.search as string) || data.search
          );
        case 'get':
          return expensesService.getCategoryById(Number(query.id || data.id));
        case 'create':
          return expensesService.createCategory(data as ExpenseCategory);
        case 'update':
          return expensesService.updateCategory(Number(data.id), data);
        case 'delete':
          return expensesService.deleteCategory(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for expense_categories`);
      }

    // ─── Expenses ──────────────────────────────────────────────
    case 'expenses':
      switch (operation) {
        case 'list':
          return expensesService.listExpenses(
            query.category_id ? Number(query.category_id) : data.category_id,
            (query.search as string) || data.search
          );
        case 'get':
          return expensesService.getExpenseById(Number(query.id || data.id));
        case 'create':
          return expensesService.createExpense(data as Expense);
        case 'update':
          return expensesService.updateExpense(Number(data.id), data);
        case 'delete':
          return expensesService.deleteExpense(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for expenses`);
      }

    default:
      throw new Error(`Unknown entity: ${entity}. Available: ms_parties, vendors, assets, expense_categories, expenses`);
  }
}
