import sqlite3
import os
from flask import g

DATABASE = 'instance/GEE.db'

# Database connection helper functions
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def modify_db(query, args=(), get_lastrowid=False):
    conn = get_db()
    cursor = conn.execute(query, args)
    conn.commit()
    if get_lastrowid:
        return cursor.lastrowid
    return None

# Ensure instance directory exists and initialize rule groups tables
def init_db():
    os.makedirs('instance', exist_ok=True)

    # Create necessary tables for rule groups
    with sqlite3.connect(DATABASE) as conn:
        # Create rule tables
        conn.execute('''
            CREATE TABLE IF NOT EXISTS GRG_RULES (
                RULE_ID INTEGER PRIMARY KEY,
                RULE_NAME TEXT NOT NULL,
                RULE_TYPE TEXT,
                DESCRIPTION TEXT,
                CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
                UPDATE_DATE DATETIME
            )
        ''')

        # Create rule groups table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS GRG_RULE_GROUPS (
                GRG_ID INTEGER PRIMARY KEY,
                GROUP_NAME TEXT NOT NULL,
                COND_TYPE TEXT,
                GRG_ID_PARENT INTEGER,
                DESCRIPTION TEXT,
                COND_GRG_ID_START INTEGER,
                ACT_GRG_ID_START INTEGER,
                CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
                UPDATE_DATE DATETIME,
                FOREIGN KEY (GRG_ID_PARENT) REFERENCES GRG_RULE_GROUPS(GRG_ID)
            )
        ''')

        # Create mapping table for rule groups and rules
        conn.execute('''
            CREATE TABLE IF NOT EXISTS GRG_RULE_GROUP_RULES (
                MAPPING_ID INTEGER PRIMARY KEY,
                GRG_ID INTEGER,
                RULE_ID INTEGER,
                SEQUENCE INTEGER,
                CREATE_DATE DATETIME DEFAULT CURRENT_TIMESTAMP,
                UPDATE_DATE DATETIME,
                FOREIGN KEY (GRG_ID) REFERENCES GRG_RULE_GROUPS(GRG_ID),
                FOREIGN KEY (RULE_ID) REFERENCES GRG_RULES(RULE_ID)
            )
        ''')

        # Check if we need to insert sample data (only if tables are empty)
        cursor = conn.execute("SELECT COUNT(*) FROM GRG_RULES")
        count = cursor.fetchone()[0]

        if count == 0:
            # Insert sample rules for testing
            sample_rules = [
                (1, 'Validate Email Format', 'VALIDATION', 'Validates that an email address is properly formatted'),
                (2, 'Check Required Fields', 'VALIDATION', 'Checks that all required fields have values'),
                (3, 'Calculate Total Amount', 'CALCULATION', 'Calculates the total amount including taxes and fees'),
                (4, 'Format Phone Number', 'FORMATTING', 'Formats phone numbers to a standardized format'),
                (5, 'Verify Address', 'VALIDATION', 'Verifies that an address is valid and properly formatted')
            ]

            conn.executemany('''
                INSERT INTO GRG_RULES (RULE_ID, RULE_NAME, RULE_TYPE, DESCRIPTION)
                VALUES (?, ?, ?, ?)
            ''', sample_rules)

            conn.commit()
