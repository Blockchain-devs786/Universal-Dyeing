import { neon } from '@neondatabase/serverless';

const sql = neon('postgresql://neondb_owner:npg_5xuaRAfIFwv9@ep-restless-art-amofidog-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require');

async function run() {
  try {
    console.log('Dropping UNIQUE constraint on sr_no in inwards...');
    await sql`ALTER TABLE inwards DROP CONSTRAINT IF EXISTS inwards_sr_no_key`;
    console.log('Successfully dropped the constraint.');
  } catch (err) {
    console.error('Error:', err);
  }
}

run();
