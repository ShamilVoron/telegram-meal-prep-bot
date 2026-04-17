# SQLite database for orders, menu, and contacts in one database
import sqlite3
import json
from datetime import datetime

DB_FILE = 'orders.db'

def init_db():
    """Initialize database with all tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Table for menu (dishes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY,
            category TEXT NOT NULL,
            name_ru TEXT,
            name_en TEXT,
            name_es TEXT,
            kcal INTEGER,
            protein REAL,
            fat REAL,
            carbs REAL,
            is_meat BOOLEAN DEFAULT 0,
            has_base BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table for menu schedule (what's available each day)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            breakfast INTEGER,
            snack1 INTEGER,
            lunch INTEGER,
            snack2 INTEGER,
            dinner INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (breakfast) REFERENCES menu(id),
            FOREIGN KEY (snack1) REFERENCES menu(id),
            FOREIGN KEY (lunch) REFERENCES menu(id),
            FOREIGN KEY (snack2) REFERENCES menu(id),
            FOREIGN KEY (dinner) REFERENCES menu(id)
        )
    """)
    
    # Table for orders
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            customer_name TEXT,
            phone TEXT,
            address TEXT,
            postcode TEXT,
            building TEXT,
            floor TEXT,
            apartment TEXT,
            ration TEXT,
            days_count INTEGER,
            dates TEXT,
            payment_method TEXT,
            cash_bill TEXT,
            total REAL,
            status TEXT DEFAULT 'New',
            manager_notified INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    
    # Table for user contact information (cached from chat mode)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_contacts (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            address TEXT,
            postcode TEXT,
            entrance TEXT,
            floor TEXT,
            apartment TEXT,
            comment TEXT,
            updated_at TEXT
        )
    """)
    
    # Table for additional rations per user
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_rations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ration TEXT,
            added_at TEXT,
            UNIQUE(user_id, ration)
        )
    """)
    
    # Table for business contact information
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_contacts (
            id INTEGER PRIMARY KEY,
            contact_type TEXT UNIQUE,
            value TEXT,
            description TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table for manager chat IDs (auto-registered)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS managers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE NOT NULL,
            manager_name TEXT,
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# ==================== MENU FUNCTIONS ====================

def save_menu_item(dish_id: int, category: str, name_ru: str, name_en: str = "", 
                   name_es: str = "", kcal: int = 0, protein: float = 0, 
                   fat: float = 0, carbs: float = 0, is_meat: bool = False, 
                   has_base: bool = False):
    """Save or update menu item"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO menu (
                id, category, name_ru, name_en, name_es, kcal, protein, fat, carbs, 
                is_meat, has_base, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (dish_id, category, name_ru, name_en, name_es, kcal, protein, fat, carbs, 
              is_meat, has_base, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database error saving menu item: {e}")
        return False

def get_menu_item(dish_id: int):
    """Get menu item by ID"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM menu WHERE id = ?", (dish_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    except Exception as e:
        print(f"Database error: {e}")
        return None

def get_menu_by_category(category: str):
    """Get all menu items in category"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM menu WHERE category = ? ORDER BY id", (category,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Database error: {e}")
        return []

def get_all_menu():
    """Get all menu items grouped by category"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM menu ORDER BY category, id")
        rows = cursor.fetchall()
        conn.close()
        
        menu_dict = {}
        for row in rows:
            cat = row['category']
            if cat not in menu_dict:
                menu_dict[cat] = []
            menu_dict[cat].append(dict(row))
        
        return menu_dict
    except Exception as e:
        print(f"Database error: {e}")
        return {}

def save_menu_schedule(date_str: str, breakfast_id: int, snack1_id: int, 
                       lunch_id: int, snack2_id: int, dinner_id: int):
    """Save menu schedule for a specific date"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO menu_schedule (date, breakfast, snack1, lunch, snack2, dinner)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date_str, breakfast_id, snack1_id, lunch_id, snack2_id, dinner_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database error saving schedule: {e}")
        return False

def get_menu_schedule(date_str: str):
    """Get menu schedule for a specific date"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM menu_schedule WHERE date = ?", (date_str,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    except Exception as e:
        print(f"Database error: {e}")
        return None

# ==================== ORDER FUNCTIONS ====================

def save_order(order_data: dict):
    """Save order to SQLite database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        customer = order_data.get('customer', {})
        payment = order_data.get('payment', {})
        days = order_data.get('days', [])
        
        cursor.execute("""
            INSERT INTO orders (
                timestamp, customer_name, phone, address, postcode, 
                building, floor, apartment, ration, days_count, 
                dates, payment_method, cash_bill, total, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_data.get('timestamp', datetime.now().isoformat()),
            f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
            customer.get('phone', ''),
            customer.get('address', ''),
            customer.get('postcode', ''),
            customer.get('building', ''),
            customer.get('floor', ''),
            customer.get('apartment', ''),
            order_data.get('ration', ''),
            len(days),
            ', '.join(days),
            payment.get('method', ''),
            str(payment.get('cashBill', '')) if payment.get('needChange') else 'Exact',
            order_data.get('total', 0),
            'New',
            datetime.now().isoformat()
        ))
        
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return order_id
        
    except Exception as e:
        print(f"Database error: {e}")
        return None

def get_new_orders():
    """Get orders with status 'New'"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM orders WHERE status = 'New' ORDER BY id DESC")
        rows = cursor.fetchall()
        
        orders = [dict(row) for row in rows]
        conn.close()
        
        return orders
    except Exception as e:
        print(f"Database error: {e}")
        return []

def get_all_orders():
    """Get all orders"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM orders ORDER BY id DESC")
        rows = cursor.fetchall()
        
        orders = [dict(row) for row in rows]
        conn.close()
        
        return orders
    except Exception as e:
        print(f"Database error: {e}")
        return []

def get_order_by_id(order_id: int):
    """Get specific order by ID"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    except Exception as e:
        print(f"Database error: {e}")
        return None

def update_order_status_db(order_id: int, new_status: str):
    """Update order status"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def mark_order_notified(order_id: int):
    """Mark that notification was sent to manager"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE orders SET manager_notified = 1 WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def get_unnotified_orders():
    """Get orders that haven't been notified to manager yet"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM orders WHERE status = 'New' AND manager_notified = 0 ORDER BY id DESC"
        )
        rows = cursor.fetchall()
        
        orders = [dict(row) for row in rows]
        conn.close()
        
        return orders
    except Exception as e:
        print(f"Database error: {e}")
        return []

# ==================== USER CONTACT FUNCTIONS ====================

def save_user_contact(user_id: int, contact_info: dict):
    """Save or update user contact information"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_contacts (
                user_id, first_name, last_name, phone, address, 
                postcode, entrance, floor, apartment, comment, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            contact_info.get('firstName', ''),
            contact_info.get('lastName', ''),
            contact_info.get('phone', ''),
            contact_info.get('address', ''),
            contact_info.get('postcode', ''),
            contact_info.get('entrance', ''),
            contact_info.get('floor', ''),
            contact_info.get('apartment', ''),
            contact_info.get('comment', ''),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database error saving contact: {e}")
        return False

def get_user_contact(user_id: int):
    """Get saved contact information for user"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_contacts WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'firstName': row['first_name'],
                'lastName': row['last_name'],
                'phone': row['phone'],
                'address': row['address'],
                'postcode': row['postcode'],
                'entrance': row['entrance'],
                'floor': row['floor'],
                'apartment': row['apartment'],
                'comment': row['comment']
            }
        return None
    except Exception as e:
        print(f"Database error loading contact: {e}")
        return None

def get_all_user_contacts():
    """Get all user contacts"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_contacts ORDER BY user_id")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Database error: {e}")
        return []

def save_additional_ration(user_id: int, ration: str):
    """Save additional ration to user profile"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO user_rations (user_id, ration, added_at)
            VALUES (?, ?, ?)
        """, (user_id, ration, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database error saving ration: {e}")
        return False

def get_user_rations(user_id: int) -> list:
    """Get all additional rations for user"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT ration FROM user_rations WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    except Exception as e:
        print(f"Database error loading rations: {e}")
        return []

# ==================== BUSINESS CONTACT FUNCTIONS ====================

def save_business_contact(contact_type: str, value: str, description: str = ""):
    """Save or update business contact information (phone, email, address, etc.)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO business_contacts (contact_type, value, description, updated_at)
            VALUES (?, ?, ?, ?)
        """, (contact_type, value, description, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database error saving business contact: {e}")
        return False

def get_business_contact(contact_type: str):
    """Get business contact by type"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM business_contacts WHERE contact_type = ?", (contact_type,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    except Exception as e:
        print(f"Database error: {e}")
        return None

def get_all_business_contacts():
    """Get all business contacts"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM business_contacts ORDER BY contact_type")
        rows = cursor.fetchall()
        conn.close()
        
        return {row['contact_type']: dict(row) for row in rows}
    except Exception as e:
        print(f"Database error: {e}")
        return {}

# ==================== MANAGER FUNCTIONS ====================

def register_manager(chat_id: int, manager_name: str = None):
    """Register manager chat ID when they send /start"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO managers (chat_id, manager_name)
            VALUES (?, ?)
        """, (chat_id, manager_name))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database error registering manager: {e}")
        return False

def get_all_managers():
    """Get all registered manager chat IDs"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT chat_id FROM managers ORDER BY registered_at")
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    except Exception as e:
        print(f"Database error getting managers: {e}")
        return []

def unregister_manager(chat_id: int):
    """Unregister manager"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM managers WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database error unregistering manager: {e}")
        return False

# Initialize on import
init_db()
