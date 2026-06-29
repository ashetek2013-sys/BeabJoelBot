import sqlite3

conn = sqlite3.connect("beabjoel.db")
cursor = conn.cursor()

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    username TEXT,
    full_name TEXT,
    approved INTEGER DEFAULT 0,
    rejected INTEGER DEFAULT 0
)
""")

# Matches table
cursor.execute("""
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team1 TEXT,
    team2 TEXT,
    match_time TEXT,
    result TEXT
)
""")

# Predictions table
cursor.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    match_id INTEGER,
    predicted_score TEXT
)
""")

# Scores table
cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0
)
""")

# ---------------- SETTINGS ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cursor.execute("""
INSERT OR IGNORE INTO settings (key, value)
VALUES ('predictions_blocked', '0')
""")

---------- Add new columns safely ----------

def add_column(table, column, definition):
   cursor.execute(f"PRAGMA table_info({table})")
   columns = [row[1] for row in cursor.fetchall()]

   if column not in columns:
       cursor.execute(
           f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
       )

Added only if missing
add_column("matches", "manually_open", "INTEGER DEFAULT 0")
add_column("matches", "prediction_blocked", "INTEGER DEFAULT 0")


try:
    cursor.execute("""
    ALTER TABLE matches
    ADD COLUMN manually_open INTEGER DEFAULT 0
    """)
except sqlite3.OperationalError:
    pass

# cursor.execute("""
# ALTER TABLE matches
# ADD COLUMN manually_open INTEGER DEFAULT 0
# """)

conn.commit()
conn.close()

print("Database initialized successfully.")