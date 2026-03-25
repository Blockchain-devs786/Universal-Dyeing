import { neon } from '@neondatabase/serverless';

const sql = neon('postgresql://neondb_owner:npg_5xuaRAfIFwv9@ep-restless-art-amofidog-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require');

async function test() {
  try {
    console.log("Checking accounts table...");
    const tables = await sql`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' AND table_name = 'accounts'
    `;
    
    if (tables.length === 0) {
      console.log("Creating accounts table...");
      await sql`
        CREATE TABLE IF NOT EXISTS accounts (
          id SERIAL PRIMARY KEY,
          name VARCHAR(255) NOT NULL UNIQUE,
          type VARCHAR(50) NOT NULL CHECK (type IN ('Cash', 'Bank')),
          account_no VARCHAR(100),
          bank_name VARCHAR(100),
          opening_balance DECIMAL(15,2) DEFAULT 0,
          current_balance DECIMAL(15,2) DEFAULT 0,
          status VARCHAR(20) DEFAULT 'active',
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
      `;
      console.log("Table created!");
    } else {
      console.log("Table already exists.");
    }
  } catch (err) {
    console.error("Error:", err);
  }
}

test();
