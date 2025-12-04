import sqlite3
import json
import os
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

DB_PATH = os.path.join(os.path.dirname(__file__), '../.tmp/local_state.db')
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if DATABASE_URL:
        if not psycopg2:
            raise ImportError("psycopg2 is required for PostgreSQL but not installed.")
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(conn, query, params=()):
    cursor = conn.cursor()
    
    # Adapt placeholders
    if DATABASE_URL:
        # Postgres uses %s
        query = query.replace('?', '%s')
        # Postgres SERIAL vs AUTOINCREMENT
        query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    
    try:
        cursor.execute(query, params)
        return cursor
    except Exception as e:
        print(f"DB Error: {e}")
        raise e

def init_db():
    if not DATABASE_URL:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
    conn = get_db_connection()
    
    # Leads table
    execute_query(conn, '''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            phone TEXT,
            source TEXT,
            status TEXT DEFAULT 'new',
            hubspot_id TEXT,
            lead_score INTEGER,
            intent TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Events table
    execute_query(conn, '''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            event_type TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_lead(lead_data):
    conn = get_db_connection()
    
    try:
        cursor = execute_query(conn, '''
            INSERT INTO leads (email, name, phone, source, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            lead_data.get('email'),
            lead_data.get('name'),
            lead_data.get('phone'),
            lead_data.get('source'),
            json.dumps(lead_data.get('metadata', {}))
        ))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None # Duplicate
    except Exception as e:
        # Check for Postgres UniqueViolation if psycopg2 is available
        if psycopg2 and isinstance(e, psycopg2.errors.UniqueViolation):
            return None
        raise e
    finally:
        conn.close()

def get_lead_by_email(email):
    conn = get_db_connection()
    cursor = execute_query(conn, 'SELECT * FROM leads WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        lead = dict(row)
        if lead.get('metadata') and isinstance(lead['metadata'], str):
            try:
                lead['metadata'] = json.loads(lead['metadata'])
            except json.JSONDecodeError:
                lead['metadata'] = {}
        return lead
    return None

def update_lead_hubspot_id(local_id, hubspot_id):
    conn = get_db_connection()
    execute_query(conn, 'UPDATE leads SET hubspot_id = ? WHERE id = ?', (hubspot_id, local_id))
    conn.commit()
    conn.close()

def update_lead_analysis(lead_id, analysis):
    conn = get_db_connection()
    execute_query(conn, '''
        UPDATE leads 
        SET lead_score = ?, intent = ?, status = ?
        WHERE id = ?
    ''', (
        analysis.get('score'),
        analysis.get('intent'),
        'analyzed',
        lead_id
    ))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    if DATABASE_URL:
        print("Database initialized (PostgreSQL)")
    else:
        print(f"Database initialized at {DB_PATH} (SQLite)")
