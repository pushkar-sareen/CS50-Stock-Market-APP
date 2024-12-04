import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks and cash"""
    user_id = session["user_id"]

    
    cash_row = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
    cash = cash_row[0]["cash"] if cash_row else 0

   
    stocks = db.execute("""
        SELECT symbol, SUM(shares) AS total_shares
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING total_shares > 0
    """, user_id)

    holdings = []
    total_value = cash
    for stock in stocks:
        quote = lookup(stock["symbol"])
        if quote:
            stock_value = stock["total_shares"] * quote["price"]
            total_value += stock_value
            holdings.append({
                "symbol": stock["symbol"],
                "shares": stock["total_shares"],
                "price": usd(quote["price"]),
                "total": usd(stock_value)
            })
    return render_template("index.html", cash=usd(cash), holdings=holdings, total=usd(total_value))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    
    db.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        shares INTEGER NOT NULL,
        price NUMERIC NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    if request.method == "POST":
       
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        if not symbol:
            return apology("must provide stock symbol", 400)
        if not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("must provide a valid number of shares", 400)

        shares = int(shares)

        stock = lookup(symbol)
        if stock is None:
            return apology("invalid stock symbol", 400)

        stock_price = stock["price"]
        total_cost = stock_price * shares

        user = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        if not user or len(user) == 0:
            return apology("user not found", 400)

        user_cash = user[0]["cash"]

        
        if total_cost > user_cash:
            return apology("not enough cash to complete purchase", 400)

        
        db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", total_cost, session["user_id"])
        db.execute(
            "INSERT INTO transactions (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)",
            session["user_id"], symbol, shares, stock_price
        )

        flash("Bought!")
        return redirect("/")


    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    
    user_id = session["user_id"]

    transactions = db.execute("""
        SELECT symbol, shares, price, timestamp
        FROM transactions
        WHERE user_id = ?
        ORDER BY timestamp DESC
    """, user_id)

    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    session.clear()

    if request.method == "POST":
       
        if not request.form.get("username"):
            return apology("must provide username", 403)

       
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]

        return redirect("/")


    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    session.clear()


    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        
        symbol = request.form.get("symbol")

        if not symbol:
            return render_template("quote.html", error="Must provide stock symbol.")

  
        stock = lookup(symbol)

        if stock is None:
            return apology("Invalid Symbol")

        return render_template("quoted.html", stock=stock)

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)

        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        hashed_password = generate_password_hash(request.form.get("password"))

       
        try:
            result = db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                request.form.get("username"),
                hashed_password,
            )
        except:
            return apology("username already taken", 400)

        session["user_id"] = result
        flash("Registered!")
        return redirect("/")

    else:
        
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        
        user_id = session["user_id"]

        symbol = request.form.get("symbol").upper()
        shares_to_sell = request.form.get("shares")

        if not symbol:
            return apology("must provide stock symbol", 400)
        if not shares_to_sell or not shares_to_sell.isdigit() or int(shares_to_sell) <= 0:
            return apology("must provide a valid number of shares", 400)

        shares_to_sell = int(shares_to_sell)

        stock_ownership = db.execute("""
            SELECT symbol, SUM(shares) AS total_shares
            FROM transactions
            WHERE user_id = ? AND symbol = ?
            GROUP BY symbol
        """, user_id, symbol)

        if not stock_ownership or stock_ownership[0]["total_shares"] < shares_to_sell:
            return apology("not enough shares to sell", 400)

     
        stock = lookup(symbol)
        if not stock:
            return apology("invalid stock symbol", 400)

      
        sale_price = stock["price"]
        total_sale_value = sale_price * shares_to_sell

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", total_sale_value, user_id)

        db.execute("""
            INSERT INTO transactions (user_id, symbol, shares, price)
            VALUES (?, ?, ?, ?)
        """, user_id, symbol, -shares_to_sell, sale_price)

        flash("Sold!")
        return redirect("/")


    user_id = session["user_id"]
    stocks = db.execute("""
        SELECT symbol, SUM(shares) AS total_shares
        FROM transactions
        WHERE user_id = ?
        GROUP BY symbol
        HAVING total_shares > 0
    """, user_id)

    return render_template("sell.html", stocks=stocks)

