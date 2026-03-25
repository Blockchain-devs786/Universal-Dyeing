import { neon } from '@neondatabase/serverless';

const sql = neon('postgresql://neondb_owner:npg_5xuaRAfIFwv9@ep-restless-art-amofidog-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require');

async function run() {
  try {
    console.log('Adding columns to transfer_by_names...');
    await sql`ALTER TABLE transfer_by_names ADD COLUMN IF NOT EXISTS gp_no VARCHAR(50) UNIQUE`;
    await sql`ALTER TABLE transfer_by_names ADD COLUMN IF NOT EXISTS vehicle_no VARCHAR(100)`;
    await sql`ALTER TABLE transfer_by_names ADD COLUMN IF NOT EXISTS driver_name VARCHAR(100)`;
    console.log('Successfully added columns.');

    console.log('Fixing foreign key on transfers...');
    await sql`ALTER TABLE transfers DROP CONSTRAINT IF EXISTS transfers_transfer_to_party_id_fkey`;
    await sql`ALTER TABLE transfers ADD CONSTRAINT transfers_transfer_to_party_id_fkey FOREIGN KEY (transfer_to_party_id) REFERENCES from_parties(id) ON DELETE RESTRICT`;
    console.log('Successfully fixed transfers foreign key!');
  } catch (err) {
    console.error('Error:', err);
  }
}

run();
