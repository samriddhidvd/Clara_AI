#!/usr/bin/env python3
"""
Clara AI - Persistence and Tracking System
------------------------------------------
Industrial-grade SQLite backend for tracking account progression through 
the automation pipeline. Maintains the canonical state for all customer 
configuration artifacts.

Author: Clara AI Pipeline Team
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "outputs/pipeline_tracker.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            company_name TEXT,
            status TEXT,
            last_updated TEXT,
            v1_memo_path TEXT,
            v1_agent_path TEXT,
            v2_memo_path TEXT,
            v2_agent_path TEXT,
            changelog_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def update_account_status(account_id, status, company_name=None, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get existing data
    cursor.execute("SELECT company_name FROM accounts WHERE account_id = ?", (account_id,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("INSERT INTO accounts (account_id, status, last_updated) VALUES (?, ?, ?)",
                       (account_id, status, datetime.now().isoformat()))
    else:
        cursor.execute("UPDATE accounts SET status = ?, last_updated = ? WHERE account_id = ?",
                       (status, datetime.now().isoformat(), account_id))
    
    if company_name:
        cursor.execute("UPDATE accounts SET company_name = ? WHERE account_id = ?", (company_name, account_id))
    
    for key, value in kwargs.items():
        if key in ["v1_memo_path", "v1_agent_path", "v2_memo_path", "v2_agent_path", "changelog_path"]:
            cursor.execute(f"UPDATE accounts SET {key} = ? WHERE account_id = ?", (value, account_id))
            
    conn.commit()
    conn.close()

def get_account(account_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def list_all_accounts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts")
    rows = cursor.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH)
