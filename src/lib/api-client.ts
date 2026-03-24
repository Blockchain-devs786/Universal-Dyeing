/**
 * Universal API Client for Universal Dyeing
 * 
 * All CRUD operations go through a single endpoint: /api/core
 * using an action-based routing pattern (entity.operation).
 * 
 * This keeps Vercel serverless function count to minimum (2 functions total).
 */

const API_BASE = '/api';

// ─── Types ─────────────────────────────────────────────────────────

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface MsParty {
  id: number;
  name: string;
  phone?: string;
  address?: string;
  city?: string;
  opening_balance?: number;
  debit?: number;
  credit?: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface FromParty {
  id: number;
  name: string;
  phone?: string;
  address?: string;
  city?: string;
  opening_balance?: number;
  debit?: number;
  credit?: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Vendor {
  id: number;
  name: string;
  phone?: string;
  address?: string;
  city?: string;
  opening_balance?: number;
  debit?: number;
  credit?: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Item {
  id: number;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface InwardItem {
  id: number;
  inward_id: number;
  item_id: number;
  item_name?: string;
  measurement: 15 | 22;
  quantity: number;
}

export interface Inward {
  id: number;
  inward_no: string;
  gp_no: string;
  sr_no: string;
  ms_party_id: number;
  ms_party_name?: string;
  from_party_id: number;
  from_party_name?: string;
  vehicle_no?: string;
  driver_name?: string;
  date: string;
  total_qty?: number;
  status: string;
  items?: InwardItem[];
  created_at: string;
  updated_at: string;
}

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

export interface AssetCategory {
  id: number;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Asset {
  id: number;
  name: string;
  category_id?: number | null;
  category_name?: string;
  description?: string;
  value?: number;
  location?: string;
  status: string;
  purchase_date?: string;
  created_at: string;
  updated_at: string;
}

export interface ExpenseCategory {
  id: number;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Expense {
  id: number;
  name: string;
  category_id: number;
  category_name?: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

// ─── Core Request Function ───────────────────────────────────────

async function coreRequest<T>(action: string, data?: Record<string, any>, queryParams?: Record<string, string>): Promise<T> {
  const params = new URLSearchParams({ action, ...queryParams });
  
  const response = await fetch(`${API_BASE}/core?${params.toString()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, data: data || {} }),
  });

  const result: ApiResponse<T> = await response.json();
  
  if (!result.success) {
    throw new Error(result.error || 'API request failed');
  }
  
  return result.data as T;
}

// ─── MS Parties API ──────────────────────────────────────────────

export const msPartiesApi = {
  list: (search?: string, status?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (status) params.status = status;
    return coreRequest<MsParty[]>('ms_parties.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<MsParty>('ms_parties.get', { id }),
  
  create: (data: Omit<MsParty, 'id' | 'debit' | 'credit' | 'created_at' | 'updated_at'>) => 
    coreRequest<MsParty>('ms_parties.create', data),
  
  update: (id: number, data: Partial<MsParty>) => 
    coreRequest<MsParty>('ms_parties.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('ms_parties.delete', { id }),
};

// ─── From Parties API ────────────────────────────────────────────

export const fromPartiesApi = {
  list: (search?: string, status?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (status) params.status = status;
    return coreRequest<FromParty[]>('from_parties.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<FromParty>('from_parties.get', { id }),
  
  create: (data: Omit<FromParty, 'id' | 'debit' | 'credit' | 'created_at' | 'updated_at'>) => 
    coreRequest<FromParty>('from_parties.create', data),
  
  update: (id: number, data: Partial<FromParty>) => 
    coreRequest<FromParty>('from_parties.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('from_parties.delete', { id }),
};

// ─── Vendors API ─────────────────────────────────────────────────

export const vendorsApi = {
  list: (search?: string, status?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (status) params.status = status;
    return coreRequest<Vendor[]>('vendors.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<Vendor>('vendors.get', { id }),
  
  create: (data: Omit<Vendor, 'id' | 'debit' | 'credit' | 'created_at' | 'updated_at'>) => 
    coreRequest<Vendor>('vendors.create', data),
  
  update: (id: number, data: Partial<Vendor>) => 
    coreRequest<Vendor>('vendors.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('vendors.delete', { id }),
};

// ─── Items API ───────────────────────────────────────────────────

export const itemsApi = {
  list: (search?: string, status?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (status) params.status = status;
    return coreRequest<Item[]>('items.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<Item>('items.get', { id }),
  
  create: (data: Omit<Item, 'id' | 'created_at' | 'updated_at'>) => 
    coreRequest<Item>('items.create', data),
  
  update: (id: number, data: Partial<Item>) => 
    coreRequest<Item>('items.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('items.delete', { id }),
};

// ─── Reports API ─────────────────────────────────────────────────

export const reportsApi = {
  getStock: (ms_party_id?: string | number, item_id?: string | number) => {
    const params: Record<string, string> = {};
    if (ms_party_id && ms_party_id !== "all") params.ms_party_id = String(ms_party_id);
    if (item_id && item_id !== "all") params.item_id = String(item_id);
    return coreRequest<StockReportRow[]>('reports.stock', {}, params);
  }
};

// ─── Inwards API ─────────────────────────────────────────────────

export const inwardsApi = {
  list: (filters?: { ms_party_id?: number, inward_no?: string, gp_no?: string, from_date?: string, to_date?: string }) => {
    const params: Record<string, string> = {};
    if (filters?.ms_party_id) params.ms_party_id = String(filters.ms_party_id);
    if (filters?.inward_no) params.inward_no = filters.inward_no;
    if (filters?.gp_no) params.gp_no = filters.gp_no;
    if (filters?.from_date) params.from_date = filters.from_date;
    if (filters?.to_date) params.to_date = filters.to_date;
    return coreRequest<Inward[]>('inwards.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<Inward>('inwards.get', { id }),
  
  create: (data: Omit<Inward, 'id' | 'inward_no' | 'gp_no' | 'sr_no' | 'created_at' | 'updated_at'>) => 
    coreRequest<Inward>('inwards.create', data),
  
  update: (id: number, data: Partial<Inward>) => 
    coreRequest<Inward>('inwards.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('inwards.delete', { id }),
};

// ─── Asset Categories API ────────────────────────────────────────

export const assetCategoriesApi = {
  list: (search?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    return coreRequest<AssetCategory[]>('asset_categories.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<AssetCategory>('asset_categories.get', { id }),
  
  create: (data: Omit<AssetCategory, 'id' | 'created_at' | 'updated_at'>) => 
    coreRequest<AssetCategory>('asset_categories.create', data),
  
  update: (id: number, data: Partial<AssetCategory>) => 
    coreRequest<AssetCategory>('asset_categories.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('asset_categories.delete', { id }),
};

// ─── Assets API ──────────────────────────────────────────────────

export const assetsApi = {
  list: (categoryId?: number, search?: string) => {
    const params: Record<string, string> = {};
    if (categoryId) params.category_id = String(categoryId);
    if (search) params.search = search;
    return coreRequest<Asset[]>('assets.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<Asset>('assets.get', { id }),
  
  create: (data: Omit<Asset, 'id' | 'category_name' | 'created_at' | 'updated_at'>) => 
    coreRequest<Asset>('assets.create', data),
  
  update: (id: number, data: Partial<Asset>) => 
    coreRequest<Asset>('assets.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('assets.delete', { id }),
};

// ─── Expense Categories API ──────────────────────────────────────

export const expenseCategoriesApi = {
  list: (search?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    return coreRequest<ExpenseCategory[]>('expense_categories.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<ExpenseCategory>('expense_categories.get', { id }),
  
  create: (data: Omit<ExpenseCategory, 'id' | 'created_at' | 'updated_at'>) => 
    coreRequest<ExpenseCategory>('expense_categories.create', data),
  
  update: (id: number, data: Partial<ExpenseCategory>) => 
    coreRequest<ExpenseCategory>('expense_categories.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('expense_categories.delete', { id }),
};

// ─── Expenses API ────────────────────────────────────────────────

export const expensesApi = {
  list: (categoryId?: number, search?: string) => {
    const params: Record<string, string> = {};
    if (categoryId) params.category_id = String(categoryId);
    if (search) params.search = search;
    return coreRequest<Expense[]>('expenses.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<Expense>('expenses.get', { id }),
  
  create: (data: Omit<Expense, 'id' | 'category_name' | 'created_at' | 'updated_at'>) => 
    coreRequest<Expense>('expenses.create', data),
  
  update: (id: number, data: Partial<Expense>) => 
    coreRequest<Expense>('expenses.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('expenses.delete', { id }),
};

// ─── Health Check ────────────────────────────────────────────────

export const healthApi = {
  check: async () => {
    const response = await fetch(`${API_BASE}/auth?action=health`);
    return response.json();
  },
  ping: async () => {
    const response = await fetch(`${API_BASE}/auth?action=ping`);
    return response.json();
  },
};
