from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'secretkey'

# ---------------- Database Setup ----------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    item_name TEXT,
                    category TEXT,
                    quantity INTEGER,
                    price REAL,
                    total REAL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )''')
    conn.commit()
    conn.close()

init_db()

# ---------------- Routes ----------------
@app.route('/')
def home():
    return redirect(url_for('login'))

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash('Registered Successfully! Please Login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists!', 'danger')
        conn.close()
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'danger')
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out!', 'info')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

# Add Sale
@app.route('/add-sale', methods=['GET', 'POST'])
def add_sale():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        date = request.form['date']
        item_name = request.form['item_name']
        category = request.form['category']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        total = quantity * price
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''INSERT INTO sales(user_id, date, item_name, category, quantity, price, total)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (session['user_id'], date, item_name, category, quantity, price, total))
        conn.commit()
        conn.close()
        flash('Sale added successfully!', 'success')
    return render_template('add_sale.html')

# Sales Table
@app.route('/sales')
def sales_table():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    quick_filter = request.args.get('quick_filter')
    selected_date = request.args.get('date')

    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query(f"SELECT * FROM sales WHERE user_id={user_id}", conn)
    conn.close()

    if df.empty:
        return render_template('sales_table.html', data=[])

    df['date'] = pd.to_datetime(df['date']).dt.date
    today = datetime.now().date()

    if quick_filter == "today":
        df = df[df['date'] == today]
    elif quick_filter == "week":
        start_week = today - timedelta(days=today.weekday())
        df = df[(df['date'] >= start_week) & (df['date'] <= today)]
    elif quick_filter == "month":
        start_month = today.replace(day=1)
        df = df[(df['date'] >= start_month) & (df['date'] <= today)]
    elif selected_date:
        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            df = df[df['date'] == selected_date]
        except ValueError:
            flash("Invalid date format.", "danger")

    return render_template('sales_table.html', data=df.to_dict(orient='records'))


# Analytics
@app.route('/analytics', methods=['GET'])
def analytics():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    quick_filter = request.args.get('quick_filter')

    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query(f"SELECT * FROM sales WHERE user_id={user_id}", conn)
    conn.close()

    if df.empty:
        return render_template('analytics.html', chart_html=None, total_sales=0, avg_sales=0, top_category=None, top_item=None)

    df['date'] = pd.to_datetime(df['date'])

    today = pd.to_datetime(datetime.now().date())

    # Quick filters
    if quick_filter == "today":
        start_dt = end_dt = today
    elif quick_filter == "week":
        start_dt = today - pd.Timedelta(days=today.dayofweek)
        end_dt = today
    elif quick_filter == "month":
        start_dt = today.replace(day=1)
        end_dt = today
    elif start_date and end_date:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
    else:
        start_dt = df['date'].min()
        end_dt = df['date'].max()

    # Filter data
    df_filtered = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]

    if df_filtered.empty:
        return render_template('analytics.html', chart_html=None, total_sales=0, avg_sales=0, top_category=None, top_item=None)

    # Total and Average Sales
    total_sales = df_filtered['total'].sum()
    avg_sales = df_filtered['total'].mean()

    # Top Category
    top_category = df_filtered.groupby('category')['total'].sum().idxmax()
    # Top Item
    top_item = df_filtered.groupby('item_name')['total'].sum().idxmax()

    # Plotly Chart
    fig = px.bar(df_filtered, x='date', y='total', color='category', title=f"Sales Analysis ({start_dt.date()} to {end_dt.date()})")
    chart_html = fig.to_html(full_html=False)

    return render_template('analytics.html', chart_html=chart_html, total_sales=total_sales,
                           avg_sales=avg_sales, top_category=top_category, top_item=top_item,
                           start_date=start_dt.date(), end_date=end_dt.date())

# ---------------- Sales Summary API ----------------
@app.route('/api/sales-summary')
def sales_summary():
    if 'user_id' not in session:
        return {"error": "Unauthorized"}, 401

    user_id = session['user_id']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    today = datetime.now().date().isoformat()
    yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()

    # Total sales today
    c.execute("SELECT COUNT(*) FROM sales WHERE user_id=? AND date=?", (user_id, today))
    total_sales = c.fetchone()[0]

    # Best-selling item today
    c.execute("""
        SELECT item_name, COUNT(*) as count 
        FROM sales 
        WHERE user_id=? AND date=? 
        GROUP BY item_name 
        ORDER BY count DESC 
        LIMIT 1
    """, (user_id, today))
    best_item = c.fetchone()
    best_selling = best_item[0] if best_item else "N/A"

    # Revenue today
    c.execute("SELECT SUM(total) FROM sales WHERE user_id=? AND date=?", (user_id, today))
    today_revenue = c.fetchone()[0] or 0

    # Revenue yesterday
    c.execute("SELECT SUM(total) FROM sales WHERE user_id=? AND date=?", (user_id, yesterday))
    yesterday_revenue = c.fetchone()[0] or 0

    trend = "up" if today_revenue > yesterday_revenue else "down"

    conn.close()

    return {
        "total_sales": total_sales,
        "best_selling": best_selling,
        "revenue": today_revenue,
        "trend": trend
    }

if __name__ == '__main__':
    app.run(debug=True)
