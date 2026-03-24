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

export interface Asset {
  id: number;
  name: string;
  description?: string;
  category?: string;
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

// ─── Assets API ──────────────────────────────────────────────────

export const assetsApi = {
  list: (search?: string, status?: string, category?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (status) params.status = status;
    if (category) params.category = category;
    return coreRequest<Asset[]>('assets.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<Asset>('assets.get', { id }),
  
  create: (data: Omit<Asset, 'id' | 'created_at' | 'updated_at'>) => 
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
