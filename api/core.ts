import type { VercelRequest, VercelResponse } from '@vercel/node';
import { initializeDatabase } from './_lib/db.js';
import { msPartiesService, type MsParty } from './_lib/services/ms-parties.js';
import { fromPartiesService, type FromParty } from './_lib/services/from-parties.js';
import { suppliersService, type Supplier } from './_lib/services/suppliers.js';
import { itemsService, type Item } from './_lib/services/items.js';
import { inwardsService, type Inward } from './_lib/services/inwards.js';
import { assetsService, type Asset, type AssetCategory } from './_lib/services/assets.js';
import { expensesService, type ExpenseCategory, type Expense } from './_lib/services/expenses.js';
import { outwardsService, type Outward } from './_lib/services/outwards.js';
import { transfersService, type Transfer } from './_lib/services/transfers.js';
import { transferByNamesService, type TransferByName } from './_lib/services/transfer_by_names.js';
import { reportsService } from './_lib/services/reports.js';
import { invoicesService, type Invoice } from './_lib/services/invoices.js';
import { accountsService } from './_lib/services/accounts.js';
import { vouchersService } from './_lib/services/vouchers.js';
import { settingsService } from './_lib/services/settings.js';
import { outwardPartiesService, type OutwardParty } from './_lib/services/outward-parties.js';

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

    // ─── From Parties ──────────────────────────────────────────
    case 'from_parties':
      switch (operation) {
        case 'list':
          return fromPartiesService.list(
            (query.search as string) || data.search,
            (query.status as string) || data.status
          );
        case 'get':
          return fromPartiesService.getById(Number(query.id || data.id));
        case 'create':
          return fromPartiesService.create(data as FromParty);
        case 'update':
          return fromPartiesService.update(Number(data.id), data);
        case 'delete':
          return fromPartiesService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for from_parties`);
      }

    // ─── Suppliers ───────────────────────────────────────────────
    case 'suppliers':
      switch (operation) {
        case 'list':
          return suppliersService.list(
            (query.search as string) || data.search,
            (query.status as string) || data.status
          );
        case 'get':
          return suppliersService.getById(Number(query.id || data.id));
        case 'create':
          return suppliersService.create(data as Supplier);
        case 'update':
          return suppliersService.update(Number(data.id), data);
        case 'delete':
          return suppliersService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for suppliers`);
      }

    // ─── Outward Parties ─────────────────────────────────────────
    case 'outward_parties':
      switch (operation) {
        case 'list':
          return outwardPartiesService.list(
            (query.search as string) || data.search,
            (query.status as string) || data.status
          );
        case 'get':
          return outwardPartiesService.getById(Number(query.id || data.id));
        case 'create':
          return outwardPartiesService.create(data as OutwardParty);
        case 'update':
          return outwardPartiesService.update(Number(data.id), data);
        case 'delete':
          return outwardPartiesService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for outward_parties`);
      }

    // ─── Items ─────────────────────────────────────────────────
    case 'items':
      switch (operation) {
        case 'list':
          return itemsService.list(
            (query.search as string) || data.search,
            (query.status as string) || data.status
          );
        case 'get':
          return itemsService.getById(Number(query.id || data.id));
        case 'create':
          return itemsService.create(data as Item);
        case 'update':
          return itemsService.update(Number(data.id), data);
        case 'delete':
          return itemsService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for items`);
      }

    // ─── Inwards ───────────────────────────────────────────────
    case 'inwards':
      switch (operation) {
        case 'list':
          return inwardsService.list(
            query.ms_party_id ? Number(query.ms_party_id) : data.ms_party_id,
            (query.inward_no as string) || data.inward_no,
            (query.gp_no as string) || data.gp_no,
            (query.from_date as string) || data.from_date,
            (query.to_date as string) || data.to_date
          );
        case 'get':
          return inwardsService.getById(Number(query.id || data.id));
        case 'get_references':
          return inwardsService.getReferencesByMsParty(Number(query.ms_party_id || data.ms_party_id));
        case 'create':
          return inwardsService.create(data as Inward);
        case 'update':
          return inwardsService.update(Number(data.id), data);
        case 'delete':
          return inwardsService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for inwards`);
      }

    // ─── Outwards ──────────────────────────────────────────────
    case 'outwards':
      switch (operation) {
        case 'list':
          return outwardsService.list(
            query.ms_party_id ? Number(query.ms_party_id) : data.ms_party_id,
            (query.outward_no as string) || data.outward_no,
            (query.gp_no as string) || data.gp_no,
            (query.from_date as string) || data.from_date,
            (query.to_date as string) || data.to_date
          );
        case 'get':
          return outwardsService.getById(Number(query.id || data.id));
        case 'create':
          return outwardsService.create(data as Outward);
        case 'update':
          return outwardsService.update(Number(data.id), data);
        case 'delete':
          return outwardsService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for outwards`);
      }

    // ─── Transfers ───────────────────────────────────────────────
    case 'transfers':
      switch (operation) {
        case 'list':
          return transfersService.list(
            query.ms_party_id ? Number(query.ms_party_id) : data.ms_party_id,
            (query.transfer_no as string) || data.transfer_no,
            (query.gp_no as string) || data.gp_no,
            (query.from_date as string) || data.from_date,
            (query.to_date as string) || data.to_date
          );
        case 'get':
          return transfersService.getById(Number(query.id || data.id));
        case 'create':
          return transfersService.create(data as Transfer);
        case 'update':
          return transfersService.update(Number(data.id), data);
        case 'delete':
          return transfersService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for transfers`);
      }

    // ─── Transfer By Names ───────────────────────────────────────────
    case 'transfer_by_names':
      switch (operation) {
        case 'list':
          return transferByNamesService.list(
            query.ms_party_id ? Number(query.ms_party_id) : data.ms_party_id,
            (query.tbn_no as string) || data.tbn_no,
            (query.gp_no as string) || data.gp_no,
            (query.from_date as string) || data.from_date,
            (query.to_date as string) || data.to_date
          );
        case 'get':
          return transferByNamesService.getById(Number(query.id || data.id));
        case 'create':
          return transferByNamesService.create(data as TransferByName);
        case 'update':
          return transferByNamesService.update(Number(data.id), data);
        case 'delete':
          return transferByNamesService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for transfer_by_names`);
      }

    // ─── Asset Categories ──────────────────────────────────────
    case 'asset_categories':
      switch (operation) {
        case 'list':
          return assetsService.listCategories(
            (query.search as string) || data.search
          );
        case 'get':
          return assetsService.getCategoryById(Number(query.id || data.id));
        case 'create':
          return assetsService.createCategory(data as AssetCategory);
        case 'update':
          return assetsService.updateCategory(Number(data.id), data);
        case 'delete':
          return assetsService.deleteCategory(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for asset_categories`);
      }

    // ─── Assets ────────────────────────────────────────────────
    case 'assets':
      switch (operation) {
        case 'list':
          return assetsService.listAssets(
            query.category_id ? Number(query.category_id) : data.category_id,
            (query.search as string) || data.search
          );
        case 'get':
          return assetsService.getAssetById(Number(query.id || data.id));
        case 'create':
          return assetsService.createAsset(data as Asset);
        case 'update':
          return assetsService.updateAsset(Number(data.id), data);
        case 'delete':
          return assetsService.deleteAsset(Number(query.id || data.id));
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

    // ─── Reports ───────────────────────────────────────────────
    case 'reports':
      switch (operation) {
        case 'stock':
          return reportsService.getStockReport(
            query.ms_party_id ? Number(query.ms_party_id) : undefined,
            query.item_id ? Number(query.item_id) : undefined
          );
        case 'stock_ledger':
          return reportsService.getStockLedger({
            ms_party_id: query.ms_party_id ? Number(query.ms_party_id) : data.ms_party_id,
            item_id: query.item_id ? Number(query.item_id) : data.item_id,
            from_date: (query.from_date as string) || data.from_date,
            to_date: (query.to_date as string) || data.to_date,
            transaction_type: (query.transaction_type as string) || data.transaction_type,
            particulars: (query.particulars as string) || data.particulars,
            measurement: query.measurement ? Number(query.measurement) : data.measurement,
            amount_type: (query.amount_type as 'debit' | 'credit') || data.amount_type
          });
        case 'financial_ledger':
          return reportsService.getFinancialLedger(
            (query.account_type as string || data.account_type as string || 'MS Party'),
            Number(query.account_id || data.account_id || query.ms_party_id || data.ms_party_id),
            (query.from_date as string) || data.from_date,
            (query.to_date as string) || data.to_date
          );
        default:
          throw new Error(`Unknown operation: ${operation} for reports`);
      }

    // ─── Invoices ──────────────────────────────────────────────
    case 'invoices':
      switch (operation) {
        case 'list':
          return invoicesService.list((query.search as string) || data.search);
        case 'get':
          return invoicesService.getById(Number(query.id || data.id));
        case 'available_outwards':
          return invoicesService.getAvailableOutwards(Number(query.ms_party_id || data.ms_party_id));
        case 'create':
          return invoicesService.create(data as Invoice);
        case 'update':
          return invoicesService.update(Number(data.id), data);
        case 'delete':
          return invoicesService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for invoices`);
      }

    // ─── Accounts ──────────────────────────────────────────────
    case 'accounts':
      switch (operation) {
        case 'list':
          return accountsService.list((query.search as string) || data.search);
        case 'get':
          return accountsService.getById(Number(query.id || data.id));
        case 'create':
          return accountsService.create(data);
        case 'update':
          return accountsService.update(Number(data.id), data);
        case 'delete':
          return accountsService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for accounts`);
      }

    // ─── Vouchers ──────────────────────────────────────────────
    case 'vouchers':
      switch (operation) {
        case 'list':
          return vouchersService.list({
            type: query.type || data.type,
            from_date: query.from_date || data.from_date,
            to_date: query.to_date || data.to_date,
            search: query.search || data.search
          });
        case 'create':
          return vouchersService.create(data);
        case 'delete':
          return vouchersService.delete(Number(query.id || data.id));
        default:
          throw new Error(`Unknown operation: ${operation} for vouchers`);
      }

    // ─── Settings ──────────────────────────────────────────────
    case 'settings':
      switch (operation) {
        case 'list':
          return settingsService.list();
        case 'get':
          return settingsService.getByKey(query.key as string || data.key as string);
        case 'update':
          return settingsService.updateByKey(data.key, data.value);
        case 'update_multiple':
          return settingsService.updateMultiple(data.settings);
        default:
          throw new Error(`Unknown operation: ${operation} for settings`);
      }

    default:
      throw new Error(`Unknown entity: ${entity}. Available: ms_parties, from_parties, suppliers, items, inwards, asset_categories, assets, expense_categories, expenses, reports, invoices, accounts, vouchers, settings`);
  }
}
