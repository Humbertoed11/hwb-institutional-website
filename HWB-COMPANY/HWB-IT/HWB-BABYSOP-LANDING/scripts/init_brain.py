import os
import psycopg2
from dotenv import load_dotenv

# Load local .env if it exists
load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def init_db():
    print("--- George Bytes: Initializing Monolithic Neural Core ---")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            # 1. Interaction Core
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "HEX_InteractionCore" (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT,
                    user_prompt TEXT,
                    agent_explanation TEXT,
                    tools_used JSONB,
                    technical_data JSONB,
                    status TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 2. Knowledge Scars
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "HEX_KnowledgeScars" (
                    id SERIAL PRIMARY KEY,
                    description TEXT NOT NULL,
                    category TEXT DEFAULT 'General',
                    status TEXT DEFAULT 'Pending',
                    impact_level INTEGER DEFAULT 3,
                    implemented_fix TEXT,
                    preventative_rule TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            


            # 5. HEX_Users
            cur.execute("""
                CREATE TABLE IF NOT EXISTS "HEX_Users" (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'User',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            from werkzeug.security import generate_password_hash
            cur.execute('SELECT COUNT(*) FROM "HEX_Users" WHERE username = %s', ('humberto',))
            if cur.fetchone()[0] == 0:
                p_hash = generate_password_hash('hexgrowth2026!')
                cur.execute('INSERT INTO "HEX_Users" (username, password_hash, role) VALUES (%s, %s, %s)', ('humberto', p_hash, 'Admin'))
                print("SUCCESS: Default user 'humberto' created.")
                
            cur.execute('SELECT COUNT(*) FROM "HEX_Users" WHERE username = %s', ('Ddominguez',))
            if cur.fetchone()[0] == 0:
                p_hash = generate_password_hash('money2026')
                cur.execute('INSERT INTO "HEX_Users" (username, password_hash, role) VALUES (%s, %s, %s)', ('Ddominguez', p_hash, 'User'))
                print("SUCCESS: User 'Ddominguez' created.")
            
            print("SUCCESS: HEXGROWTH Neural Cores Initialized.")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"FAILURE: Database initialization failed. {e}")

if __name__ == "__main__":
    init_db()
