import { neon } from '@neondatabase/serverless';
import dotenv from 'dotenv';
dotenv.config();

const url = process.env.VITE_NEON_DB_URL || process.env.DATABASE_URL;
if (!url) {
    console.error('DATABASE_URL is not defined');
    process.exit(1);
}

const sql = neon(url);

async function check() {
    try {
        console.log('--- Vouchers Table ---');
        const count = await sql`SELECT count(*) FROM vouchers`;
        console.log('Total Count:', count);
        
        const all = await sql`SELECT * FROM vouchers LIMIT 10`;
        console.log('First 10 Vouchers:', JSON.stringify(all, null, 2));

        console.log('--- Account Balance check ---');
        const accs = await sql`SELECT id, name, current_balance FROM accounts`;
        console.log('Accounts:', accs);
    } catch (e) {
        console.error(e);
    }
}

check();
