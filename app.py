from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify
import sqlite3
import bcrypt
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"

# --- Automatic DB & admin initialization ---
def init_db_and_admin():
    db_file = DB_PATH
    need_seed = not Path(db_file).exists()
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()

    # --- Core tables ---
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
        items TEXT,
        total REAL,
        name TEXT,
        contact TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        item_id INTEGER,
        qty INTEGER,
        price REAL
    )""")

    # --- New tables for feedback & queries ---
    cur.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # --- Seed admin user ---
    try:
        cur.execute("SELECT id FROM users WHERE username = ?", ('admin',))
        if not cur.fetchone():
            pw = 'admin123'
            hashed = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute("INSERT INTO users (username, password) VALUES (?,?)", ('admin', hashed))
    except Exception as e:
        print('Error ensuring admin user:', e)

    # --- Seed items if empty ---
    cur.execute("SELECT COUNT(*) FROM items")
    if cur.fetchone()[0] == 0:
        sample = [
            ('Chicken Biryani', 'Delicious chicken biryani', 150, 'static/images/chickenbiryani.jpg'),
            ('Paneer Frankie', 'Tasty paneer frankie', 120, 'static/images/paneerfrankie.jpg'),
            ('White Pasta', 'Creamy white pasta', 140, 'static/images/whitepasta.jpg'),
            ('Oreo Shake', 'Chocolate oreo shake', 90, 'static/images/oreoshake.jpg'),
        ]
        cur.executemany("INSERT INTO items (name, description, price, image) VALUES (?,?,?,?)", sample)

    conn.commit()
    conn.close()


# --- Call initialization on startup ---
init_db_and_admin()

# --- Flask setup ---
app = Flask(__name__, static_folder=str(BASE_DIR / "static"), template_folder=str(BASE_DIR / "templates"))
app.secret_key = "replace_this_with_a_random_secret"


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(str(DB_PATH))
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


# --- Main Routes ---
@app.route("/")
def index():
    return render_template("index.html")


# Serve static-like pages
pages = ["index.html", "login.html", "signup.html", "menu123.html", "cart.html", "checkout.html", "payment.html",
         "order-success.html", "my-orders.html", "track-order.html", "admin.html"]
for p in pages:
    route = "/" + p

    def _make_route(p):
        def route_func():
            return render_template(p)
        route_func.__name__ = "page_" + p.replace(".", "_")
        return route_func

    app.add_url_rule(route, endpoint=route, view_func=_make_route(p), methods=["GET", "POST"])


# --- Authentication APIs ---
@app.route("/api/signup", methods=["POST"])
def api_signup():
    data = request.form or request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    db = get_db()
    cur = db.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cur.fetchone():
        return jsonify({"error": "user exists"}), 400
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    db.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, hashed.decode('utf-8')))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.form or request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    db = get_db()
    cur = db.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "invalid credentials"}), 401
    stored = row["password"]
    try:
        ok = bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
    except Exception:
        ok = False
    if not ok:
        return jsonify({"error": "invalid credentials"}), 401
    session["user_id"] = row["id"]
    return jsonify({"ok": True})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("user_id", None)
    return jsonify({"ok": True})


# --- Menu API ---
@app.route("/api/menu", methods=["GET"])
def api_menu():
    db = get_db()
    cur = db.execute("SELECT * FROM items")
    items = [dict(r) for r in cur.fetchall()]
    return jsonify(items)


# --- Order APIs ---
@app.route("/api/create_order", methods=["POST"])
def api_create_order():
    data = request.get_json(silent=True) or request.form or {}
    try:
        if isinstance(data, dict) and isinstance(data.get('items'), str):
            data['items'] = json.loads(data['items'])
    except Exception:
        pass
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "login required"}), 401
    items = data.get("items") or []
    if not items:
        return jsonify({"error": "no items"}), 400
    db = get_db()
    cur = db.execute("INSERT INTO orders (user_id, status) VALUES (?,?)", (user_id, "created"))
    order_id = cur.lastrowid
    for it in items:
        db.execute("INSERT INTO order_items (order_id, item_id, qty, price) VALUES (?,?,?,?)",
                   (order_id, it.get("id"), it.get("qty", 1), it.get("price", 0)))
    db.commit()
    return jsonify({"ok": True, "order_id": order_id})


@app.route("/api/my_orders", methods=["GET"])
def api_my_orders():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "login required"}), 401
    db = get_db()
    cur = db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    orders = [dict(r) for r in cur.fetchall()]
    return jsonify(orders)


# --- Admin ---
@app.route("/admin.html")
def admin_page():
    if session.get("user_id") is None:
        return redirect(url_for('page_index_html'))
    db = get_db()
    cur = db.execute("SELECT username FROM users WHERE id = ?", (session.get('user_id'),))
    row = cur.fetchone()
    if not row or row["username"] != "admin":
        return redirect(url_for('page_index_html'))
    return render_template("admin.html")


@app.route("/api/admin/orders", methods=["GET"])
def api_admin_orders():
    db = get_db()
    cur = db.execute("SELECT username FROM users WHERE id = ?", (session.get('user_id'),))
    r = cur.fetchone()
    if not r or r["username"] != "admin":
        return jsonify({"error": "forbidden"}), 403
    cur = db.execute("""SELECT o.id,o.user_id,o.status,o.items,o.total,o.name,o.contact,
                     o.created_at,u.username FROM orders o 
                     LEFT JOIN users u ON o.user_id = u.id 
                     ORDER BY o.created_at DESC""")
    orders = [dict(row) for row in cur.fetchall()]
    return jsonify(orders)


@app.route("/api/admin/customers", methods=["GET"])
def api_admin_customers():
    db = get_db()
    cur = db.execute("SELECT username,id FROM users ORDER BY id DESC")
    users = [dict(r) for r in cur.fetchall()]
    return jsonify(users)


@app.route("/api/admin/order/<int:order_id>/update", methods=["POST"])
def api_admin_update_order(order_id):
    db = get_db()
    cur = db.execute("SELECT username FROM users WHERE id = ?", (session.get('user_id'),))
    r = cur.fetchone()
    if not r or r["username"] != "admin":
        return jsonify({"error": "forbidden"}), 403
    data = request.get_json(silent=True) or request.form or {}
    status = data.get("status")
    if status not in ("created", "cancelled", "delivered"):
        return jsonify({"error": "invalid status"}), 400
    db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    db.commit()
    return jsonify({"ok": True})


# --- FEEDBACK STORE ---
@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    name = request.form.get('name')
    message = request.form.get('message')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO feedback (name, message) VALUES (?, ?)", (name, message))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "msg": "Feedback stored"})


# --- QUERY STORE ---
@app.route('/submit_query', methods=['POST'])
def submit_query():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO queries (name, email, message) VALUES (?, ?, ?)", (name, email, message))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "msg": "Query stored"})
@app.route("/admin/feedbacks")
def admin_feedbacks():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM feedback ORDER BY date DESC")
    data = c.fetchall()
    conn.close()
    return render_template("admin_feedbacks.html", feedbacks=data)


@app.route("/admin/queries")
def admin_queries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM queries ORDER BY date DESC")
    data = c.fetchall()
    conn.close()
    return render_template("admin_queries.html", queries=data)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
