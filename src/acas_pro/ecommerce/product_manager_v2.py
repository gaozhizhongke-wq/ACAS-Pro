"""ACAS Pro - Product Manager v2"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from ..core.config_v2 import AppConfig
from ..core.database_v2 import DatabaseManager


class ProductManager:
    """Product manager - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or AppConfig.load()
        self.db = db or DatabaseManager(self.config.database)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                price REAL DEFAULT 0,
                stock INTEGER DEFAULT 0,
                category TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT
            )
        """)
    
    def create_product(self, name: str, price: float, stock: int = 0, 
                       category: str = "", description: str = "") -> Tuple[bool, str]:
        """Create product"""
        product_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        self.db.execute("""
            INSERT INTO products (id, name, description, price, stock, category, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (product_id, name, description, price, stock, category, 'active', now, now))
        
        return True, product_id
    
    def get_product(self, product_id: str) -> Optional[Dict]:
        """Get product"""
        return self.db.fetchone("SELECT * FROM products WHERE id = ?", (product_id,))
    
    def list_products(self, category: str = None, limit: int = 100) -> List[Dict]:
        """List products"""
        if category:
            return self.db.fetchall("SELECT * FROM products WHERE category = ? LIMIT ?", (category, limit))
        return self.db.fetchall("SELECT * FROM products LIMIT ?", (limit,))
    
    def update_stock(self, product_id: str, quantity: int) -> Tuple[bool, str]:
        """Update stock"""
        self.db.execute(
            "UPDATE products SET stock = stock + ?, updated_at = ? WHERE id = ?",
            (quantity, datetime.now(timezone.utc).isoformat(), product_id)
        )
        return True, "Stock updated"
    
    def delete_product(self, product_id: str) -> Tuple[bool, str]:
        """Delete product"""
        self.db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        return True, "Deleted"
