# Run this script once to create app.db and populate sample menu items.
import sqlite3, os
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "gaurirestro" / "app.db"
DB.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

# Create tables
cur.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    price REAL,
    image TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    item_id INTEGER,
    qty INTEGER,
    price REAL
)""")




# Insert sample items if empty
cur.execute("SELECT COUNT(*) FROM items")
if cur.fetchone()[0] == 0:
    sample = [
        ('Chicken Biryani','Delicious chicken biryani',150,'static/images/chickenbiryani.jpg'),
        ('Paneer Frankie','Tasty paneer frankie',120,'static/images/paneerfrankie.jpg'),
        ('White Pasta','Creamy white pasta',140,'static/images/whitepasta.jpg'),
        ('Oreo Shake','Chocolate oreo shake',90,'static/images/oreoshake.jpg'),
        ('pizza pasta','Fusion of cheesy pizza and creamy pasta',239,'\static\images\pizzapasta.jpg')
    ]
    cur.executemany("INSERT INTO items (name,description,price,image) VALUES (?,?,?,?)", sample)
conn.commit()
conn.close()
print('Database created at', DB)


