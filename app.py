from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets
import re
from datetime import datetime, timedelta
from collections import defaultdict

# ---------- Config ----------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'frontend', 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# Load config from env (with sensible defaults)
def env(name, default=""):
    return os.environ.get(name, default)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # Update if different
app.config['MYSQL_PASSWORD'] = '#20Sufi04'  # Update with your real password
app.config['MYSQL_DB'] = 'finflow_db'

secret = env('FLASK_SECRET')
app.secret_key = secret if secret else secrets.token_hex(24)

PORT = int(env('PORT', '5002'))

mysql = MySQL(app)

# ---------- Helpers ----------
def get_user():
    if 'user_id' in session:
        return {'id': session['user_id'], 'first_name': session.get('first_name')}
    return None

def fetchone_val(cur):
    row = cur.fetchone()
    return (row[0] if row and row[0] is not None else 0)

def month_bounds(dt):
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if dt.month == 12:
        next_start = dt.replace(year=dt.year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_start = dt.replace(month=dt.month+1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end = next_start - timedelta(seconds=1)
    return start, end

def last_month_bounds():
    today = datetime.now()
    first_this = today.replace(day=1)
    last_month_end = first_this - timedelta(seconds=1)
    last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return last_month_start, last_month_end

def simple_monthly_forecast(user_id):
    """
    Predict next month's total expense as the average of last 3 months' totals.
    Lightweight and dependency-free.
    """
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT DATE_FORMAT(transaction_date, '%%Y-%%m') ym,
               SUM(CASE WHEN category='Expense' THEN amount ELSE 0 END) AS total_expense
        FROM transactions
        WHERE user_id=%s
        GROUP BY ym
        ORDER BY ym DESC
        LIMIT 3
    """, [user_id])
    rows = cur.fetchall()
    if not rows:
        return 0.0
    totals = [float(r[1] or 0) for r in rows]
    return round(sum(totals)/len(totals), 2)

def detect_recurring(user_id, min_count=3):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT description,
               COUNT(*) AS c,
               AVG(amount) AS avg_amt,
               MAX(transaction_date) AS last_dt
        FROM transactions
        WHERE user_id=%s AND category='Expense'
        GROUP BY description
        HAVING c >= %s
        ORDER BY c DESC, last_dt DESC
        LIMIT 20
    """, [user_id, min_count])
    res = []
    for desc, c, avg_amt, last_dt in cur.fetchall():
        next_eta = (last_dt or datetime.now()) + timedelta(days=30)
        res.append({
            'description': desc,
            'count': int(c),
            'avg_amount': float(avg_amt or 0),
            'last_date': last_dt,
            'next_eta': next_eta
        })
    return res

def estimate_next_salary_date(user_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT MAX(transaction_date) FROM transactions
        WHERE user_id=%s AND category='Income' AND (description LIKE '%%Salary%%' OR description LIKE '%%salary%%')
    """, [user_id])
    last_salary = cur.fetchone()[0]
    if last_salary:
        return last_salary + timedelta(days=30)
    today = datetime.now()
    if today.month == 12:
        return today.replace(year=today.year+1, month=1, day=1)
    return today.replace(month=today.month+1, day=1)

def cash_flow_warning(user_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
          SUM(CASE WHEN category='Income' THEN amount ELSE 0 END) -
          SUM(CASE WHEN category='Expense' THEN amount ELSE 0 END)
        FROM transactions WHERE user_id=%s
    """, [user_id])
    net_balance = float(fetchone_val(cur))

    cur.execute("""
        SELECT DATE(transaction_date) d,
               SUM(CASE WHEN category='Income' THEN amount ELSE -amount END) AS net
        FROM transactions
        WHERE user_id=%s AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
        GROUP BY d
    """, [user_id])
    rows = cur.fetchall()
    if rows:
        avg_daily_net = sum(float(r[1]) for r in rows) / len(rows)
    else:
        avg_daily_net = 0.0

    next_salary = estimate_next_salary_date(user_id)
    days_until = max(0, (next_salary.date() - datetime.now().date()).days)

    projected = net_balance + avg_daily_net * days_until
    will_go_negative = projected < 0
    return {
        'net_balance': round(net_balance,2),
        'avg_daily_net': round(avg_daily_net,2),
        'days_until_salary': days_until,
        'projected_balance': round(projected,2),
        'warning': will_go_negative,
        'next_salary_eta': next_salary
    }

# ---------- Routes ----------
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute('SELECT id, first_name, last_name, email, password FROM users WHERE email=%s', [email])
        user = cur.fetchone()
        if user and check_password_hash(user[4], password):
            session['user_id'] = user[0]
            session['first_name'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials.', 'danger')
    return render_template('auth.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first-name']
        last_name = request.form['last-name']
        email = request.form['email']
        password = request.form['password']
        occupation = request.form.get('occupation','')

        cur = mysql.connection.cursor()
        cur.execute('SELECT id FROM users WHERE email=%s', [email])
        if cur.fetchone():
            flash('Email already exists', 'danger')
            return render_template('auth.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters', 'danger')
            return render_template('auth.html')

        hpw = generate_password_hash(password)
        cur.execute("""
            INSERT INTO users(first_name, last_name, email, password, occupation)
            VALUES (%s,%s,%s,%s,%s)
        """, [first_name, last_name, email, hpw, occupation])
        mysql.connection.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('auth.html')

@app.route('/dashboard')
def index():
    user = get_user()
    if not user:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, description, amount, category, subcategory, transaction_date
        FROM transactions WHERE user_id=%s
        ORDER BY transaction_date DESC LIMIT 5
    """, [user['id']])
    transactions = cur.fetchall()

    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=%s AND category='Income'", [user['id']])
    total_income = float(fetchone_val(cur))

    cur.execute("SELECT SUM(amount) FROM transactions WHERE user_id=%s AND category='Expense'", [user['id']])
    total_expenses = float(fetchone_val(cur))

    net_balance = total_income - total_expenses

    recurring = detect_recurring(user['id'])
    cf = cash_flow_warning(user['id'])

    advice_msgs = []
    if total_income > 0 and total_expenses > 0.8 * total_income:
        advice_msgs.append("You're spending more than 80% of your income. Consider tightening variable expenses.")
    if cf['warning']:
        advice_msgs.append("Cash flow risk: you may go negative before the next salary credit.")

    return render_template('index.html',
                           first_name=user['first_name'],
                           transactions=transactions,
                           total_income=round(total_income,2),
                           total_expenses=round(total_expenses,2),
                           net_balance=round(net_balance,2),
                           recurring=recurring,
                           cashflow=cf,
                           advice_msgs=advice_msgs)

@app.route('/all-transactions')
def all_transactions():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, description, amount, category, subcategory, transaction_date
        FROM transactions WHERE user_id=%s ORDER BY transaction_date DESC
    """, [user['id']])
    transactions = cur.fetchall()
    return render_template('all_transactions.html', transactions=transactions)

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    description = request.form['description']
    amount = request.form['amount']
    category = request.form['category']
    subcategory = request.form.get('subcategory') if category == 'Expense' else None
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO transactions (user_id, description, amount, category, subcategory, transaction_date)
        VALUES (%s,%s,%s,%s,%s,NOW())
    """, [user['id'], description, amount, category, subcategory])
    mysql.connection.commit()
    flash('Transaction added!', 'success')
    return redirect(url_for('index'))

@app.route('/analytics')
def analytics():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT category, SUM(amount)
        FROM transactions WHERE user_id=%s GROUP BY category
    """, [user['id']])
    category_data = cur.fetchall()
    categories = [r[0] for r in category_data]
    amounts = [float(r[1] or 0) for r in category_data]

    cur.execute("""
        SELECT COALESCE(subcategory,'Uncategorized'), SUM(amount)
        FROM transactions
        WHERE user_id=%s AND category='Expense'
        GROUP BY COALESCE(subcategory,'Uncategorized')
    """, [user['id']])
    sub_data = cur.fetchall()
    subcategories = [r[0] for r in sub_data]
    sub_amounts = [float(r[1] or 0) for r in sub_data]

    cur.execute("""
        SELECT CASE WHEN DAYOFWEEK(transaction_date) IN (1,7) THEN 'Weekend' ELSE 'Weekday' END AS d,
               SUM(CASE WHEN category='Expense' THEN amount ELSE 0 END) AS s
        FROM transactions WHERE user_id=%s GROUP BY d
    """, [user['id']])
    ww = dict((r[0], float(r[1] or 0)) for r in cur.fetchall())

    next_month_forecast = simple_monthly_forecast(user['id'])

    return render_template('dashboard.html',
                           categories=categories,
                           amounts=amounts,
                           subcategories=subcategories,
                           sub_amounts=sub_amounts,
                           weekend_spend=ww.get('Weekend',0.0),
                           weekday_spend=ww.get('Weekday',0.0),
                           next_month_forecast=next_month_forecast)

# ---------- Chatbot ----------
def parse_intent(message):
    m = message.lower()
    food_last_month = re.search(r"(how much.*spend.*(food|grocer|restaurant).*(last month))", m)
    top3_week = re.search(r"(top\s*3.*categories.*(this|current)\s*week)", m)
    gen = re.search(r"how much.*spend.*on\s+([a-z\s]+)\s+(this|last)\s+(month|week)", m)

    if food_last_month:
        return {'type': 'food_last_month'}
    if top3_week:
        return {'type': 'top3_week'}
    if gen:
        return {'type': 'generic_spend', 'subcategory': gen.group(1).strip(), 'period_pos': gen.group(2), 'period_unit': gen.group(3)}
    if "advice" in m or "overspending" in m:
        return {'type': 'advice'}
    return {'type': 'fallback'}

@app.route('/chat')
def chat_page():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('chat.html', first_name=user['first_name'])

@app.route('/api/chat', methods=['POST'])
def chat_api():
    user = get_user()
    if not user:
        return jsonify({'response': "Please log in first."})
    data = request.get_json() or {}
    msg = data.get('message','').strip()
    if not msg:
        return jsonify({'response': "Ask me something like: 'How much did I spend on food last month?'"})

    intent = parse_intent(msg)
    cur = mysql.connection.cursor()

    if intent['type'] == 'food_last_month':
        start, end = last_month_bounds()
        cur.execute("""
            SELECT SUM(amount) FROM transactions
            WHERE user_id=%s AND category='Expense' AND (subcategory='Food' OR description LIKE '%%food%%')
              AND transaction_date BETWEEN %s AND %s
        """, [user['id'], start, end])
        total = float(fetchone_val(cur))
        return jsonify({'response': f"You spent ₹{total:.2f} on food last month."})

    if intent['type'] == 'top3_week':
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        cur.execute("""
            SELECT COALESCE(subcategory,'Uncategorized') sc, SUM(amount) s
            FROM transactions
            WHERE user_id=%s AND category='Expense'
              AND DATE(transaction_date) BETWEEN %s AND %s
            GROUP BY COALESCE(subcategory,'Uncategorized')
            ORDER BY s DESC LIMIT 3
        """, [user['id'], week_start, week_end])
        rows = cur.fetchall()
        if not rows:
            return jsonify({'response': "No expenses recorded this week."})
        lines = [f"{i+1}. {r[0]} (₹{float(r[1]):.2f})" for i, r in enumerate(rows)]
        return jsonify({'response': "Top 3 categories this week:\n" + "\n".join(lines)})

    if intent['type'] == 'generic_spend':
        sub = intent['subcategory'].title()
        when_pos = intent['period_pos']
        unit = intent['period_unit']

        if unit == 'month':
            if when_pos == 'last':
                start, end = last_month_bounds()
            else:
                start, end = month_bounds(datetime.now())
        else:
            today = datetime.now().date()
            if when_pos == 'last':
                week_end = today - timedelta(days=today.weekday()+1)
                week_start = week_end - timedelta(days=6)
            else:
                week_start = today - timedelta(days=today.weekday())
                week_end = week_start + timedelta(days=6)
            start = datetime.combine(week_start, datetime.min.time())
            end = datetime.combine(week_end, datetime.max.time())

        cur.execute("""
            SELECT SUM(amount) FROM transactions
            WHERE user_id=%s AND category='Expense'
              AND (subcategory=%s OR description LIKE %s)
              AND transaction_date BETWEEN %s AND %s
        """, [user['id'], sub, f"%{sub.lower()}%", start, end])
        total = float(fetchone_val(cur))
        return jsonify({'response': f"You spent ₹{total:.2f} on {sub} {when_pos} {unit}."})

    if intent['type'] == 'advice':
        cur.execute("""
            SELECT COALESCE(subcategory,'Uncategorized') sc, SUM(amount) s
            FROM transactions
            WHERE user_id=%s AND category='Expense'
              AND transaction_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY COALESCE(subcategory,'Uncategorized')
            ORDER BY s DESC LIMIT 5
        """, [user['id']])
        rows = cur.fetchall()
        if not rows:
            return jsonify({'response': "No recent expenses to analyze for advice."})

        total30 = sum(float(r[1]) for r in rows)
        advice = []
        for sc, s in rows:
            share = (float(s)/total30)*100 if total30>0 else 0
            if sc and sc.lower() in ('entertainment','eating out','food') and share > 20:
                advice.append(f"You're overspending on {sc} ({share:.1f}% of last 30 days). Try setting a weekly cap.")
        if not advice:
            advice.append("Spending looks balanced overall. Consider automating savings before expenses.")
        return jsonify({'response': "\n".join(advice)})

    return jsonify({'response': "I didn't catch that. Try:\n• How much did I spend on food last month?\n• Show me my top 3 categories this week\n• Give me spending advice"})

# ---------- Logout ----------
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ---------- Run ----------
if __name__ == '__main__':
    app.run(debug=True, port=PORT)
