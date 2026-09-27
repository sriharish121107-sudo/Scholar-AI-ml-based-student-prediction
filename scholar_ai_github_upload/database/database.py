import os
import sqlite3
import json
import shutil
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

# Resolve DB Path
# If running on Vercel, use /tmp which is writable, and copy database template there
if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    DB_PATH = "/tmp/scholar_ai.db"
    STATIC_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "scholar_ai.db")
    if not os.path.exists(DB_PATH) and os.path.exists(STATIC_DB):
        try:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            shutil.copy(STATIC_DB, DB_PATH)
            print("Successfully copied static database template to /tmp/scholar_ai.db")
        except Exception as e:
            print("Database template copy error:", e)
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "scholar_ai.db")


# Cursor adapters for PostgreSQL / SQLite cross-compatibility
class SqliteCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
        
    def execute(self, query, params=None):
        if params is None:
            return self.cursor.execute(query)
        return self.cursor.execute(query, params)
        
    def fetchone(self):
        return self.cursor.fetchone()
        
    def fetchall(self):
        return self.cursor.fetchall()
        
    def __getattr__(self, name):
        return getattr(self.cursor, name)


class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
        
    def execute(self, query, params=None):
        query_pg = query.replace("?", "%s")
        if "AUTOINCREMENT" in query_pg:
            query_pg = query_pg.replace("AUTOINCREMENT", "")
            query_pg = query_pg.replace("INTEGER PRIMARY KEY", "SERIAL PRIMARY KEY")
        
        if params is None:
            return self.cursor.execute(query_pg)
        return self.cursor.execute(query_pg, params)
        
    def fetchone(self):
        return self.cursor.fetchone()
        
    def fetchall(self):
        return self.cursor.fetchall()
        
    def __getattr__(self, name):
        return getattr(self.cursor, name)


class DBAdapter:
    def __init__(self, conn, is_postgres=False):
        self.conn = conn
        self.is_postgres = is_postgres
        
    def cursor(self):
        cur = self.conn.cursor()
        if self.is_postgres:
            return PostgresCursorWrapper(cur)
        else:
            return SqliteCursorWrapper(cur)
            
    def commit(self):
        self.conn.commit()
        
    def close(self):
        self.conn.close()


def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.DictCursor)
            return DBAdapter(conn, is_postgres=True)
        except Exception as e:
            print("PostgreSQL connection error, falling back to SQLite:", e)
            
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return DBAdapter(conn, is_postgres=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create teachers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    """)
    
    # Create students table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        attendance REAL NOT NULL,
        study_hours REAL NOT NULL,
        assignment_completion REAL NOT NULL,
        previous_grade REAL NOT NULL,
        class_participation REAL NOT NULL,
        family_support TEXT NOT NULL,
        parental_education TEXT NOT NULL,
        internet_access TEXT NOT NULL,
        extra_activities TEXT NOT NULL,
        predicted_category TEXT,
        confidence REAL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create predictions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER,
        student_id TEXT NOT NULL,
        attendance REAL NOT NULL,
        study_hours REAL NOT NULL,
        assignment_percentage REAL NOT NULL,
        previous_grade REAL NOT NULL,
        class_participation REAL NOT NULL,
        family_support TEXT NOT NULL,
        parental_education TEXT NOT NULL,
        internet_access TEXT NOT NULL,
        extra_activities TEXT NOT NULL,
        prediction TEXT NOT NULL,
        confidence REAL NOT NULL,
        prob_high REAL NOT NULL,
        prob_average REAL NOT NULL,
        prob_at_risk REAL NOT NULL,
        prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id)
    )
    """)
    
    # Check if predictions table needs column migration
    if not getattr(conn, "is_postgres", False):
        cursor.execute("PRAGMA table_info(predictions)")
        cols = [row[1] for row in cursor.fetchall()]
        if cols and "teacher_id" not in cols:
            try:
                cursor.execute("ALTER TABLE predictions ADD COLUMN teacher_id INTEGER REFERENCES teachers(id)")
                print("Database migration: added teacher_id column to predictions table.")
            except sqlite3.OperationalError as e:
                print("Migration warning:", e)

    # Create model_metrics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_metrics (
        model_name TEXT PRIMARY KEY,
        accuracy REAL,
        precision REAL,
        recall REAL,
        f1_score REAL,
        cv_score REAL,
        confusion_matrix TEXT,
        last_trained TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create interventions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        category TEXT NOT NULL,
        notes TEXT,
        status TEXT NOT NULL DEFAULT 'Pending',
        follow_up_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    
    # Create notifications table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Seed default notifications if empty
    cursor.execute("SELECT COUNT(*) as count FROM notifications")
    if cursor.fetchone()['count'] == 0:
        cursor.execute("INSERT INTO notifications (message, type) VALUES ('Welcome to Scholar AI. Machine Learning models are fully active.', 'info')")
        cursor.execute("INSERT INTO notifications (message, type) VALUES ('Verification Complete: Random Forest validation metrics logged.', 'success')")
    
    
    # Seed default teacher if not exists
    teacher_user = os.getenv("TEACHER_USERNAME", "admin")
    teacher_pass = os.getenv("TEACHER_PASSWORD", "admin123")
    
    cursor.execute("SELECT id FROM teachers WHERE username = ?", (teacher_user,))
    if not cursor.fetchone():
        hashed_password = generate_password_hash(teacher_pass)
        cursor.execute(
            "INSERT INTO teachers (username, password_hash) VALUES (?, ?)",
            (teacher_user, hashed_password)
        )
        print(f"Default teacher user '{teacher_user}' created.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
