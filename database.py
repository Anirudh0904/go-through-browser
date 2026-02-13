import sqlite3
import time
import os
import sys

def get_database_path():
    """Get database path - robust for both development and bundled"""
    if getattr(sys, 'frozen', False):
        # Running as bundled executable - use exe directory
        base_path = os.path.dirname(sys.executable)
    else:
        # Running as script - use current working directory
        base_path = os.getcwd()
    
    return os.path.join(base_path, 'browser_data.db')

class BrowserDatabase:
    def __init__(self, db_name=None):
        if db_name is None:
            self.db_path = get_database_path()
        else:
            self.db_path = db_name
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.conn.commit()

    def create_tables(self):
        """Create all database tables"""
        # History table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                timestamp REAL,
                visit_count INTEGER DEFAULT 1
            )
        """)
        
        # Bookmarks table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                created_at REAL
            )
        """)
        
        # MIGRATION: Add created_at column if it doesn't exist
        try:
            self.cursor.execute("ALTER TABLE bookmarks ADD COLUMN created_at REAL")
            print("✅ Added created_at column to bookmarks table")
        except sqlite3.OperationalError:
            print("✅ created_at column already exists")
        
        self.conn.commit()
        
        # Downloads table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                downloaded_at REAL,
                size_bytes INTEGER
            )
        """)
        
        # Settings table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        self.conn.commit()

    def add_history_entry(self, url, title):
        """Add or update history entry"""
        timestamp = time.time()
        # Check if URL already exists
        self.cursor.execute("SELECT visit_count FROM history WHERE url = ?", (url,))
        result = self.cursor.fetchone()
        
        if result:
            # Update existing entry
            new_count = result[0] + 1
            self.cursor.execute("""
                UPDATE history 
                SET title = ?, timestamp = ?, visit_count = ? 
                WHERE url = ?
            """, (title, timestamp, new_count, url))
        else:
            # Add new entry
            self.cursor.execute("""
                INSERT INTO history (url, title, timestamp, visit_count) 
                VALUES (?, ?, ?, ?)
            """, (url, title, timestamp, 1))
        
        self.conn.commit()

    def get_history(self, limit=50):
        """Get recent history"""
        self.cursor.execute("""
            SELECT url, title, timestamp 
            FROM history 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()
    
    def search_history(self, query, limit=50):
        """Search history by query"""
        self.cursor.execute("""
            SELECT url, title, timestamp 
            FROM history 
            WHERE LOWER(title) LIKE ? OR LOWER(url) LIKE ?
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (f'%{query.lower()}%', f'%{query.lower()}%', limit))
        return self.cursor.fetchall()

    def add_bookmark(self, url, title):
        """Add bookmark (ignores duplicates)"""
        try:
            self.cursor.execute("""
                INSERT INTO bookmarks (url, title, created_at) 
                VALUES (?, ?, ?)
            """, (url, title, time.time()))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_bookmarks(self):
        """Get all bookmarks"""
        self.cursor.execute("SELECT url, title FROM bookmarks ORDER BY title ASC")
        return self.cursor.fetchall()
    
    def search_bookmarks(self, query):
        """Search bookmarks by query"""
        self.cursor.execute("""
            SELECT url, title 
            FROM bookmarks 
            WHERE LOWER(title) LIKE ? OR LOWER(url) LIKE ?
            ORDER BY title ASC
        """, (f'%{query.lower()}%', f'%{query.lower()}%'))
        return self.cursor.fetchall()
    
    def update_bookmark(self, url, new_title):
        """Update bookmark title"""
        self.cursor.execute("UPDATE bookmarks SET title = ? WHERE url = ?", (new_title, url))
        self.conn.commit()
    
    def delete_bookmark(self, url):
        """Delete bookmark by URL"""
        self.cursor.execute("DELETE FROM bookmarks WHERE url = ?", (url,))
        self.conn.commit()
    
    def remove_bookmark(self, url):
        """Remove bookmark by URL (alias for delete_bookmark)"""
        self.delete_bookmark(url)

    def get_bookmark_count(self):
        """Get bookmark count"""
        self.cursor.execute("SELECT COUNT(*) FROM bookmarks")
        return self.cursor.fetchone()[0]

    def clear_history(self):
        """Clear all history"""
        self.cursor.execute("DELETE FROM history")
        self.conn.commit()

    def clear_all_data(self):
        """Nuclear option - clear everything"""
        self.cursor.execute("DELETE FROM history")
        self.cursor.execute("DELETE FROM bookmarks")
        self.cursor.execute("DELETE FROM downloads")
        self.conn.commit()

    def get_suggestions(self, text):
        """Get URL suggestions for autocomplete"""
        pattern = f"%{text}%"
        self.cursor.execute("SELECT url, title FROM history WHERE url LIKE ? OR title LIKE ? ORDER BY timestamp DESC LIMIT 5", (pattern, pattern))
        return self.cursor.fetchall()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
