"""Initialize database with menu and business contacts data"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from database import (
    save_menu_item,
    save_menu_schedule,
    save_business_contact,
    get_menu_by_category,
    get_all_menu,
    get_all_business_contacts
)
from data import DISHES, BASE_MENU
from datetime import datetime

def init_menu_in_db():
    """Initialize menu items from data.py to database"""
    print("Loading menu items to database...")
    
    for dish_id, dish_info in DISHES.items():
        success = save_menu_item(
            dish_id=dish_id,
            category=dish_info['category'],
            name_ru=dish_info.get('name_ru', ''),
            name_en=dish_info.get('name_en', ''),
            name_es=dish_info.get('name_es', ''),
            kcal=dish_info.get('kcal', 0),
            protein=dish_info.get('protein', 0),
            fat=dish_info.get('fat', 0),
            carbs=dish_info.get('carbs', 0),
            is_meat=dish_info.get('is_meat', False),
            has_base=dish_info.get('has_base', False)
        )
        if success:
            print(f"✓ Dish {dish_id}: {dish_info.get('name_ru', 'Unknown')}")
        else:
            print(f"✗ Failed to save dish {dish_id}")
    
    print("\nMenu loaded successfully!")

def init_menu_schedule_in_db():
    """Initialize menu schedule from data.py to database"""
    print("\nLoading menu schedule to database...")
    
    schedule_count = 0
    for date_str, menu_dict in BASE_MENU.items():
        success = save_menu_schedule(
            date_str=date_str,
            breakfast_id=menu_dict.get('Breakfast'),
            snack1_id=menu_dict.get('Snack1'),
            lunch_id=menu_dict.get('Lunch'),
            snack2_id=menu_dict.get('Snack2'),
            dinner_id=menu_dict.get('Dinner')
        )
        if success:
            schedule_count += 1
    
    print(f"Menu schedule loaded: {schedule_count} dates")

def init_business_contacts_in_db():
    """Initialize business contact information"""
    print("\nInitializing business contacts...")
    
    contacts = [
        {
            'contact_type': 'main_phone',
            'value': '+34 600 123 456',
            'description': 'Main business phone'
        },
        {
            'contact_type': 'email',
            'value': 'info@business.com',
            'description': 'Business email'
        },
        {
            'contact_type': 'address',
            'value': 'Calle Mayor, 10, 28013, Madrid',
            'description': 'Business address'
        },
        {
            'contact_type': 'instagram',
            'value': '@business_handle',
            'description': 'Instagram account'
        },
        {
            'contact_type': 'delivery_hours',
            'value': '08:00-20:00',
            'description': 'Delivery hours'
        },
        {
            'contact_type': 'website',
            'value': 'https://www.business.com',
            'description': 'Business website'
        }
    ]
    
    for contact in contacts:
        success = save_business_contact(
            contact_type=contact['contact_type'],
            value=contact['value'],
            description=contact['description']
        )
        if success:
            print(f"✓ {contact['contact_type']}: {contact['value']}")
        else:
            print(f"✗ Failed to save {contact['contact_type']}")
    
    print("Business contacts initialized!")

def verify_db():
    """Verify that data was loaded correctly"""
    print("\n" + "="*50)
    print("DATABASE VERIFICATION")
    print("="*50)
    
    print("\nMenu by category:")
    menu = get_all_menu()
    for category, items in menu.items():
        print(f"  {category}: {len(items)} items")
    
    print("\nBusiness contacts:")
    contacts = get_all_business_contacts()
    for contact_type, info in contacts.items():
        print(f"  {contact_type}: {info.get('value', 'N/A')}")

if __name__ == "__main__":
    print("Starting database initialization...\n")
    init_menu_in_db()
    init_menu_schedule_in_db()
    init_business_contacts_in_db()
    verify_db()
    print("\n✓ Database initialization complete!")
