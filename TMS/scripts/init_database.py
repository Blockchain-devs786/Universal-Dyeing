"""Initialize TMS Database"""

import mysql.connector
from common.config import DB_CONFIG


def init_database():
    """Create database and tables"""
    try:
        # Connect without database first
        config = DB_CONFIG.copy()
        database = config.pop("database")
        
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"Database '{database}' created or already exists.")
        
        # Use database
        cursor.execute(f"USE {database}")
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                role ENUM('ADMIN','USER') DEFAULT 'USER',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        print("Table 'users' created or already exists.")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False


if __name__ == "__main__":
    init_database()

