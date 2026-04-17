# Google Sheets integration
import logging
from datetime import datetime

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

GSHEET_CREDS_FILE = "service_account.json"
GSHEET_SPREADSHEET_ID = "1LDA6OIqNAp4o9gl06B1PlpyEFoxZaFx42GqOBIoYLt4"

def get_gsheet_client():
    """Initialize Google Sheets client"""
    if not GSPREAD_AVAILABLE:
        raise RuntimeError("gspread not installed. Run: pip install gspread oauth2client")
    
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GSHEET_CREDS_FILE, scope)
    return gspread.authorize(creds)

def save_order_to_gsheet(order_data: dict):
    """
    Save order to Google Sheets
    
    Order data structure:
    {
        'lang': 'ru',
        'ration': 'MEDIUM',
        'days': ['2024-11-18', '2024-11-19'],
        'customer': {
            'firstName': 'Ivan',
            'lastName': 'Ivanov',
            'phone': '+34600123456',
            'address': 'Calle Mayor, 10',
            'postcode': '28013',
            'building': '2',
            'floor': '3',
            'apartment': '5A'
        },
        'payment': {
            'method': 'cash',
            'cashBill': 100,
            'needChange': True
        },
        'total': 260.00,
        'timestamp': '2024-11-17T10:30:00'
    }
    """
    try:
        gc = get_gsheet_client()
        sh = gc.open_by_key(GSHEET_SPREADSHEET_ID)
        
        # Try to get Orders worksheet, create if doesn't exist
        try:
            worksheet = sh.worksheet("Orders")
        except:
            worksheet = sh.add_worksheet(title="Orders", rows=1000, cols=20)
            # Add header row
            worksheet.append_row([
                "Timestamp", "Customer Name", "Phone", "Address", "Postcode", 
                "Building", "Floor", "Apartment", "Ration", "Days Count", 
                "Dates", "Payment Method", "Cash Bill", "Total", "Status"
            ])
        
        # Prepare row data
        customer = order_data.get('customer', {})
        payment = order_data.get('payment', {})
        
        row = [
            order_data.get('timestamp', datetime.now().isoformat()),
            f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
            customer.get('phone', ''),
            customer.get('address', ''),
            customer.get('postcode', ''),
            customer.get('building', ''),
            customer.get('floor', ''),
            customer.get('apartment', ''),
            order_data.get('ration', ''),
            len(order_data.get('days', [])),
            ', '.join(order_data.get('days', [])),
            payment.get('method', ''),
            str(payment.get('cashBill', '')) if payment.get('needChange') else 'Exact',
            f"{order_data.get('total', 0):.2f} €",
            "New"
        ]
        
        worksheet.append_row(row)
        logging.info(f"Order saved to Google Sheets: {customer.get('firstName', '')} {customer.get('lastName', '')}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to save order to Google Sheets: {e}")
        return False

def get_orders_from_gsheet(status: str = None):
    """Get orders from Google Sheets, optionally filter by status"""
    try:
        gc = get_gsheet_client()
        sh = gc.open_by_key(GSHEET_SPREADSHEET_ID)
        worksheet = sh.worksheet("Orders")
        
        records = worksheet.get_all_records()
        
        if status:
            records = [r for r in records if r.get('Status') == status]
        
        return records
        
    except Exception as e:
        logging.error(f"Failed to get orders from Google Sheets: {e}")
        return []

def update_order_status(row_number: int, new_status: str):
    """Update order status in Google Sheets"""
    try:
        gc = get_gsheet_client()
        sh = gc.open_by_key(GSHEET_SPREADSHEET_ID)
        worksheet = sh.worksheet("Orders")
        
        # Column O (15) is Status
        worksheet.update_cell(row_number, 15, new_status)
        logging.info(f"Order status updated: row {row_number} → {new_status}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to update order status: {e}")
        return False
