import { neon, type NeonQueryFunction } from '@neondatabase/serverless';

let _sql: NeonQueryFunction<false, false> | null = null;

function getDb(): NeonQueryFunction<false, false> {
  if (!_sql) {
    const url = process.env.DATABASE_URL || process.env.POSTGRES_URL;
    if (!url) {
      throw new Error("DATABASE_URL is not set. Please ensure Vercel Environment Variables are configured.");
    }
    _sql = neon(url);
  }
  return _sql;
}

/**
 * Initialize all database tables.
 * Called on first request to ensure schema is ready.
 */
export async function initializeDatabase() {
  const db = getDb();

  // MS Parties table
  await db`
    CREATE TABLE IF NOT EXISTS ms_parties (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL UNIQUE,
      phone VARCHAR(50),
      address TEXT,
      city VARCHAR(100),
      opening_balance DECIMAL(15,2) DEFAULT 0,
      debit DECIMAL(15,2) DEFAULT 0,
      credit DECIMAL(15,2) DEFAULT 0,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Vendors table
  await db`
    CREATE TABLE IF NOT EXISTS vendors (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL UNIQUE,
      phone VARCHAR(50),
      address TEXT,
      city VARCHAR(100),
      opening_balance DECIMAL(15,2) DEFAULT 0,
      debit DECIMAL(15,2) DEFAULT 0,
      credit DECIMAL(15,2) DEFAULT 0,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // From Parties table (synced with MS Parties occasionally or manually managed)
  await db`
    CREATE TABLE IF NOT EXISTS from_parties (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL UNIQUE,
      phone VARCHAR(50),
      address TEXT,
      city VARCHAR(100),
      opening_balance DECIMAL(15,2) DEFAULT 0,
      debit DECIMAL(15,2) DEFAULT 0,
      credit DECIMAL(15,2) DEFAULT 0,
      status VARCHAR(20) DEFAULT 'active',
      is_default BOOLEAN DEFAULT false,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Safe alter for existing tables without the is_default column
  try {
    await db`ALTER TABLE from_parties ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT false`;
    // Seed default from_party
    await db`
      INSERT INTO from_parties (name, is_default) 
      SELECT 'Dyeing', true 
      WHERE NOT EXISTS (SELECT 1 FROM from_parties WHERE is_default = true)
      ON CONFLICT (name) DO NOTHING
    `;

    // Seed default ms_party (Dyeing)
    await db`
      INSERT INTO ms_parties (name) 
      SELECT 'Dyeing' 
      WHERE NOT EXISTS (SELECT 1 FROM ms_parties WHERE name = 'Dyeing' OR name LIKE '%UNIVERSAL DYEING%')
      ON CONFLICT (name) DO NOTHING
    `;
  } catch (err) {
    console.error("Migration error for from_parties:", err);
  }

  // Asset categories table
  await db`
    CREATE TABLE IF NOT EXISTS asset_categories (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL UNIQUE,
      description TEXT,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Items table
  await db`
    CREATE TABLE IF NOT EXISTS items (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL UNIQUE,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Assets table
  await db`
    CREATE TABLE IF NOT EXISTS assets (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      description TEXT,
      category_id INTEGER REFERENCES asset_categories(id) ON DELETE SET NULL,
      value DECIMAL(15,2) DEFAULT 0,
      location VARCHAR(255),
      status VARCHAR(20) DEFAULT 'active',
      purchase_date DATE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      UNIQUE(name, category_id)
    )
  `;

  // Expense categories table
  await db`
    CREATE TABLE IF NOT EXISTS expense_categories (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL UNIQUE,
      description TEXT,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Expenses table (linked to categories, unique name per category)
  await db`
    CREATE TABLE IF NOT EXISTS expenses (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      category_id INTEGER NOT NULL REFERENCES expense_categories(id) ON DELETE CASCADE,
      description TEXT,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      UNIQUE(name, category_id)
    )
  `;

  // Inwards base table
  await db`
    CREATE TABLE IF NOT EXISTS inwards (
      id SERIAL PRIMARY KEY,
      inward_no VARCHAR(50) UNIQUE,
      gp_no VARCHAR(50) UNIQUE,
      sr_no VARCHAR(50),
      ms_party_id INTEGER REFERENCES ms_parties(id) ON DELETE RESTRICT,
      from_party_id INTEGER REFERENCES from_parties(id) ON DELETE RESTRICT,
      vehicle_no VARCHAR(100),
      driver_name VARCHAR(100),
      date DATE NOT NULL,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Inward details (items)
  await db`
    CREATE TABLE IF NOT EXISTS inward_items (
      id SERIAL PRIMARY KEY,
      inward_id INTEGER REFERENCES inwards(id) ON DELETE CASCADE,
      item_id INTEGER REFERENCES items(id) ON DELETE RESTRICT,
      measurement INTEGER NOT NULL CHECK (measurement IN (15, 22)),
      quantity DECIMAL(15,2) NOT NULL DEFAULT 0
    )
  `;

  // Outwards base table
  await db`
    CREATE TABLE IF NOT EXISTS outwards (
      id SERIAL PRIMARY KEY,
      outward_no VARCHAR(50) UNIQUE,
      gp_no VARCHAR(50) UNIQUE,
      sr_no VARCHAR(50),
      ms_party_id INTEGER REFERENCES ms_parties(id) ON DELETE RESTRICT,
      from_party_id INTEGER REFERENCES from_parties(id) ON DELETE RESTRICT,
      outward_to_party_id INTEGER REFERENCES from_parties(id) ON DELETE RESTRICT,
      vehicle_no VARCHAR(100),
      driver_name VARCHAR(100),
      date DATE NOT NULL,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Outward details (items)
  await db`
    CREATE TABLE IF NOT EXISTS outward_items (
      id SERIAL PRIMARY KEY,
      outward_id INTEGER REFERENCES outwards(id) ON DELETE CASCADE,
      item_id INTEGER REFERENCES items(id) ON DELETE RESTRICT,
      measurement INTEGER NOT NULL CHECK (measurement IN (15, 22)),
      quantity DECIMAL(15,2) NOT NULL DEFAULT 0
    )
  `;

  // Transfers base table
  await db`
    CREATE TABLE IF NOT EXISTS transfers (
      id SERIAL PRIMARY KEY,
      transfer_no VARCHAR(50) UNIQUE,
      gp_no VARCHAR(50) UNIQUE,
      sr_no VARCHAR(50),
      ms_party_id INTEGER REFERENCES ms_parties(id) ON DELETE RESTRICT,
      from_party_id INTEGER REFERENCES from_parties(id) ON DELETE RESTRICT,
      transfer_to_party_id INTEGER REFERENCES from_parties(id) ON DELETE RESTRICT,
      vehicle_no VARCHAR(100),
      driver_name VARCHAR(100),
      date DATE NOT NULL,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Transfer details (items)
  await db`
    CREATE TABLE IF NOT EXISTS transfer_items (
      id SERIAL PRIMARY KEY,
      transfer_id INTEGER REFERENCES transfers(id) ON DELETE CASCADE,
      item_id INTEGER REFERENCES items(id) ON DELETE RESTRICT,
      measurement INTEGER NOT NULL CHECK (measurement IN (15, 22)),
      quantity DECIMAL(15,2) NOT NULL DEFAULT 0
    )
  `;

  // Transfer By Names base table
  await db`
    CREATE TABLE IF NOT EXISTS transfer_by_names (
      id SERIAL PRIMARY KEY,
      tbn_no VARCHAR(50) UNIQUE,
      sr_no VARCHAR(50),
      ms_party_id INTEGER REFERENCES ms_parties(id) ON DELETE RESTRICT,
      from_party_id INTEGER REFERENCES from_parties(id) ON DELETE RESTRICT,
      transfer_to_party_id INTEGER REFERENCES ms_parties(id) ON DELETE RESTRICT,
      date DATE NOT NULL,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Transfer By Names details (items)
  await db`
    CREATE TABLE IF NOT EXISTS transfer_bn_items (
      id SERIAL PRIMARY KEY,
      tbn_id INTEGER REFERENCES transfer_by_names(id) ON DELETE CASCADE,
      item_id INTEGER REFERENCES items(id) ON DELETE RESTRICT,
      measurement INTEGER NOT NULL CHECK (measurement IN (15, 22)),
      quantity DECIMAL(15,2) NOT NULL DEFAULT 0
    )
  `;

  // Activity log table
  await db`
    CREATE TABLE IF NOT EXISTS activity_log (
      id SERIAL PRIMARY KEY,
      entity_type VARCHAR(50) NOT NULL,
      entity_id INTEGER,
      action VARCHAR(50) NOT NULL,
      details JSONB,
      performed_by VARCHAR(100) DEFAULT 'system',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Invoices table
  await db`
    CREATE TABLE IF NOT EXISTS invoices (
      id SERIAL PRIMARY KEY,
      invoice_no VARCHAR(50) UNIQUE,
      ms_party_id INTEGER REFERENCES ms_parties(id) ON DELETE RESTRICT,
      date DATE NOT NULL,
      sub_total DECIMAL(15,2) DEFAULT 0,
      discount_percent DECIMAL(5,2) DEFAULT 0,
      discount_amount DECIMAL(15,2) DEFAULT 0,
      total_amount DECIMAL(15,2) DEFAULT 0,
      rate_15 DECIMAL(10,2) DEFAULT 0,
      rate_22 DECIMAL(10,2) DEFAULT 0,
      status VARCHAR(20) DEFAULT 'active',
      created_by VARCHAR(100),
      edited_by VARCHAR(100),
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Invoice Items table (linking to outwards)
  await db`
    CREATE TABLE IF NOT EXISTS invoice_items (
      id SERIAL PRIMARY KEY,
      invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
      outward_id INTEGER REFERENCES outwards(id) ON DELETE CASCADE,
      UNIQUE(outward_id)
    )
  `;

  // Accounts table (Cash and Bank)
  await db`
    CREATE TABLE IF NOT EXISTS accounts (
      id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL UNIQUE,
      type VARCHAR(50) NOT NULL CHECK (type IN ('Cash', 'Bank')),
      account_number VARCHAR(100),
      bank_name VARCHAR(255),
      opening_balance DECIMAL(15,2) DEFAULT 0,
      current_balance DECIMAL(15,2) DEFAULT 0,
      status VARCHAR(20) DEFAULT 'active',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
  `;

  // Safety migrations for accounts
  try {
    await db`ALTER TABLE accounts ADD COLUMN IF NOT EXISTS account_number VARCHAR(100)`;
    await db`ALTER TABLE accounts ADD COLUMN IF NOT EXISTS bank_name VARCHAR(255)`;
    await db`ALTER TABLE accounts ADD COLUMN IF NOT EXISTS current_balance DECIMAL(15,2) DEFAULT 0`;
  } catch (err) {
    console.error("Migration error for accounts:", err);
  }
}

/**
 * Execute a SQL query using the Neon serverless driver.
 * Use this as a tagged template: sql`SELECT * FROM table`
 */
export { getDb as getDb };

// Re-export a simple sql tagged template helper
export const sql = {
  query: (strings: TemplateStringsArray, ...values: any[]) => {
    const db = getDb();
    return db(strings, ...values);
  }
};
