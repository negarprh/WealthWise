from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import yfinance as yf
import pandas as pd
import os
import matplotlib.pyplot as plt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError


app = Flask(__name__)
app.secret_key = '123456789'

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

# Load user callback
@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect('finance_tracker.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            return User(user[0], user[1])
        return None

# Database setup
# Updated Database setup with month column
def init_db():
    with sqlite3.connect('finance_tracker.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL UNIQUE,
                            password TEXT NOT NULL
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            category TEXT NOT NULL,
                            amount REAL NOT NULL,
                            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS income (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            monthly_income REAL NOT NULL,
                            month TEXT NOT NULL,
                            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS investments (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            ticker TEXT NOT NULL,
                            quantity INTEGER NOT NULL,
                            price REAL NOT NULL,
                            total REAL NOT NULL,
                            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(user_id) REFERENCES users(id)
                          )''')
        conn.commit()


init_db()


# Welcome route
@app.route('/')
def welcome():
    return render_template('welcome.html')  # A simple page with "Login" and "Sign-Up" buttons

# Sign-Up route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])  # Hash the password
        try:
            with sqlite3.connect('finance_tracker.db') as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                flash('Sign-up successful! Please log in.', 'success')
                return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please try again.', 'error')
    return render_template('signup.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('finance_tracker.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user[1], password):
                user_obj = User(user[0], username)
                login_user(user_obj)
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')


# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('welcome'))

#Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = current_user.id
    with sqlite3.connect('finance_tracker.db') as conn:
        cursor = conn.cursor()

        # Fetch user-specific expenses
        cursor.execute("SELECT id, date, category, amount FROM expenses WHERE user_id = ? ORDER BY date DESC", (user_id,))
        expenses = cursor.fetchall()

        # Fetch user-specific investments
        cursor.execute("SELECT id, ticker, quantity, price, total, date FROM investments WHERE user_id = ? ORDER BY date DESC", (user_id,))
        investments = cursor.fetchall()

        # Fetch user-specific income
        cursor.execute("SELECT id, monthly_income, month, date FROM income WHERE user_id = ? ORDER BY date DESC", (user_id,))
        income = cursor.fetchall()

        # Generate charts
        generate_expense_chart(user_id)
        generate_investment_chart(user_id)

    return render_template(
        'dashboard.html',
        expenses=expenses,
        investments=investments,
        income=income
    )





# Add expense
@app.route('/add-expense', methods=['POST'])
@login_required
def add_expense():
    try:
        category = request.form['category']
        amount = float(request.form['amount'])
        user_id = current_user.id
        with sqlite3.connect('finance_tracker.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO expenses (user_id, category, amount) VALUES (?, ?, ?)", (user_id, category, amount))
            conn.commit()
        flash('Expense added successfully!', 'success')
    except Exception as e:
        flash(f"Error adding expense: {e}", "error")
    return redirect(url_for('dashboard'))

# Delete expense
@app.route('/delete-expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    try:
        with sqlite3.connect('finance_tracker.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            conn.commit()
    except Exception as e:
        flash(f"Error deleting expense: {e}", "error")
    return redirect(url_for('dashboard'))




# Add income with month tracking
@app.route('/add-income', methods=['POST'])
@login_required
def add_income():
    try:
        monthly_income = float(request.form['income'])
        month = request.form['month']  # Format: YYYY-MM
        user_id = current_user.id  # Get the logged-in user's ID
        with sqlite3.connect('finance_tracker.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO income (user_id, monthly_income, month) VALUES (?, ?, ?)", (user_id, monthly_income, month))
            conn.commit()
        flash('Income added successfully!', 'success')
    except Exception as e:
        flash(f"Error adding income: {e}", 'error')
    return redirect(url_for('dashboard'))

# Delete income
@app.route('/delete-income/<int:income_id>', methods=['POST'])
@login_required
def delete_income(income_id):
    try:
        user_id = current_user.id
        with sqlite3.connect('finance_tracker.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM income WHERE id = ? AND user_id = ?", (income_id, user_id))
            conn.commit()
        flash('Income deleted successfully!', 'success')
    except Exception as e:
        flash(f"Error deleting income: {e}", 'error')
    return redirect(url_for('dashboard'))

# Add investment
@app.route('/add-investment', methods=['POST'])
def add_investment():
    try:
        ticker = request.form['ticker'].upper()
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])

        # Fetch stock price
        stock = yf.Ticker(ticker)
        stock_history = stock.history(period="1d")

        # Check if the data is empty
        if stock_history.empty:
            flash(f"Error: Could not fetch data for ticker {ticker}. Please try again with a valid ticker.", "error")
            return redirect(url_for('dashboard'))

        # Extract the closing price of the last day if available
        current_price = stock_history['Close'].iloc[-1] if 'Close' in stock_history.columns else None

        if current_price is None:
            flash(f"Error: Closing price not available for ticker {ticker}.", "error")
            return redirect(url_for('dashboard'))

        total_value = quantity * price

        # Add to database
        with sqlite3.connect('finance_tracker.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO investments (ticker, quantity, price, total) VALUES (?, ?, ?, ?)",
                           (ticker, quantity, price, total_value))
            conn.commit()

        flash('Investment added successfully!', 'success')
    except Exception as e:
        flash(f"Error adding investment: {e}", "error")
    return redirect(url_for('dashboard'))


# Generate expense chart function
def generate_expense_chart(user_id):
    with sqlite3.connect('finance_tracker.db') as conn:
        df = pd.read_sql_query("SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category", conn, params=(user_id,))

    plt.figure(figsize=(8, 6))
    plt.bar(df['category'], df['total'], color='blue')
    plt.title('Expenses by Category')
    plt.xlabel('Category')
    plt.ylabel('Total Expense')
    plt.savefig('static/expense_chart.png')
    plt.close()

# Generate investment chart function
def generate_investment_chart(user_id):
    with sqlite3.connect('finance_tracker.db') as conn:
        df = pd.read_sql_query("SELECT ticker, SUM(total) as total_value FROM investments WHERE user_id = ? GROUP BY ticker", conn, params=(user_id,))

    plt.figure(figsize=(8, 6))
    plt.pie(df['total_value'], labels=df['ticker'], autopct='%1.1f%%', startangle=90)
    plt.title('Investment Portfolio Distribution')
    plt.savefig('static/investment_chart.png')
    plt.close()


if __name__ == "__main__":
    app.run(debug=True)
