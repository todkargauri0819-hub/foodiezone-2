README - Modified gaurirestro project
------------------------------------
What's included:
- The original UI/UX files are unchanged (templates and static assets).
- Added a Flask backend scaffold (app.py) at project root of the package.
- Added a database init script (db_init.py) to create SQLite DB and seed sample items.
- requirements.txt with Flask.

Instructions to run:
1. Extract the zip and in project folder run:
   python3 -m venv venv
   source venv/bin/activate   # on Windows use venv\Scripts\activate
   pip install -r requirements.txt
2. Initialize database:
   python3 db_init.py
3. Run the app:
   python3 app.py
4. Open http://127.0.0.1:5000/index.html

Notes:
- Templates and static files were NOT modified to preserve UI/UX.
- API endpoints available under /api/* (signup, login, menu, create_order, my_orders).
- The secret key in app.py should be replaced for production.
