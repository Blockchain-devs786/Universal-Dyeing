"""MySQL Connection Pool Manager"""

import mysql.connector
from mysql.connector import pooling
import threading
import time
from typing import Optional
from common.config import DB_CONFIG, POOL_CONFIG


def ensure_database_exists() -> bool:
    """Create database and tables if they don't exist"""
    try:
        # Connect without database first
        config = DB_CONFIG.copy()
        database = config.pop("database")
        
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"Database '{database}' checked/created.")
        
        # Use database
        cursor.execute(f"USE {database}")
        
        # Create users table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                role ENUM('ADMIN','USER','MODULE_USER') DEFAULT 'USER',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'users' checked/created.")
        
        # Update existing users table to add MODULE_USER to role ENUM if table exists but column doesn't have it
        try:
            cursor.execute("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'role'
            """)
            result = cursor.fetchone()
            if result and 'MODULE_USER' not in result[0]:
                cursor.execute("ALTER TABLE users MODIFY COLUMN role ENUM('ADMIN','USER','MODULE_USER') DEFAULT 'USER'")
                conn.commit()
                print("Updated 'role' column to include 'MODULE_USER' in users table.")
        except Exception as e:
            if "Duplicate" not in str(e) and "doesn't exist" not in str(e):
                print(f"Note: MODULE_USER role update: {e}")
            try:
                conn.rollback()
            except:
                pass
        
        # Create user_modules table for module access control
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_modules (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                module_name VARCHAR(50) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE KEY unique_user_module (user_id, module_name),
                INDEX idx_user_id (user_id),
                INDEX idx_module_name (module_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'user_modules' checked/created.")
        
        # Add user_modules table if it doesn't exist (migration)
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.TABLES 
                WHERE table_schema = DATABASE() 
                AND table_name = 'user_modules'
            """)
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    CREATE TABLE user_modules (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        module_name VARCHAR(50) NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        UNIQUE KEY unique_user_module (user_id, module_name),
                        INDEX idx_user_id (user_id),
                        INDEX idx_module_name (module_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                print("Created 'user_modules' table.")
        except Exception as e:
            print(f"Note: user_modules table migration check: {e}")
        
        # Migrate existing parties table to liabilities if it exists
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.TABLES 
                WHERE table_schema = DATABASE() 
                AND table_name = 'parties'
            """)
            has_parties_table = cursor.fetchone()[0] > 0
            
            if has_parties_table:
                # Check if liabilities table already exists
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.TABLES 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'liabilities'
                """)
                has_liabilities_table = cursor.fetchone()[0] > 0
                
                if not has_liabilities_table:
                    # Rename parties table to liabilities
                    cursor.execute("RENAME TABLE parties TO liabilities")
                    conn.commit()
                    print("Migrated 'parties' table to 'liabilities'.")
                else:
                    print("Note: Both 'parties' and 'liabilities' tables exist. Keeping 'liabilities'.")
        except Exception as e:
            print(f"Note: Table migration check: {e}")
            try:
                conn.rollback()
            except:
                pass
        
        # Create liabilities table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS liabilities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                rate_15_yards DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                rate_22_yards DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                discount_percent DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
                is_ms_party BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'liabilities' checked/created.")
        
        # Migrate existing liabilities to have is_ms_party = TRUE (default)
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS 
                WHERE table_schema = DATABASE() 
                AND table_name = 'liabilities' 
                AND column_name = 'is_ms_party'
            """)
            has_column = cursor.fetchone()[0] > 0
            
            if not has_column:
                cursor.execute("ALTER TABLE liabilities ADD COLUMN is_ms_party BOOLEAN NOT NULL DEFAULT TRUE")
                conn.commit()
                print("Added is_ms_party column to liabilities table.")
        except Exception as e:
            print(f"Note: liabilities table migration check: {e}")
            try:
                conn.rollback()
            except:
                pass
        
        # Migrate existing liabilities to have is_active = TRUE (default) for soft delete
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.COLUMNS 
                WHERE table_schema = DATABASE() 
                AND table_name = 'liabilities' 
                AND column_name = 'is_active'
            """)
            has_column = cursor.fetchone()[0] > 0
            
            if not has_column:
                cursor.execute("ALTER TABLE liabilities ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE AFTER discount_percent")
                conn.commit()
                print("Added is_active column to liabilities table for soft delete.")
        except Exception as e:
            print(f"Note: is_active column migration check: {e}")
            try:
                conn.rollback()
            except:
                pass
        
        # Migrate party_changelog table name and foreign key if needed
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.TABLES 
                WHERE table_schema = DATABASE() 
                AND table_name = 'party_changelog'
            """)
            has_party_changelog = cursor.fetchone()[0] > 0
            
            if has_party_changelog:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.TABLES 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'liability_changelog'
                """)
                has_liability_changelog = cursor.fetchone()[0] > 0
                
                if not has_liability_changelog:
                    # Rename party_changelog to liability_changelog
                    cursor.execute("RENAME TABLE party_changelog TO liability_changelog")
                    # Update foreign key reference
                    try:
                        cursor.execute("ALTER TABLE liability_changelog DROP FOREIGN KEY liability_changelog_ibfk_1")
                    except:
                        pass
                    cursor.execute("""
                        ALTER TABLE liability_changelog 
                        ADD CONSTRAINT fk_liability_changelog_liability 
                        FOREIGN KEY (party_id) REFERENCES liabilities(id) ON DELETE CASCADE
                    """)
                    conn.commit()
                    print("Migrated 'party_changelog' table to 'liability_changelog'.")
        except Exception as e:
            print(f"Note: Changelog table migration check: {e}")
            try:
                conn.rollback()
            except:
                pass
        
        # Create liability_changelog table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS liability_changelog (
                id INT AUTO_INCREMENT PRIMARY KEY,
                party_id INT NOT NULL,
                change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                changes TEXT NOT NULL,
                FOREIGN KEY (party_id) REFERENCES liabilities(id) ON DELETE CASCADE,
                INDEX idx_party_id (party_id),
                INDEX idx_change_date (change_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'liability_changelog' checked/created.")
        
        # Create assets table (name-only master with audit fields)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                updated_by VARCHAR(100),
                UNIQUE KEY unique_name (name),
                INDEX idx_is_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'assets' checked/created.")
        
        # Create expenses table (name-only master with audit fields)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                updated_by VARCHAR(100),
                UNIQUE KEY unique_name (name),
                INDEX idx_is_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'expenses' checked/created.")
        
        # Create vendors table (name-only master with audit fields)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                updated_by VARCHAR(100),
                UNIQUE KEY unique_name (name),
                INDEX idx_is_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'vendors' checked/created.")
        
        # Create auto_numbering table for tracking counters
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_numbering (
                id INT AUTO_INCREMENT PRIMARY KEY,
                counter_type VARCHAR(50) NOT NULL,
                counter_value INT NOT NULL DEFAULT 0,
                party_name VARCHAR(255),
                UNIQUE KEY unique_counter (counter_type, party_name),
                INDEX idx_counter_type (counter_type),
                INDEX idx_party (party_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'auto_numbering' checked/created.")
        
        # Migrate existing data if needed - update unique constraint to composite key
        # This handles the case where the table already exists with the old schema
        try:
            # Check if the new composite unique constraint already exists
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.table_constraints 
                WHERE table_schema = DATABASE() 
                AND table_name = 'auto_numbering' 
                AND constraint_type = 'UNIQUE' 
                AND constraint_name = 'unique_counter'
            """)
            has_new_constraint = cursor.fetchone()[0] > 0
            
            if not has_new_constraint:
                # Try to add the composite unique constraint
                # First, try to drop any old unique constraint on counter_type
                try:
                    # Check for old constraint
                    cursor.execute("SHOW INDEX FROM auto_numbering WHERE Key_name = 'counter_type'")
                    if cursor.fetchone():
                        cursor.execute("ALTER TABLE auto_numbering DROP INDEX counter_type")
                except Exception:
                    # Old constraint might not exist or have different name, continue
                    pass
                
                # Add the new composite unique constraint
                try:
                    cursor.execute("ALTER TABLE auto_numbering ADD UNIQUE KEY unique_counter (counter_type, party_name)")
                    conn.commit()
                    print("Migrated auto_numbering table to use composite unique key.")
                except Exception as e:
                    # Constraint might already exist or table might be empty
                    if "Duplicate key name" not in str(e):
                        print(f"Note: Could not add unique_counter constraint: {e}")
                    conn.rollback()
        except Exception as e:
            # If migration fails, it might be because the constraint doesn't exist or already migrated
            print(f"Note: auto_numbering migration check: {e}")
            try:
                conn.rollback()
            except:
                pass
        
        # Create items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'items' checked/created.")
        
        # Create inward_documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inward_documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                inward_number VARCHAR(50) UNIQUE NOT NULL,
                gp_number VARCHAR(50) NOT NULL,
                sr_number VARCHAR(50),
                ms_party_id INT NOT NULL,
                from_party VARCHAR(255),
                vehicle_number VARCHAR(100),
                driver_name VARCHAR(255),
                total_quantity DECIMAL(10, 2) DEFAULT 0.00,
                document_date DATE NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                edited_by VARCHAR(100) NULL,
                edit_log_history TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (ms_party_id) REFERENCES liabilities(id) ON DELETE RESTRICT,
                INDEX idx_inward_number (inward_number),
                INDEX idx_gp_number (gp_number),
                INDEX idx_sr_number (sr_number),
                INDEX idx_ms_party (ms_party_id),
                INDEX idx_document_date (document_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'inward_documents' checked/created.")
        
        # Create inward_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inward_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                inward_document_id INT NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                measurement INT NOT NULL CHECK (measurement IN (15, 22)),
                quantity DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                FOREIGN KEY (inward_document_id) REFERENCES inward_documents(id) ON DELETE CASCADE,
                UNIQUE KEY unique_item_measurement (inward_document_id, item_name, measurement),
                INDEX idx_item_name (item_name),
                INDEX idx_measurement (measurement)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'inward_items' checked/created.")
        
        # Create transfer_documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfer_documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                transfer_number VARCHAR(50) UNIQUE NOT NULL,
                gp_number VARCHAR(50) NOT NULL,
                sr_number VARCHAR(50),
                ms_party_id INT NOT NULL,
                from_party VARCHAR(255),
                transfer_to VARCHAR(255),
                transfer_to_ms_party_id INT NULL,
                vehicle_number VARCHAR(100),
                driver_name VARCHAR(255),
                total_quantity DECIMAL(10, 2) DEFAULT 0.00,
                transfer_type ENUM('simple', 'by_name') DEFAULT 'simple',
                document_date DATE NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                edited_by VARCHAR(100) NULL,
                edit_log_history TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (ms_party_id) REFERENCES liabilities(id) ON DELETE RESTRICT,
                FOREIGN KEY (transfer_to_ms_party_id) REFERENCES liabilities(id) ON DELETE RESTRICT,
                INDEX idx_transfer_number (transfer_number),
                INDEX idx_gp_number (gp_number),
                INDEX idx_sr_number (sr_number),
                INDEX idx_ms_party (ms_party_id),
                INDEX idx_transfer_type (transfer_type),
                INDEX idx_transfer_to_ms_party (transfer_to_ms_party_id),
                INDEX idx_document_date (document_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'transfer_documents' checked/created.")
        
        # Add transfer_type column if table exists but column doesn't
        try:
            cursor.execute("ALTER TABLE transfer_documents ADD COLUMN transfer_type ENUM('simple', 'by_name') DEFAULT 'simple'")
            print("Added 'transfer_type' column to transfer_documents.")
        except Exception as e:
            if "Duplicate column name" not in str(e):
                print(f"Note: transfer_type column may already exist: {e}")
        
        # Add transfer_to_ms_party_id column if table exists but column doesn't
        try:
            cursor.execute("ALTER TABLE transfer_documents ADD COLUMN transfer_to_ms_party_id INT NULL")
            cursor.execute("ALTER TABLE transfer_documents ADD CONSTRAINT fk_transfer_to_ms_party FOREIGN KEY (transfer_to_ms_party_id) REFERENCES liabilities(id) ON DELETE RESTRICT")
            print("Added 'transfer_to_ms_party_id' column to transfer_documents.")
        except Exception as e:
            if "Duplicate column name" not in str(e) and "Duplicate key name" not in str(e):
                print(f"Note: transfer_to_ms_party_id column may already exist: {e}")
        
        # Create transfer_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfer_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                transfer_document_id INT NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                measurement INT NOT NULL CHECK (measurement IN (15, 22)),
                quantity DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                FOREIGN KEY (transfer_document_id) REFERENCES transfer_documents(id) ON DELETE CASCADE,
                UNIQUE KEY unique_item_measurement (transfer_document_id, item_name, measurement),
                INDEX idx_item_name (item_name),
                INDEX idx_measurement (measurement)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'transfer_items' checked/created.")
        
        # Create outward_documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outward_documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                outward_number VARCHAR(50) UNIQUE NOT NULL,
                gp_number VARCHAR(50) NOT NULL,
                sr_number VARCHAR(50),
                ms_party_id INT NOT NULL,
                from_party VARCHAR(255),
                outward_to VARCHAR(255),
                vehicle_number VARCHAR(100),
                driver_name VARCHAR(255),
                total_quantity DECIMAL(10, 2) DEFAULT 0.00,
                document_date DATE NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                edited_by VARCHAR(100) NULL,
                edit_log_history TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (ms_party_id) REFERENCES liabilities(id) ON DELETE RESTRICT,
                INDEX idx_outward_number (outward_number),
                INDEX idx_gp_number (gp_number),
                INDEX idx_sr_number (sr_number),
                INDEX idx_ms_party (ms_party_id),
                INDEX idx_document_date (document_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'outward_documents' checked/created.")
        
        # Create outward_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outward_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                outward_document_id INT NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                measurement INT NOT NULL CHECK (measurement IN (15, 22)),
                quantity DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                FOREIGN KEY (outward_document_id) REFERENCES outward_documents(id) ON DELETE CASCADE,
                UNIQUE KEY unique_item_measurement (outward_document_id, item_name, measurement),
                INDEX idx_item_name (item_name),
                INDEX idx_measurement (measurement)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'outward_items' checked/created.")
        
        # Create stock table (materialized view for performance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ms_party_id INT NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                measurement INT NOT NULL CHECK (measurement IN (15, 22)),
                total_inward DECIMAL(10, 2) DEFAULT 0.00,
                total_transfer DECIMAL(10, 2) DEFAULT 0.00,
                transfer_bn_in DECIMAL(10, 2) DEFAULT 0.00,
                transfer_bn_out DECIMAL(10, 2) DEFAULT 0.00,
                total_outward DECIMAL(10, 2) DEFAULT 0.00,
                remaining_stock DECIMAL(10, 2) GENERATED ALWAYS AS (total_inward - total_transfer - transfer_bn_out + transfer_bn_in - total_outward) STORED,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (ms_party_id) REFERENCES liabilities(id) ON DELETE RESTRICT,
                UNIQUE KEY unique_stock (ms_party_id, item_name, measurement),
                INDEX idx_ms_party (ms_party_id),
                INDEX idx_item_name (item_name),
                INDEX idx_measurement (measurement)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'stock' checked/created.")
        
        # Create stock_ledgers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_ledgers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                party_id INT NULL,
                ledger_name VARCHAR(255) NOT NULL,
                is_ud_ledger BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (party_id) REFERENCES liabilities(id) ON DELETE RESTRICT,
                UNIQUE KEY unique_ledger_name (ledger_name),
                UNIQUE KEY unique_party_ledger (party_id),
                INDEX idx_party_id (party_id),
                INDEX idx_is_ud_ledger (is_ud_ledger)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'stock_ledgers' checked/created.")
        
        # Fix unique constraint to allow NULL party_id (for UD ledger)
        try:
            cursor.execute("""
                SELECT CONSTRAINT_NAME 
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'stock_ledgers' 
                AND CONSTRAINT_NAME = 'unique_party_ledger'
            """)
            if cursor.fetchone():
                # Drop and recreate with proper NULL handling
                cursor.execute("ALTER TABLE stock_ledgers DROP INDEX unique_party_ledger")
                cursor.execute("""
                    CREATE UNIQUE INDEX unique_party_ledger ON stock_ledgers (party_id)
                """)
        except Exception as e:
            print(f"Note: unique_party_ledger constraint check: {e}")
        
        # Create stock_ledger_entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_ledger_entries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ledger_id INT NOT NULL,
                entry_date DATE NOT NULL,
                transaction_type VARCHAR(50) NOT NULL,
                transaction_number VARCHAR(100) NOT NULL,
                particulars VARCHAR(255) NOT NULL,
                description TEXT,
                item_name VARCHAR(255) NOT NULL,
                qty_15_yards DECIMAL(10, 2) DEFAULT 0.00,
                qty_22_yards DECIMAL(10, 2) DEFAULT 0.00,
                total_qty_debit DECIMAL(10, 2) DEFAULT 0.00,
                total_qty_credit DECIMAL(10, 2) DEFAULT 0.00,
                balance DECIMAL(10, 2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ledger_id) REFERENCES stock_ledgers(id) ON DELETE RESTRICT,
                INDEX idx_ledger_id (ledger_id),
                INDEX idx_entry_date (entry_date),
                INDEX idx_transaction_type (transaction_type),
                INDEX idx_transaction_number (transaction_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'stock_ledger_entries' checked/created.")
        
        # Create default UNIVERSAL DYEING (UD) ledger if it doesn't exist
        cursor.execute("""
            SELECT id FROM stock_ledgers WHERE is_ud_ledger = TRUE LIMIT 1
        """)
        ud_ledger = cursor.fetchone()
        if not ud_ledger:
            cursor.execute("""
                INSERT INTO stock_ledgers (ledger_name, is_ud_ledger, party_id)
                VALUES ('UNIVERSAL DYEING (UD)', TRUE, NULL)
            """)
            conn.commit()
            print("Default UNIVERSAL DYEING (UD) ledger created.")
        
        # Migration: Add transfer_bn_in and transfer_bn_out columns if they don't exist
        try:
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'stock' 
                AND COLUMN_NAME = 'transfer_bn_in'
            """)
            if not cursor.fetchone():
                print("Migrating stock table: Adding transfer_bn_in and transfer_bn_out columns...")
                cursor.execute("""
                    ALTER TABLE stock 
                    ADD COLUMN transfer_bn_in DECIMAL(10, 2) DEFAULT 0.00 AFTER total_transfer,
                    ADD COLUMN transfer_bn_out DECIMAL(10, 2) DEFAULT 0.00 AFTER transfer_bn_in
                """)
                # Update remaining_stock calculation
                cursor.execute("""
                    ALTER TABLE stock 
                    MODIFY COLUMN remaining_stock DECIMAL(10, 2) GENERATED ALWAYS AS 
                    (total_inward - total_transfer - transfer_bn_out + transfer_bn_in - total_outward) STORED
                """)
                conn.commit()
                print("Migration completed: transfer_bn_in and transfer_bn_out columns added.")
        except Exception as e:
            print(f"Migration check/execution error (may be expected if columns already exist): {e}")
            conn.rollback()
        
        # Create invoices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_number VARCHAR(50) UNIQUE NOT NULL,
                ms_party_id INT NOT NULL,
                number_of_items INT NOT NULL DEFAULT 0,
                discount_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                discount_source ENUM('auto', 'manual') NOT NULL DEFAULT 'auto',
                total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                invoice_date DATE NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                edited_by VARCHAR(100) NULL,
                edit_log_history TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (ms_party_id) REFERENCES liabilities(id) ON DELETE RESTRICT,
                INDEX idx_invoice_number (invoice_number),
                INDEX idx_ms_party (ms_party_id),
                INDEX idx_invoice_date (invoice_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'invoices' checked/created.")
        
        # Create invoice_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_id INT NOT NULL,
                outward_document_id INT NULL,
                transfer_document_id INT NULL,
                item_name VARCHAR(255) NOT NULL,
                measurement INT NOT NULL CHECK (measurement IN (15, 22)),
                quantity DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                rate DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (outward_document_id) REFERENCES outward_documents(id) ON DELETE RESTRICT,
                FOREIGN KEY (transfer_document_id) REFERENCES transfer_documents(id) ON DELETE RESTRICT,
                INDEX idx_invoice_id (invoice_id),
                INDEX idx_outward_document_id (outward_document_id),
                INDEX idx_transfer_document_id (transfer_document_id),
                INDEX idx_item_name (item_name),
                CHECK ((outward_document_id IS NOT NULL AND transfer_document_id IS NULL) OR 
                       (outward_document_id IS NULL AND transfer_document_id IS NOT NULL))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'invoice_items' checked/created.")

        # Create financial_ledgers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_ledgers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                party_id INT NULL,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (party_id) REFERENCES liabilities(id) ON DELETE CASCADE,
                UNIQUE KEY unique_name (name),
                UNIQUE KEY unique_party_ledger (party_id),
                INDEX idx_party_id (party_id),
                INDEX idx_is_default (is_default)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'financial_ledgers' checked/created.")

        # Migration: Ensure 'financial_ledgers' table has 'name' column (not 'ledger_name')
        try:
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'financial_ledgers' 
                AND COLUMN_NAME = 'ledger_name'
            """)
            if cursor.fetchone():
                print("Migrating financial_ledgers: Renaming ledger_name to name...")
                cursor.execute("ALTER TABLE financial_ledgers CHANGE COLUMN ledger_name name VARCHAR(255) NOT NULL")
                conn.commit()
        except Exception as e:
            print(f"Note: financial_ledgers migration check: {e}")

        # Create financial_ledger_entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_ledger_entries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ledger_id INT NOT NULL,
                entry_date DATE NOT NULL,
                particulars VARCHAR(255) NOT NULL,
                invoice_number VARCHAR(100),
                voucher_number VARCHAR(100),
                description TEXT,
                debit DECIMAL(15, 2) DEFAULT 0.00,
                credit DECIMAL(15, 2) DEFAULT 0.00,
                balance DECIMAL(15, 2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ledger_id) REFERENCES financial_ledgers(id) ON DELETE CASCADE,
                INDEX idx_ledger_id (ledger_id),
                INDEX idx_entry_date (entry_date),
                INDEX idx_invoice_number (invoice_number),
                INDEX idx_voucher_number (voucher_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'financial_ledger_entries' checked/created.")

        # Migration: Ensure 'financial_ledger_entries' has correct columns
        try:
            cursor.execute("DESCRIBE financial_ledger_entries")
            columns = [row[0] for row in cursor.fetchall()]
            
            if 'transaction_number' in columns and 'invoice_number' not in columns:
                print("Migrating financial_ledger_entries: Renaming transaction_number to invoice_number...")
                cursor.execute("ALTER TABLE financial_ledger_entries CHANGE COLUMN transaction_number invoice_number VARCHAR(100)")
                conn.commit()
            
            if 'transaction_type' in columns:
                print("Migrating financial_ledger_entries: Removing transaction_type column...")
                cursor.execute("ALTER TABLE financial_ledger_entries DROP COLUMN transaction_type")
                conn.commit()
                
            # Refresh columns list
            cursor.execute("DESCRIBE financial_ledger_entries")
            columns = [row[0] for row in cursor.fetchall()]
            
            if 'voucher_number' not in columns:
                print("Migrating financial_ledger_entries: Adding voucher_number column...")
                cursor.execute("ALTER TABLE financial_ledger_entries ADD COLUMN voucher_number VARCHAR(100) AFTER invoice_number")
                cursor.execute("CREATE INDEX idx_voucher_number ON financial_ledger_entries (voucher_number)")
                conn.commit()
        except Exception as e:
            print(f"Note: financial_ledger_entries migration check: {e}")

        # Create default 'Dyeing service charges' ledger if it doesn't exist
        cursor.execute("""
            SELECT id FROM financial_ledgers WHERE name = 'Dyeing service charges' LIMIT 1
        """)
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO financial_ledgers (name, is_default, party_id)
                VALUES ('Dyeing service charges', TRUE, NULL)
            """)
            print("Default 'Dyeing service charges' ledger created.")

        # Migration: Post existing invoices to financial ledgers if not already present
        try:
            # Check for invoices not in ledger entries
            cursor.execute("""
                SELECT i.id, i.invoice_number, i.ms_party_id, i.total_amount, i.invoice_date, l.name as party_name
                FROM invoices i
                JOIN liabilities l ON i.ms_party_id = l.id
                WHERE i.invoice_number NOT IN (
                    SELECT DISTINCT invoice_number FROM financial_ledger_entries WHERE invoice_number IS NOT NULL
                )
            """)
            invoices_to_post = cursor.fetchall()
            
            if invoices_to_post:
                print(f"Migrating {len(invoices_to_post)} existing invoices to financial ledgers...")
                
                # Get default ledger ID
                cursor.execute("SELECT id FROM financial_ledgers WHERE name = 'Dyeing service charges' LIMIT 1")
                income_ledger_row = cursor.fetchone()
                if income_ledger_row:
                    income_ledger_id = income_ledger_row[0]
                    
                    for inv_id, inv_num, ms_party_id, total_amt, inv_date, party_name in invoices_to_post:
                        # 1. Get or create party ledger
                        cursor.execute("SELECT id FROM financial_ledgers WHERE party_id = %s", (ms_party_id,))
                        party_ledger_row = cursor.fetchone()
                        if party_ledger_row:
                            party_ledger_id = party_ledger_row[0]
                        else:
                            cursor.execute("INSERT INTO financial_ledgers (name, party_id, is_default) VALUES (%s, %s, FALSE)", (party_name, ms_party_id))
                            party_ledger_id = cursor.lastrowid
                        
                        # 2. Post to Party Ledger (Debit)
                        cursor.execute("""
                            INSERT INTO financial_ledger_entries 
                            (ledger_id, entry_date, particulars, invoice_number, description, debit, credit, balance)
                            VALUES (%s, %s, 'Dyeing services', %s, 'Dyeing charges', %s, 0.00, 0.00)
                        """, (party_ledger_id, inv_date, inv_num, total_amt))
                        
                        # 3. Post to Income Ledger (Credit)
                        cursor.execute("""
                            INSERT INTO financial_ledger_entries 
                            (ledger_id, entry_date, particulars, invoice_number, description, debit, credit, balance)
                            VALUES (%s, %s, %s, %s, 'service income', 0.00, %s, 0.00)
                        """, (income_ledger_id, inv_date, party_name, inv_num, total_amt))
                    
                    conn.commit()
                    print("Migration of existing invoices completed.")
                    
                    # Update all balances (simplified)
                    cursor.execute("SELECT id FROM financial_ledgers")
                    all_ledger_ids = [row[0] for row in cursor.fetchall()]
                    for lid in all_ledger_ids:
                        cursor.execute("SELECT id, debit, credit FROM financial_ledger_entries WHERE ledger_id = %s ORDER BY entry_date ASC, id ASC", (lid,))
                        entries = cursor.fetchall()
                        rb = 0.0
                        for eid, db, cr in entries:
                            rb += float(db or 0) - float(cr or 0)
                            cursor.execute("UPDATE financial_ledger_entries SET balance = %s WHERE id = %s", (rb, eid))
                    conn.commit()
        except Exception as e:
            print(f"Note: Existing invoices migration check: {e}")

        # Add transfer_document_id column if table exists but column doesn't
        try:
            cursor.execute("ALTER TABLE invoice_items ADD COLUMN transfer_document_id INT NULL")
            cursor.execute("ALTER TABLE invoice_items ADD CONSTRAINT fk_invoice_transfer FOREIGN KEY (transfer_document_id) REFERENCES transfer_documents(id) ON DELETE RESTRICT")
            cursor.execute("ALTER TABLE invoice_items MODIFY COLUMN outward_document_id INT NULL")
            print("Added 'transfer_document_id' column to invoice_items and made outward_document_id nullable.")
        except Exception as e:
            if "Duplicate column name" not in str(e) and "Duplicate key name" not in str(e) and "doesn't have a default value" not in str(e):
                print(f"Note: transfer_document_id column may already exist: {e}")
        
        # Create voucher_master table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voucher_master (
                id INT AUTO_INCREMENT PRIMARY KEY,
                voucher_no VARCHAR(50) UNIQUE NOT NULL,
                voucher_type ENUM('CP', 'CR', 'JV') NOT NULL,
                voucher_date DATE NOT NULL,
                description TEXT,
                total_amount DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                created_by VARCHAR(100) NULL,
                edited_by VARCHAR(100) NULL,
                edit_log_history TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_voucher_no (voucher_no),
                INDEX idx_voucher_type (voucher_type),
                INDEX idx_voucher_date (voucher_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'voucher_master' checked/created.")
        
        # Create voucher_detail table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voucher_detail (
                id INT AUTO_INCREMENT PRIMARY KEY,
                voucher_id INT NOT NULL,
                party_id INT NULL,
                debit_amount DECIMAL(15, 2) NULL,
                credit_amount DECIMAL(15, 2) NULL,
                FOREIGN KEY (voucher_id) REFERENCES voucher_master(id) ON DELETE CASCADE,
                FOREIGN KEY (party_id) REFERENCES liabilities(id) ON DELETE RESTRICT,
                INDEX idx_voucher_id (voucher_id),
                INDEX idx_party_id (party_id),
                CHECK ((debit_amount IS NOT NULL AND credit_amount IS NULL) OR 
                       (debit_amount IS NULL AND credit_amount IS NOT NULL))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'voucher_detail' checked/created.")
        
        # Migration: Add asset_id, expense_id, vendor_id columns to voucher_detail
        try:
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'voucher_detail' 
                AND COLUMN_NAME = 'asset_id'
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE voucher_detail ADD COLUMN asset_id INT NULL")
                cursor.execute("""
                    ALTER TABLE voucher_detail 
                    ADD CONSTRAINT fk_voucher_asset 
                    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE RESTRICT
                """)
                cursor.execute("CREATE INDEX idx_asset_id ON voucher_detail (asset_id)")
                print("Added 'asset_id' column to voucher_detail for asset parties.")
        except Exception as e:
            if "Duplicate column name" not in str(e) and "Duplicate key name" not in str(e):
                print(f"Note: asset_id column may already exist: {e}")
        
        try:
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'voucher_detail' 
                AND COLUMN_NAME = 'expense_id'
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE voucher_detail ADD COLUMN expense_id INT NULL")
                cursor.execute("""
                    ALTER TABLE voucher_detail 
                    ADD CONSTRAINT fk_voucher_expense 
                    FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE RESTRICT
                """)
                cursor.execute("CREATE INDEX idx_expense_id ON voucher_detail (expense_id)")
                print("Added 'expense_id' column to voucher_detail for expense parties.")
        except Exception as e:
            if "Duplicate column name" not in str(e) and "Duplicate key name" not in str(e):
                print(f"Note: expense_id column may already exist: {e}")
        
        try:
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'voucher_detail' 
                AND COLUMN_NAME = 'vendor_id'
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE voucher_detail ADD COLUMN vendor_id INT NULL")
                cursor.execute("""
                    ALTER TABLE voucher_detail 
                    ADD CONSTRAINT fk_voucher_vendor 
                    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE RESTRICT
                """)
                cursor.execute("CREATE INDEX idx_vendor_id ON voucher_detail (vendor_id)")
                print("Added 'vendor_id' column to voucher_detail for vendor parties.")
        except Exception as e:
            if "Duplicate column name" not in str(e) and "Duplicate key name" not in str(e):
                print(f"Note: vendor_id column may already exist: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error ensuring database exists: {e}")
        return False


class MySQLConnectionPoolManager:
    """Thread-safe MySQL connection pool manager"""
    
    def __init__(self):
        self._pool: Optional[pooling.MySQLConnectionPool] = None
        self._lock = threading.Lock()
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize connection pool at startup"""
        with self._lock:
            if self._initialized:
                return True
            
            try:
                # Ensure database exists before creating pool
                if not ensure_database_exists():
                    print("Failed to ensure database exists")
                    return False
                
                # Create pool configuration
                pool_config = {
                    "pool_name": "tms_pool",
                    "pool_size": POOL_CONFIG["max_connections"],
                    "pool_reset_session": True,
                    **DB_CONFIG
                }
                
                # Create connection pool
                self._pool = pooling.MySQLConnectionPool(**pool_config)
                
                # Pre-create minimum connections
                connections = []
                for _ in range(POOL_CONFIG["min_connections"]):
                    try:
                        conn = self._pool.get_connection()
                        connections.append(conn)
                    except Exception as e:
                        print(f"Warning: Could not pre-create connection: {e}")
                
                # Return connections to pool
                for conn in connections:
                    conn.close()
                
                self._initialized = True
                print(f"Connection pool initialized: {POOL_CONFIG['min_connections']}-{POOL_CONFIG['max_connections']} connections")
                return True
                
            except Exception as e:
                print(f"Failed to initialize connection pool: {e}")
                self._initialized = False
                return False
    
    def get_connection(self, timeout: float = None) -> Optional[mysql.connector.MySQLConnection]:
        """Borrow a connection from the pool"""
        if not self._initialized:
            if not self.initialize():
                return None
        
        timeout = timeout or POOL_CONFIG["timeout"]
        try:
            conn = self._pool.get_connection()
            return conn
        except Exception as e:
            print(f"Failed to get connection from pool: {e}")
            return None
    
    def return_connection(self, conn: mysql.connector.MySQLConnection) -> None:
        """Return connection to pool"""
        if conn:
            try:
                conn.close()  # Returns connection to pool
            except Exception:
                pass
    
    def health_check(self) -> dict:
        """Check pool health"""
        if not self._initialized:
            return {"status": "not_initialized", "active": 0, "total": 0}
        
        try:
            # Try to get a connection
            conn = self.get_connection(timeout=1.0)
            if conn:
                self.return_connection(conn)
                return {
                    "status": "healthy",
                    "pool_size": self._pool.pool_size,
                    "pool_name": self._pool.pool_name
                }
            else:
                return {"status": "unavailable", "active": 0, "total": 0}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def close_all(self) -> None:
        """Close all connections in pool"""
        with self._lock:
            # Pool will be garbage collected
            self._pool = None
            self._initialized = False


# Global pool instance
db_pool = MySQLConnectionPoolManager()

