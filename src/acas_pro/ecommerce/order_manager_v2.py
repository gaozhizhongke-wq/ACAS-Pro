"""ACAS Pro - Order Manager v2"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from ..core.config_v2 import AppConfig
from ..core.database_v2 import DatabaseManager


class OrderManager:
    """Order manager - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or AppConfig.load()
        self.db = db or DatabaseManager(self.config.database)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                total_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id TEXT PRIMARY KEY,
                order_id TEXT,
                product_id TEXT,
                quantity INTEGER DEFAULT 1,
                price REAL DEFAULT 0
            )
        """)
    
    def create_order(self, user_id: str, items: List[Dict]) -> Tuple[bool, str]:
        """Create order"""
        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Calculate total
        total = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
        
        self.db.execute("""
            INSERT INTO orders (id, user_id, total_amount, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (order_id, user_id, total, 'pending', now, now))
        
        # Add items
        for item in items:
            item_id = str(uuid.uuid4())
            self.db.execute("""
                INSERT INTO order_items (id, order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?, ?)
            """, (item_id, order_id, item.get('product_id'), item.get('quantity', 1), item.get('price', 0)))
        
        return True, order_id
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order"""
        return self.db.fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))
    
    def list_orders(self, user_id: str = None, limit: int = 100) -> List[Dict]:
        """List orders"""
        if user_id:
            return self.db.fetchall("SELECT * FROM orders WHERE user_id = ? LIMIT ?", (user_id, limit))
        return self.db.fetchall("SELECT * FROM orders LIMIT ?", (limit,))
    
    def update_status(self, order_id: str, status: str) -> Tuple[bool, str]:
        """Update order status"""
        self.db.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now(timezone.utc).isoformat(), order_id)
        )
        return True, "Updated"
