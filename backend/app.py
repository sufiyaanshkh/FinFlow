from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets

# Paths to templates and static files (CSS/JS)
base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.abspath(os.path.join(base_dir, '../frontend/templates'))
static_dir = os.path.abspath(os.path.join(base_dir, '../frontend/static'))

# Initialize Flask app with both folders
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Secure session key
app.secret_key = secrets.token_hex(24)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # Update if different
app.config['MYSQL_PASSWORD'] = '#20Sufi04'  # Update with your real password
app.config['MYSQL_DB'] = 'finflow_db'

# Initialize MySQL
mysql = MySQL(app)

# Route: Home
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
        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', [email])
        user = cursor.fetchone()

        if user and check_password_hash(user[4], password):  # user[4] is password
            session['user_id'] = user[0]
            session['first_name'] = user[1]  # ✅ Store first name in session
            flash('Login Successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid Credentials. Please try again.', 'danger')
    return render_template('auth.html')


# Route: Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first-name']
        last_name = request.form['last-name']
        email = request.form['email']
        password = request.form['password']
        occupation = request.form['occupation']
        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', [email])
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email already exists!', 'danger')
            return render_template('auth.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return render_template('auth.html')

        hashed_password = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (first_name, last_name, email, password, occupation)
            VALUES (%s, %s, %s, %s, %s)
        ''', (first_name, last_name, email, hashed_password, occupation))
        mysql.connection.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('auth.html')

# Route: Dashboard
@app.route('/dashboard')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    
    # Fetch recent 5 transactions
    cursor.execute('''
        SELECT * FROM transactions 
        WHERE user_id = %s 
        ORDER BY transaction_date DESC 
        LIMIT 5
    ''', [session['user_id']])
    transactions = cursor.fetchall()

    # Totals
    cursor.execute('SELECT SUM(amount) FROM transactions WHERE user_id = %s AND category = "Income"', [session['user_id']])
    total_income = cursor.fetchone()[0] or 0

    cursor.execute('SELECT SUM(amount) FROM transactions WHERE user_id = %s AND category = "Expense"', [session['user_id']])
    total_expenses = cursor.fetchone()[0] or 0

    net_balance = total_income - total_expenses

    # ✅ Pass first_name to the template
    return render_template(
        'index.html',
        first_name=session.get('first_name'),
        transactions=transactions,
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=net_balance
    )



# Route: View All Transactions
@app.route('/all-transactions')
def all_transactions():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute('''
        SELECT * FROM transactions 
        WHERE user_id = %s 
        ORDER BY transaction_date DESC
    ''', [session['user_id']])
    transactions = cursor.fetchall()

    return render_template('all_transactions.html', transactions=transactions)

# Route: Add Transaction
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    description = request.form['description']
    amount = request.form['amount']
    category = request.form['category']
    subcategory = request.form.get('subcategory') if category == 'Expense' else None

    cursor = mysql.connection.cursor()
    cursor.execute('''
        INSERT INTO transactions (user_id, description, amount, category, subcategory, transaction_date)
        VALUES (%s, %s, %s, %s, %s, NOW())
    ''', (session['user_id'], description, amount, category, subcategory))
    mysql.connection.commit()

    flash('Transaction added successfully!', 'success')
    return redirect(url_for('index'))

# Route: Analytics Dashboard
@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()

    # For bar chart and general category data
    cursor.execute('''
        SELECT category, SUM(amount)
        FROM transactions
        WHERE user_id = %s
        GROUP BY category
    ''', [session['user_id']])
    category_data = cursor.fetchall()
    categories = [row[0] for row in category_data]
    amounts = [float(row[1]) for row in category_data]

    # For pie chart of subcategories in Expense
    cursor.execute('''
        SELECT subcategory, SUM(amount)
        FROM transactions
        WHERE user_id = %s AND category = 'Expense'
        GROUP BY subcategory
    ''', [session['user_id']])
    sub_data = cursor.fetchall()
    subcategories = [row[0] if row[0] else "Uncategorized" for row in sub_data]
    sub_amounts = [float(row[1]) for row in sub_data]

    return render_template(
        'dashboard.html',
        categories=categories,
        amounts=amounts,
        subcategories=subcategories,
        sub_amounts=sub_amounts
    )




# Route: Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5002)