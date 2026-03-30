#!/usr/bin/env python3
"""
SQLite Database for PDF Extraction Jobs
Tracks all processing jobs with full history
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import bcrypt

logger = logging.getLogger(__name__)

# Database file location
DB_PATH = Path(__file__).parent / "data" / "extraction_history.db"

# Connection timeout (seconds)
DB_TIMEOUT = 10.0


def _connect():
    """Create a database connection with proper settings."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA cache_size = -64000")
    return conn

def init_database():
    """Initialize SQLite database with tables"""

    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = _connect()
    cursor = conn.cursor()

    # Jobs table - one row per PDF processed
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            pdf_name TEXT NOT NULL,
            pdf_hash TEXT NOT NULL,
            pdf_path TEXT,
            pdf_size INTEGER,
            total_pages INTEGER,
            text_pages INTEGER,
            image_pages INTEGER,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            processing_time_seconds REAL,
            cost_usd REAL,
            accuracy_percent REAL,
            error_message TEXT
        )
    """)

    # Add pdf_path column if missing (migration for existing DBs)
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN pdf_path TEXT")
    except Exception:
        pass  # Column already exists

    # Items table - extracted data items FORMAT 1 (6 fields - linked to jobs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            item_name TEXT,
            customs_duty_rate REAL,
            quantity TEXT,
            invoice_unit_price TEXT,
            commercial_tax_percent REAL,
            exchange_rate TEXT,
            is_valid INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        )
    """)

    # Declaration table - extracted data FORMAT 2 (16 fields - linked to jobs)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS declarations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            declaration_no TEXT,
            declaration_date TEXT,
            importer_name TEXT,
            consignor_name TEXT,
            invoice_number TEXT,
            invoice_price REAL,
            currency TEXT,
            exchange_rate REAL,
            currency_2 TEXT,
            total_customs_value REAL,
            import_export_customs_duty REAL,
            commercial_tax_ct REAL,
            advance_income_tax_at REAL,
            security_fee_sf REAL,
            maccs_service_fee_mf REAL,
            exemption_reduction REAL,
            is_valid INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        )
    """)

    # Processing logs - detailed step logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processing_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            step_number INTEGER,
            step_name TEXT,
            status TEXT,
            message TEXT,
            duration_seconds REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        )
    """)

    # PDF metadata - store full PDF info
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdf_metadata (
            job_id TEXT PRIMARY KEY,
            pdf_path TEXT,
            metadata_json TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        )
    """)

    # Users table — authentication and role management
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)

    # Activity logs — tracks who did what
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Page contents — stores raw text per page for search/RAG
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS page_contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            user_id INTEGER,
            pdf_name TEXT,
            page_number INTEGER NOT NULL,
            page_type TEXT,
            source_agent TEXT,
            content TEXT,
            char_count INTEGER DEFAULT 0,
            has_tables INTEGER DEFAULT 0,
            has_numbers INTEGER DEFAULT 0,
            ocr_status TEXT,
            skip INTEGER DEFAULT 0,
            filter_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(job_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # FTS5 virtual table for full-text search on page content
    try:
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS page_contents_fts USING fts5(
                content,
                pdf_name,
                content='page_contents',
                content_rowid='id',
                tokenize='porter unicode61'
            )
        """)
    except Exception:
        pass  # FTS5 already exists or not supported

    # Add user_id to jobs (migration for existing DBs)
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN user_id INTEGER")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN username TEXT")
    except Exception:
        pass

    # Create default admin if no users exist
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        import os
        default_pw = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")
        admin_hash = bcrypt.hashpw(default_pw.encode(), bcrypt.gensalt()).decode()
        cursor.execute("""
            INSERT INTO users (username, password_hash, display_name, role)
            VALUES ('admin', ?, 'Administrator', 'admin')
        """, (admin_hash,))
        logger.info("Created default admin user")

    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_job ON items(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_declarations_job ON declarations(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_job ON processing_logs(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_logs(created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_logs(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_job ON page_contents(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_user ON page_contents(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_pdf ON page_contents(pdf_name)")

    conn.commit()
    conn.close()

    print(f"✅ Database initialized: {DB_PATH}")

def generate_job_id(pdf_name: str) -> str:
    """Generate unique job ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"JOB_{timestamp}_{pdf_name[:20].replace(' ', '_')}"

def calculate_pdf_hash(pdf_path: str) -> str:
    """Calculate SHA256 hash of PDF file for duplicate detection."""
    try:
        with open(pdf_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        logger.warning(f"PDF hash calculation failed: {e}")
        return ""

def create_job(pdf_name: str, pdf_path: str, pdf_size: int, total_pages: int,
               text_pages: int, image_pages: int, user_id: int = None, username: str = None) -> str:
    """Create a new processing job linked to a user"""

    job_id = generate_job_id(pdf_name)
    pdf_hash = calculate_pdf_hash(pdf_path)

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jobs (job_id, pdf_name, pdf_hash, pdf_path, pdf_size, total_pages,
                         text_pages, image_pages, status, user_id, username)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PROCESSING', ?, ?)
    """, (job_id, pdf_name, pdf_hash, pdf_path, pdf_size, total_pages, text_pages, image_pages, user_id, username))

    conn.commit()
    conn.close()

    print(f"✅ Created job: {job_id}")
    return job_id

def update_job_status(job_id: str, status: str, error_message: str = None):
    """Update job status"""

    conn = _connect()
    cursor = conn.cursor()

    if status == 'COMPLETED':
        cursor.execute("""
            UPDATE jobs
            SET status = ?, completed_at = CURRENT_TIMESTAMP, error_message = ?
            WHERE job_id = ?
        """, (status, error_message, job_id))
    else:
        cursor.execute("""
            UPDATE jobs
            SET status = ?, error_message = ?
            WHERE job_id = ?
        """, (status, error_message, job_id))

    conn.commit()
    conn.close()

def update_job_metrics(job_id: str, processing_time: float, cost: float, accuracy: float):
    """Update job metrics"""

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET processing_time_seconds = ?, cost_usd = ?, accuracy_percent = ?
        WHERE job_id = ?
    """, (processing_time, cost, accuracy, job_id))

    conn.commit()
    conn.close()

def save_items(job_id: str, items: List[Dict]):
    """Save extracted items to database"""

    conn = _connect()
    cursor = conn.cursor()

    for item in items:
        cursor.execute("""
            INSERT INTO items (job_id, item_name, customs_duty_rate, quantity,
                             invoice_unit_price, commercial_tax_percent, exchange_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            item.get('Item name', ''),
            item.get('Customs duty rate', 0.0),
            item.get('Quantity (1)', ''),
            item.get('Invoice unit price', ''),
            item.get('Commercial tax %', 0.0),
            item.get('Exchange Rate (1)', '')
        ))

    conn.commit()
    conn.close()

    print(f"✅ Saved {len(items)} items for job {job_id}")

def save_declarations(job_id: str, declarations: List[Dict]):
    """Save extracted declarations (Format 2) to database"""

    conn = _connect()
    cursor = conn.cursor()

    for decl in declarations:
        cursor.execute("""
            INSERT INTO declarations (
                job_id, declaration_no, declaration_date, importer_name, consignor_name,
                invoice_number, invoice_price, currency, exchange_rate, currency_2,
                total_customs_value, import_export_customs_duty, commercial_tax_ct,
                advance_income_tax_at, security_fee_sf, maccs_service_fee_mf, exemption_reduction
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            decl.get('Declaration No', ''),
            decl.get('Declaration Date', ''),
            decl.get('Importer (Name)', ''),
            decl.get('Consignor (Name)', ''),
            decl.get('Invoice Number', ''),
            decl.get('Invoice Price ', 0.0),
            decl.get('Currency', ''),
            decl.get('Exchange Rate', 0.0),
            decl.get('Currency.1', ''),
            decl.get('Total Customs Value ', 0.0),
            decl.get('Import/Export Customs Duty ', 0.0),
            decl.get('Commercial Tax (CT)', 0.0),
            decl.get('Advance Income Tax (AT)', 0.0),
            decl.get('Security Fee (SF)', 0.0),
            decl.get('MACCS Service Fee (MF)', 0.0),
            decl.get('Exemption/Reduction', 0.0)
        ))

    conn.commit()
    conn.close()

    print(f"✅ Saved {len(declarations)} declarations for job {job_id}")

def save_pdf_metadata(job_id: str, metadata: Dict):
    """Save PDF metadata JSON"""

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO pdf_metadata (job_id, pdf_path, metadata_json)
        VALUES (?, ?, ?)
    """, (job_id, metadata.get('pdf_path', ''), json.dumps(metadata)))

    conn.commit()
    conn.close()

def log_processing_step(job_id: str, step_number: int, step_name: str,
                       status: str, message: str = "", duration: float = 0.0):
    """Log a processing step"""

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO processing_logs (job_id, step_number, step_name, status, message, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (job_id, step_number, step_name, status, message, duration))

    conn.commit()
    conn.close()

def get_all_jobs(limit: int = 50) -> List[Dict]:
    """Get all jobs (most recent first)"""

    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM jobs
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))

    jobs = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jobs

def get_job_items(job_id: str) -> List[Dict]:
    """Get all items for a job"""

    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM items
        WHERE job_id = ?
        ORDER BY id
    """, (job_id,))

    items = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return items

def get_job_declarations(job_id: str) -> List[Dict]:
    """Get all declarations for a job (Format 2)"""

    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM declarations
        WHERE job_id = ?
        ORDER BY id
    """, (job_id,))

    declarations = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return declarations

def get_job_logs(job_id: str) -> List[Dict]:
    """Get processing logs for a job"""

    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM processing_logs
        WHERE job_id = ?
        ORDER BY step_number
    """, (job_id,))

    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return logs

def get_job_details(job_id: str) -> Optional[Dict]:
    """Get complete job details"""

    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get job info
    cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    job = cursor.fetchone()

    if not job:
        conn.close()
        return None

    job_dict = dict(job)

    # Get items (Format 1)
    cursor.execute("SELECT * FROM items WHERE job_id = ?", (job_id,))
    job_dict['items'] = [dict(row) for row in cursor.fetchall()]

    # Get declarations (Format 2)
    cursor.execute("SELECT * FROM declarations WHERE job_id = ?", (job_id,))
    job_dict['declarations'] = [dict(row) for row in cursor.fetchall()]

    # Get logs
    cursor.execute("SELECT * FROM processing_logs WHERE job_id = ?", (job_id,))
    job_dict['logs'] = [dict(row) for row in cursor.fetchall()]

    # Get metadata
    cursor.execute("SELECT metadata_json FROM pdf_metadata WHERE job_id = ?", (job_id,))
    metadata_row = cursor.fetchone()
    if metadata_row:
        job_dict['pdf_metadata'] = json.loads(metadata_row['metadata_json'])

    conn.close()
    return job_dict

def get_stats() -> Dict:
    """Get database statistics"""

    conn = _connect()
    cursor = conn.cursor()

    # Total jobs
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]

    # Completed jobs
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'COMPLETED'")
    completed_jobs = cursor.fetchone()[0]

    # Failed jobs
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'FAILED'")
    failed_jobs = cursor.fetchone()[0]

    # Total items extracted (Format 1)
    cursor.execute("SELECT COUNT(*) FROM items")
    total_items = cursor.fetchone()[0]

    # Total declarations extracted (Format 2)
    cursor.execute("SELECT COUNT(*) FROM declarations")
    total_declarations = cursor.fetchone()[0]

    # Average accuracy
    cursor.execute("SELECT AVG(accuracy_percent) FROM jobs WHERE status = 'COMPLETED'")
    avg_accuracy = cursor.fetchone()[0] or 0.0

    # Total cost
    cursor.execute("SELECT SUM(cost_usd) FROM jobs WHERE status = 'COMPLETED'")
    total_cost = cursor.fetchone()[0] or 0.0

    conn.close()

    return {
        'total_jobs': total_jobs,
        'completed_jobs': completed_jobs,
        'failed_jobs': failed_jobs,
        'total_items': total_items,
        'total_declarations': total_declarations,
        'avg_accuracy': avg_accuracy,
        'total_cost': total_cost
    }

def find_job_by_hash(pdf_hash: str) -> Optional[Dict]:
    """Find a completed job with the same PDF hash (duplicate detection)."""
    if not pdf_hash:
        return None

    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM jobs
        WHERE pdf_hash = ? AND status = 'COMPLETED'
        ORDER BY created_at DESC
        LIMIT 1
    """, (pdf_hash,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def delete_job(job_id: str) -> bool:
    """Delete a job and all related data."""
    conn = _connect()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM processing_logs WHERE job_id = ?", (job_id,))
        cursor.execute("DELETE FROM pdf_metadata WHERE job_id = ?", (job_id,))
        cursor.execute("DELETE FROM items WHERE job_id = ?", (job_id,))
        cursor.execute("DELETE FROM declarations WHERE job_id = ?", (job_id,))
        cursor.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


# =============================================================================
# USER MANAGEMENT
# =============================================================================

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authenticate user with bcrypt. Falls back to SHA256 for migration."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return None

    stored_hash = user['password_hash']
    authenticated = False

    # Try bcrypt first (new format)
    if stored_hash.startswith('$2'):
        try:
            authenticated = bcrypt.checkpw(password.encode(), stored_hash.encode())
        except Exception:
            authenticated = False
    else:
        # Legacy SHA256 fallback — migrate to bcrypt on success
        sha_hash = hashlib.sha256(password.encode()).hexdigest()
        if sha_hash == stored_hash:
            authenticated = True
            new_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user['id']))
            logger.info(f"Migrated user {username} password to bcrypt")

    if authenticated:
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
        conn.commit()
        user_dict = dict(user)
        conn.close()
        return user_dict

    conn.close()
    return None


def create_user(username: str, password: str, display_name: str, role: str = 'user') -> bool:
    """Create a new user. Returns True on success."""
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = _connect()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (username, password_hash, display_name, role)
            VALUES (?, ?, ?, ?)
        """, (username, password_hash, display_name, role))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_all_users() -> List[Dict]:
    """Get all users."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, display_name, role, is_active, created_at, last_login FROM users ORDER BY created_at")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def update_user(user_id: int, display_name: str = None, role: str = None, is_active: int = None, password: str = None):
    """Update user fields."""
    conn = _connect()
    cursor = conn.cursor()

    if display_name is not None:
        cursor.execute("UPDATE users SET display_name = ? WHERE id = ?", (display_name, user_id))
    if role is not None:
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    if is_active is not None:
        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id))
    if password is not None:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))

    conn.commit()
    conn.close()


def delete_user(user_id: int) -> bool:
    """Delete a user by ID."""
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# =============================================================================
# PAGE CONTENTS — RAG STORAGE
# =============================================================================

def save_page_contents(job_id: str, pdf_name: str, pages: List[Dict], user_id: int = None):
    """Save page-by-page content to database and FTS index."""
    conn = _connect()
    cursor = conn.cursor()

    for page in pages:
        content = page.get('content', '')
        has_tables = 1 if any(kw in content.lower() for kw in ['|', 'total', 'qty', 'amount', 'rate', 'price']) else 0
        has_numbers = 1 if any(c.isdigit() for c in content) else 0

        cursor.execute("""
            INSERT INTO page_contents (job_id, user_id, pdf_name, page_number, page_type,
                source_agent, content, char_count, has_tables, has_numbers,
                ocr_status, skip, filter_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, user_id, pdf_name,
            page.get('page', 0),
            page.get('type', ''),
            page.get('source', ''),
            content,
            len(content),
            has_tables, has_numbers,
            page.get('ocr_status', ''),
            1 if page.get('skip') else 0,
            page.get('filter_reason', '')
        ))

        # Update FTS index
        row_id = cursor.lastrowid
        try:
            cursor.execute("""
                INSERT INTO page_contents_fts (rowid, content, pdf_name)
                VALUES (?, ?, ?)
            """, (row_id, content, pdf_name))
        except Exception:
            pass

    conn.commit()
    conn.close()
    print(f"  Saved {len(pages)} pages for job {job_id}")


def search_page_contents(query: str, user_id: int = None, pdf_name: str = None,
                         page_type: str = None, limit: int = 100) -> List[Dict]:
    """Full-text search across page contents."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if query and query.strip():
        # FTS5 search
        fts_query = ' OR '.join(query.strip().split())
        sql = """
            SELECT pc.*, highlight(page_contents_fts, 0, '**', '**') as snippet
            FROM page_contents_fts fts
            JOIN page_contents pc ON pc.id = fts.rowid
            WHERE page_contents_fts MATCH ?
        """
        params = [fts_query]
    else:
        sql = "SELECT pc.*, '' as snippet FROM page_contents pc WHERE 1=1"
        params = []

    if user_id:
        sql += " AND pc.user_id = ?"
        params.append(user_id)
    if pdf_name and pdf_name != "All PDFs":
        sql += " AND pc.pdf_name = ?"
        params.append(pdf_name)
    if page_type and page_type != "All Types":
        sql += " AND pc.page_type = ?"
        params.append(page_type)

    sql += " ORDER BY pc.created_at DESC, pc.page_number ASC LIMIT ?"
    params.append(limit)

    try:
        cursor.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]
    except Exception:
        results = []

    conn.close()
    return results


def get_all_page_contents(user_id: int = None, pdf_name: str = None,
                          page_type: str = None, limit: int = 500) -> List[Dict]:
    """Get all page contents with optional filters."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = "SELECT * FROM page_contents WHERE skip = 0"
    params = []

    if user_id:
        sql += " AND user_id = ?"
        params.append(user_id)
    if pdf_name and pdf_name != "All PDFs":
        sql += " AND pdf_name = ?"
        params.append(pdf_name)
    if page_type and page_type != "All Types":
        sql += " AND page_type = ?"
        params.append(page_type)

    sql += " ORDER BY created_at DESC, page_number ASC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_page_content_pdfs(user_id: int = None) -> List[str]:
    """Get list of PDF names that have stored page content."""
    conn = _connect()
    cursor = conn.cursor()

    if user_id:
        cursor.execute("SELECT DISTINCT pdf_name FROM page_contents WHERE user_id = ? ORDER BY pdf_name", (user_id,))
    else:
        cursor.execute("SELECT DISTINCT pdf_name FROM page_contents ORDER BY pdf_name")

    pdfs = [row[0] for row in cursor.fetchall()]
    conn.close()
    return pdfs


def get_page_content_stats(user_id: int = None) -> Dict:
    """Get stats for stored page contents."""
    conn = _connect()
    cursor = conn.cursor()

    if user_id:
        cursor.execute("SELECT COUNT(*) FROM page_contents WHERE user_id = ?", (user_id,))
        total_pages = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT pdf_name) FROM page_contents WHERE user_id = ?", (user_id,))
        total_pdfs = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(char_count) FROM page_contents WHERE user_id = ?", (user_id,))
        total_chars = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM page_contents WHERE user_id = ? AND page_type = 'TEXT'", (user_id,))
        text_pages = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM page_contents WHERE user_id = ? AND page_type = 'IMAGE'", (user_id,))
        image_pages = cursor.fetchone()[0]
    else:
        cursor.execute("SELECT COUNT(*) FROM page_contents")
        total_pages = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT pdf_name) FROM page_contents")
        total_pdfs = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(char_count) FROM page_contents")
        total_chars = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM page_contents WHERE page_type = 'TEXT'")
        text_pages = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM page_contents WHERE page_type = 'IMAGE'")
        image_pages = cursor.fetchone()[0]

    conn.close()
    return {
        'total_pages': total_pages,
        'total_pdfs': total_pdfs,
        'total_chars': total_chars,
        'text_pages': text_pages,
        'image_pages': image_pages
    }


# =============================================================================
# ACTIVITY LOGGING
# =============================================================================

def log_activity(user_id: int, username: str, action: str, detail: str = ""):
    """Log a user activity."""
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO activity_logs (user_id, username, action, detail)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, action, detail))
    conn.commit()
    conn.close()


def get_activity_logs(limit: int = 200, user_id: int = None) -> List[Dict]:
    """Get activity logs. Optionally filter by user."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if user_id:
        cursor.execute("""
            SELECT * FROM activity_logs WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
    else:
        cursor.execute("""
            SELECT * FROM activity_logs
            ORDER BY created_at DESC LIMIT ?
        """, (limit,))

    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs


# =============================================================================
# PER-USER QUERIES
# =============================================================================

def get_user_jobs(user_id: int, limit: int = 100) -> List[Dict]:
    """Get jobs for a specific user."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM jobs WHERE user_id = ?
        ORDER BY created_at DESC LIMIT ?
    """, (user_id, limit))

    jobs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jobs


def get_user_stats(user_id: int) -> Dict:
    """Get stats for a specific user."""
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE user_id = ? AND status = 'COMPLETED'", (user_id,))
    completed = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(accuracy_percent) FROM jobs WHERE user_id = ? AND status = 'COMPLETED'", (user_id,))
    avg_acc = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(cost_usd) FROM jobs WHERE user_id = ? AND status = 'COMPLETED'", (user_id,))
    total_cost = cursor.fetchone()[0] or 0.0

    conn.close()
    return {'total_jobs': total, 'completed_jobs': completed, 'avg_accuracy': avg_acc, 'total_cost': total_cost}


if __name__ == "__main__":
    # Initialize database
    init_database()

    # Show stats
    stats = get_stats()
    print("\n📊 Database Statistics:")
    print(f"Total Jobs: {stats['total_jobs']}")
    print(f"Completed: {stats['completed_jobs']}")
    print(f"Failed: {stats['failed_jobs']}")
    print(f"Total Items (Format 1): {stats['total_items']}")
    print(f"Total Declarations (Format 2): {stats['total_declarations']}")
    print(f"Avg Accuracy: {stats['avg_accuracy']:.1f}%")
    print(f"Total Cost: ${stats['total_cost']:.4f}")
