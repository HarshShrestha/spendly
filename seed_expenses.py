import sqlite3
import random
from datetime import datetime, timedelta
from database.db import get_db

def seed_expenses(user_id, count, months):
    conn = get_db()
    try:
        user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            print(f"No user found with id {user_id}.")
            return

        categories = {
            "Food": {"range": (50, 800), "weight": 30, "desc": ["Dinner at Taj", "Lunch with colleagues", "Street Food", "Grocery store", "Coffee and snacks"]},
            "Transport": {"range": (20, 500), "weight": 20, "desc": ["Uber Ride", "Auto Rickshaw", "Petrol Fill", "Metro Card Topup", "Parking Fee"]},
            "Bills": {"range": (200, 3000), "weight": 15, "desc": ["Electricity Bill", "Water Bill", "Internet Broadband", "Mobile Recharge", "Rent Payment"]},
            "Health": {"range": (100, 2000), "weight": 5, "desc": ["Pharmacy", "Doctor Consultation", "Lab Tests", "Health Insurance", "Vitamin Supplements"]},
            "Entertainment": {"range": (100, 1500), "weight": 10, "desc": ["Cinema Ticket", "Gaming Subscription", "Bowling", "Concert", "Book Store"]},
            "Shopping": {"range": (200, 5000), "weight": 15, "desc": ["New Shirt", "Shoes", "Electronics", "Gift for Friend", "Home Decor"]},
            "Other": {"range": (50, 1000), "weight": 5, "desc": ["Miscellaneous", "Donation", "Service Charge", "Stationery", "Laundry"]},
        }

        cat_names = list(categories.keys())
        weights = [categories[cat]["weight"] for cat in cat_names]

        expenses = []
        now = datetime.now()
        start_date = now - timedelta(days=months * 30)
        
        for _ in range(count):
            cat = random.choices(cat_names, weights=weights)[0]
            amount = round(random.uniform(*categories[cat]["range"]), 2)
            description = random.choice(categories[cat]["desc"])
            days_offset = random.randint(0, months * 30)
            date_obj = start_date + timedelta(days=days_offset)
            date_str = date_obj.strftime('%Y-%m-%d')
            expenses.append((user_id, amount, cat, date_str, description))

        with conn:
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                expenses
            )
        
        print(f"Successfully inserted {count} expenses.")
        dates = [e[3] for e in expenses]
        print(f"Date range: {min(dates)} to {max(dates)}")
        
        print("\nSample of 5 inserted records:")
        sample = random.sample(expenses, min(5, count))
        for e in sample:
            print(f"Date: {e[3]} | Cat: {e[2]} | Amt: ₹{e[1]} | Desc: {e[4]}")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        sys.exit(1)
    
    try:
        uid = int(sys.argv[1])
        cnt = int(sys.argv[2])
        mths = int(sys.argv[3])
        seed_expenses(uid, cnt, mths)
    except ValueError:
        pass
