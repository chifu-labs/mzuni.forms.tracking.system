"""
Run this once to add missing columns to your existing database.
Usage: python migrate_db.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'mzuzu_dts.db')

# Fallback: check same directory
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join(os.path.dirname(__file__), 'mzuzu_dts.db')

if not os.path.exists(DB_PATH):
    print("Database file not found. Run the Flask app first to create it.")
    exit(1)

print(f"✅ Found database at: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

def add_column_if_missing(table, column, col_type):
    cur.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cur.fetchall()]
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"  ✅ Added {table}.{column}")
    else:
        print(f"  ⏭️  {table}.{column} already exists")

print("\n── Migrating 'approvals' table ──")
add_column_if_missing('approvals', 'officer_name',   'VARCHAR(120)')
add_column_if_missing('approvals', 'officer_email',  'VARCHAR(120)')
add_column_if_missing('approvals', 'step_name',      'VARCHAR(150)')
add_column_if_missing('approvals', 'comment',        'TEXT')
add_column_if_missing('approvals', 'section_data',   'TEXT')
add_column_if_missing('approvals', 'signature_path', 'VARCHAR(256)')
add_column_if_missing('approvals', 'ip_address',     'VARCHAR(50)')
add_column_if_missing('approvals', 'verified_name',  'VARCHAR(120)')
add_column_if_missing('approvals', 'approved_at',    'DATETIME')

print("\n── Migrating 'rejections' table ──")
add_column_if_missing('rejections', 'officer_name',  'VARCHAR(120)')
add_column_if_missing('rejections', 'officer_email', 'VARCHAR(120)')
add_column_if_missing('rejections', 'step_name',     'VARCHAR(150)')
add_column_if_missing('rejections', 'ip_address',    'VARCHAR(50)')
add_column_if_missing('rejections', 'rejected_at',   'DATETIME')

conn.commit()
conn.close()
print("\n✅ Migration complete. Restart Flask and the error should be gone.")
