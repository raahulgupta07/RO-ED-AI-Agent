#!/usr/bin/env python3
"""
SQLite Database for PDF Extraction Jobs
Tracks all processing jobs with full history
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

# Database file location
DB_PATH = Path(__file__).parent / "data" / "extraction_history.db"

def init_database():
    """Initialize SQLite database with tables"""

    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
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

    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_job ON items(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_declarations_job ON declarations(job_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_job ON processing_logs(job_id)")

    conn.commit()
    conn.close()

    print(f"✅ Database initialized: {DB_PATH}")

def generate_job_id(pdf_name: str) -> str:
    """Generate unique job ID"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"JOB_{timestamp}_{pdf_name[:20].replace(' ', '_')}"

def calculate_pdf_hash(pdf_path: str) -> str:
    """Calculate MD5 hash of PDF file"""
    try:
        with open(pdf_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return ""

def create_job(pdf_name: str, pdf_path: str, pdf_size: int, total_pages: int,
               text_pages: int, image_pages: int) -> str:
    """Create a new processing job"""

    job_id = generate_job_id(pdf_name)
    pdf_hash = calculate_pdf_hash(pdf_path)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jobs (job_id, pdf_name, pdf_hash, pdf_path, pdf_size, total_pages,
                         text_pages, image_pages, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PROCESSING')
    """, (job_id, pdf_name, pdf_hash, pdf_path, pdf_size, total_pages, text_pages, image_pages))

    conn.commit()
    conn.close()

    print(f"✅ Created job: {job_id}")
    return job_id

def update_job_status(job_id: str, status: str, error_message: str = None):
    """Update job status"""

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO processing_logs (job_id, step_number, step_name, status, message, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (job_id, step_number, step_name, status, message, duration))

    conn.commit()
    conn.close()

def get_all_jobs(limit: int = 50) -> List[Dict]:
    """Get all jobs (most recent first)"""

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
