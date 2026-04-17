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
  rate_15?: number;
  rate_22?: number;
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
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface Supplier {
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

export interface OutwardParty {
  id: number;
  name: string;
  phone?: string;
  address?: string;
  city?: string;
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
  reference?: string;
  total_qty?: number;
  status: string;
  items?: InwardItem[];
  ms_party_gp_no?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface OutwardItem {
  id: number;
  outward_id: number;
  item_id: number;
  item_name?: string;
  measurement: 15 | 22;
  quantity: number;
}

export interface Outward {
  id: number;
  outward_no: string;
  gp_no: string;
  sr_no: string;
  ms_party_id: number;
  ms_party_name?: string;
  from_party_id: number;
  from_party_name?: string;
  outward_to_party_id: number;
  outward_to_party_name?: string;
  vehicle_no?: string;
  driver_name?: string;
  date: string;
  reference?: string;
  inward_id?: number;
  inward_no?: string;
  inward_sr_no?: string;
  inward_gp_no?: string;
  inward_ms_party_gp_no?: string;
  total_qty?: number;
  status: string;
  created_by?: string;
  items?: OutwardItem[];
  created_at: string;
  updated_at: string;
}

export interface TransferItem {
  id: number;
  transfer_id: number;
  item_id: number;
  item_name?: string;
  measurement: 15 | 22;
  quantity: number;
}

export interface Transfer {
  id: number;
  transfer_no: string;
  gp_no: string;
  sr_no: string;
  ms_party_id: number;
  ms_party_name?: string;
  from_party_id: number;
  from_party_name?: string;
  transfer_to_party_id: number;
  transfer_to_party_name?: string;
  vehicle_no?: string;
  driver_name?: string;
  date: string;
  total_qty?: number;
  status: string;
  items?: TransferItem[];
  created_at: string;
  updated_at: string;
}

export interface TransferByNameItem {
  id: number;
  tbn_id: number;
  item_id: number;
  item_name?: string;
  measurement: 15 | 22;
  quantity: number;
}

export interface TransferByName {
  id: number;
  tbn_no: string;
  gp_no: string;
  sr_no: string;
  ms_party_id: number;
  ms_party_name?: string;
  from_party_id: number;
  from_party_name?: string;
  transfer_to_party_id: number;
  transfer_to_party_name?: string;
  vehicle_no?: string;
  driver_name?: string;
  date: string;
  total_qty?: number;
  status: string;
  items?: TransferByNameItem[];
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

export interface Expense {
  id: number;
  name: string;
  phone?: string;
  address?: string;
  city?: string;
  opening_balance?: number;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface Account {
  id: number;
  name: string;
  type: 'Cash' | 'Bank';
  account_number?: string;
  bank_name?: string;
  opening_balance: number;
  current_balance: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface InvoiceItem {
  outward_id: number;
  outward_no: string;
  gp_no: string;
  sr_no: string;
  item_name: string;
  measurement: number;
  quantity: number;
}

export interface Invoice {
  id: number;
  invoice_no: string;
  ms_party_id: number;
  ms_party_name?: string;
  date: string;
  sub_total: number;
  discount_percent: number;
  discount_amount: number;
  total_amount: number;
  rate_15: number;
  rate_22: number;
  type?: 'credit' | 'debit';
  cash_account_id?: number | null;
  cash_account_name?: string | null;
  invoice_days?: number | null;
  status: string;
  created_by?: string;
  edited_by?: string;
  created_at: string;
  updated_at: string;
  outward_ids?: number[];
  items?: InvoiceItem[];
  item_count?: number;
}

export interface VoucherEntry {
  id?: number;
  voucher_id?: number;
  account_type: 'MS Party' | 'Supplier' | 'Expense' | 'Account' | 'Asset';
  account_id: number;
  debit: number;
  credit: number;
  description?: string;
}

export interface Voucher {
  id: number;
  voucher_no: string;
  type: 'CRV' | 'CPV' | 'JV';
  date: string;
  ref_no?: string;
  description?: string;
  total_amount: number;
  status: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
  entries?: VoucherEntry[];
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

// ─── Suppliers API ─────────────────────────────────────────────────

export const suppliersApi = {
  list: (search?: string, status?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (status) params.status = status;
    return coreRequest<Supplier[]>('suppliers.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<Supplier>('suppliers.get', { id }),
  
  create: (data: Omit<Supplier, 'id' | 'debit' | 'credit' | 'created_at' | 'updated_at'>) => 
    coreRequest<Supplier>('suppliers.create', data),
  
  update: (id: number, data: Partial<Supplier>) => 
    coreRequest<Supplier>('suppliers.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('suppliers.delete', { id }),
};

// ─── Outward Parties API ─────────────────────────────────────────

export const outwardPartiesApi = {
  list: (search?: string, status?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (status) params.status = status;
    return coreRequest<OutwardParty[]>('outward_parties.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<OutwardParty>('outward_parties.get', { id }),
  
  create: (data: Omit<OutwardParty, 'id' | 'created_at' | 'updated_at'>) => 
    coreRequest<OutwardParty>('outward_parties.create', data),
  
  update: (id: number, data: Partial<OutwardParty>) => 
    coreRequest<OutwardParty>('outward_parties.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('outward_parties.delete', { id }),
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
  },
  getStockLedger: (filters: {
    ms_party_id?: string | number;
    item_id?: string | number;
    from_date?: string;
    to_date?: string;
    transaction_type?: string;
    particulars?: string;
    measurement?: number;
    amount_type?: 'debit' | 'credit';
  }) => {
    const params: Record<string, string> = {};
    if (filters.ms_party_id && filters.ms_party_id !== "all") params.ms_party_id = String(filters.ms_party_id);
    if (filters.item_id && filters.item_id !== "all") params.item_id = String(filters.item_id);
    if (filters.from_date) params.from_date = filters.from_date;
    if (filters.to_date) params.to_date = filters.to_date;
    if (filters.transaction_type) params.transaction_type = filters.transaction_type;
    if (filters.particulars) params.particulars = filters.particulars;
    if (filters.measurement) params.measurement = String(filters.measurement);
    if (filters.amount_type) params.amount_type = filters.amount_type;
    
    return coreRequest<StockLedgerRow[]>('reports.stock_ledger', {}, params);
  },
  getFinancialLedger: (accountId: number, from_date?: string, to_date?: string, accountType: string = 'MS Party') => {
    const params: Record<string, string> = { 
        account_id: String(accountId),
        account_type: accountType
    };
    if (from_date) params.from_date = from_date;
    if (to_date) params.to_date = to_date;
    return coreRequest<any[]>('reports.financial_ledger', {}, params);
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
  
  getReferences: (msPartyId: number) =>
    coreRequest<{id: number, name: string}[]>('inwards.get_references', { ms_party_id: msPartyId }),

  create: (data: Omit<Inward, 'id' | 'inward_no' | 'gp_no' | 'sr_no' | 'created_at' | 'updated_at'>) => 
    coreRequest<Inward>('inwards.create', data),
  
  update: (id: number, data: Partial<Inward>) => 
    coreRequest<Inward>('inwards.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('inwards.delete', { id }),
};

// ─── Outwards API ────────────────────────────────────────────────
  
  export const outwardsApi = {
    list: (filters?: { ms_party_id?: number, outward_no?: string, gp_no?: string, from_date?: string, to_date?: string }) => {
      const params: Record<string, string> = {};
      if (filters?.ms_party_id) params.ms_party_id = String(filters.ms_party_id);
      if (filters?.outward_no) params.outward_no = filters.outward_no;
      if (filters?.gp_no) params.gp_no = filters.gp_no;
      if (filters?.from_date) params.from_date = filters.from_date;
      if (filters?.to_date) params.to_date = filters.to_date;
      return coreRequest<Outward[]>('outwards.list', {}, params);
    },
    
    getById: (id: number) => 
      coreRequest<Outward>('outwards.get', { id }),
    
    create: (data: Omit<Outward, 'id' | 'outward_no' | 'gp_no' | 'sr_no' | 'created_at' | 'updated_at'>) => 
      coreRequest<Outward>('outwards.create', data),
    
    update: (id: number, data: Partial<Outward>) => 
      coreRequest<Outward>('outwards.update', { ...data, id }),
    
    delete: (id: number) => 
      coreRequest<{ success: boolean }>('outwards.delete', { id }),
  };
  
  // ─── Transfers API ─────────────────────────────────────────────────
  
  export const transfersApi = {
    list: (filters?: { ms_party_id?: number, transfer_no?: string, gp_no?: string, from_date?: string, to_date?: string }) => {
      const params: Record<string, string> = {};
      if (filters?.ms_party_id) params.ms_party_id = String(filters.ms_party_id);
      if (filters?.transfer_no) params.transfer_no = filters.transfer_no;
      if (filters?.gp_no) params.gp_no = filters.gp_no;
      if (filters?.from_date) params.from_date = filters.from_date;
      if (filters?.to_date) params.to_date = filters.to_date;
      return coreRequest<Transfer[]>('transfers.list', {}, params);
    },
    
    getById: (id: number) => 
      coreRequest<Transfer>('transfers.get', { id }),
    
    create: (data: Omit<Transfer, 'id' | 'transfer_no' | 'gp_no' | 'sr_no' | 'created_at' | 'updated_at'>) => 
      coreRequest<Transfer>('transfers.create', data),
    
    update: (id: number, data: Partial<Transfer>) => 
      coreRequest<Transfer>('transfers.update', { ...data, id }),
    
    delete: (id: number) => 
      coreRequest<{ success: boolean }>('transfers.delete', { id }),
  };

  // ─── Transfer By Names API ─────────────────────────────────────────────────
  
  export const transferByNamesApi = {
    list: (filters?: { ms_party_id?: number, tbn_no?: string, gp_no?: string, from_date?: string, to_date?: string }) => {
      const params: Record<string, string> = {};
      if (filters?.ms_party_id) params.ms_party_id = String(filters.ms_party_id);
      if (filters?.tbn_no) params.tbn_no = filters.tbn_no;
      if (filters?.gp_no) params.gp_no = filters.gp_no;
      if (filters?.from_date) params.from_date = filters.from_date;
      if (filters?.to_date) params.to_date = filters.to_date;
      return coreRequest<TransferByName[]>('transfer_by_names.list', {}, params);
    },
    
    getById: (id: number) => 
      coreRequest<TransferByName>('transfer_by_names.get', { id }),
    
    create: (data: Omit<TransferByName, 'id' | 'tbn_no' | 'gp_no' | 'sr_no' | 'created_at' | 'updated_at'>) => 
      coreRequest<TransferByName>('transfer_by_names.create', data),
    
    update: (id: number, data: Partial<TransferByName>) => 
      coreRequest<TransferByName>('transfer_by_names.update', { ...data, id }),
    
    delete: (id: number) => 
      coreRequest<{ success: boolean }>('transfer_by_names.delete', { id }),
  };

// ─── Expenses API ────────────────────────────────────────────────

export const expensesApi = {
  list: (_?: any, search?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    return coreRequest<Expense[]>('expenses.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<Expense>('expenses.get', { id }),
  
  create: (data: Omit<Expense, 'id' | 'created_at' | 'updated_at'>) => 
    coreRequest<Expense>('expenses.create', data),
  
  update: (id: number, data: Partial<Expense>) => 
    coreRequest<Expense>('expenses.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('expenses.delete', { id }),
};

// ─── Invoices API ────────────────────────────────────────────────

export const invoicesApi = {
  list: (search?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    return coreRequest<Invoice[]>('invoices.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<Invoice>('invoices.get', { id }),
  
  getAvailableOutwards: (msPartyId: number) =>
    coreRequest<any[]>('invoices.available_outwards', { ms_party_id: msPartyId }),
  
  create: (data: any) => 
    coreRequest<Invoice>('invoices.create', data),
  
  update: (id: number, data: Partial<Invoice>) => 
    coreRequest<Invoice>('invoices.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('invoices.delete', { id }),
};

// ─── Accounts API ────────────────────────────────────────────────

export const accountsApi = {
  list: (search?: string) => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    return coreRequest<Account[]>('accounts.list', {}, params);
  },
  
  getById: (id: number) => 
    coreRequest<Account>('accounts.get', { id }),
  
  create: (data: Omit<Account, 'id' | 'current_balance' | 'created_at' | 'updated_at'>) => 
    coreRequest<Account>('accounts.create', data),
  
  update: (id: number, data: Partial<Account>) => 
    coreRequest<Account>('accounts.update', { ...data, id }),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('accounts.delete', { id }),
};

// ─── Vouchers API ────────────────────────────────────────────────

export const vouchersApi = {
  list: (filters: { type?: string, from_date?: string, to_date?: string, search?: string } = {}) => 
    coreRequest<Voucher[]>('vouchers.list', {}, filters as any),
  
  create: (data: Omit<Voucher, 'id' | 'voucher_no' | 'created_at' | 'updated_at'>) => 
    coreRequest<Voucher>('vouchers.create', data),
  
  delete: (id: number) => 
    coreRequest<{ success: boolean }>('vouchers.delete', { id }),
};

// ─── Settings API ──────────────────────────────────────────────

export const settingsApi = {
  list: () => coreRequest<any[]>('settings.list'),
  get: (key: string) => coreRequest<any>('settings.get', { key }),
  update: (key: string, value: string) => coreRequest<any>('settings.update', { key, value }),
  updateMultiple: (settings: Record<string, string>) => coreRequest<any[]>('settings.update_multiple', { settings }),
};


// ─── FIFO API ────────────────────────────────────────────────────

export interface InwardItemBreakdown {
  inward_item_id: number;
  item_id: number;
  item_name: string;
  measurement: number;
  original_qty: number;
  deducted_qty: number;
  outward_qty: number;
  transfer_qty: number;
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

export const fifoApi = {
  runMigration: () =>
    coreRequest<{ processed: number; totalDeductions: number }>('fifo.run_migration'),
  
  getInwardBreakdown: (inwardId: number) =>
    coreRequest<InwardItemBreakdown[]>('fifo.inward_breakdown', { inward_id: inwardId }),
  
  getInwardBreakdownsByParty: (msPartyId?: number) => {
    const params: Record<string, string> = {};
    if (msPartyId) params.ms_party_id = String(msPartyId);
    return coreRequest<Record<number, InwardItemBreakdown[]>>('fifo.inward_breakdowns_by_party', {}, params);
  },

  getOutwardDeductions: (outwardId: number) =>
    coreRequest<OutwardDeductionDetail[]>('fifo.outward_deductions', { outward_id: outwardId }),
    
  getOutwardDeductionsByParty: (msPartyId?: number) => {
    const params: Record<string, string> = {};
    if (msPartyId) params.ms_party_id = String(msPartyId);
    return coreRequest<Record<number, OutwardDeductionDetail[]>>('fifo.outward_deductions_by_party', {}, params);
  },

  getTransferDeductionsByParty: (msPartyId?: number) => {
    const params: Record<string, string> = {};
    if (msPartyId) params.ms_party_id = String(msPartyId);
    return coreRequest<Record<number, OutwardDeductionDetail[]>>('fifo.transfer_deductions_by_party', {}, params);
  },
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

// ─── Auth API ────────────────────────────────────────────────────

async function authRequest<T>(action: string, data?: Record<string, any>): Promise<T> {
  const response = await fetch(`${API_BASE}/auth?action=${action}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, data: data || {} }),
  });

  const result: ApiResponse<T> = await response.json();
  if (!result.success) throw new Error(result.error || 'Auth request failed');
  return result.data as T;
}

export const authApi = {
  createUser: (data: any) => authRequest<any>('users.create', data),
  listUsers: () => authRequest<any[]>('users.list'),
  updateUser: (data: any) => authRequest<any>('users.update', data),
  deleteUser: (id: number) => authRequest<any>('users.delete', { id }),
  verifyManually: (id: number) => authRequest<any>('users.verify_manually', { id }),
  checkEmail: (email: string) => authRequest<{ verified: boolean, message?: string }>('auth.check_email', { email }),
  verifyEmail: (token: string) => authRequest<{ success: boolean }>('auth.verify_email', { token }),
  login: (data: any) => authRequest<{ token: string, user: any }>('auth.login', data),
  resendVerification: (email: string) => authRequest<any>('auth.resend_verification', { email }),
};
