import csv
import datetime
import pytz
import requests
import urllib
import uuid
import yfinance as yf
from datetime import datetime, timedelta


from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


# def lookup(symbol):
#     """Look up quote for symbol."""

#     # Prepare API request
#     symbol = symbol.upper()
#     end = datetime.datetime.now(pytz.timezone("US/Eastern"))
#     start = end - datetime.timedelta(days=7)

#     # Yahoo Finance API
#     url = (
#         f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote_plus(symbol)}"
#         f"?period1={int(start.timestamp())}"
#         f"&period2={int(end.timestamp())}"
#         f"&interval=1d&events=history&includeAdjustedClose=true"
#     )

#     # Query API
#     try:
#         response = requests.get(
#             url,
#             cookies={"session": str(uuid.uuid4())},
#             headers={"Accept": "*/*", "User-Agent": request.headers.get("User-Agent")},
#         )
#         response.raise_for_status()

#         # CSV header: Date,Open,High,Low,Close,Adj Close,Volume
#         quotes = list(csv.DictReader(response.content.decode("utf-8").splitlines()))
#         price = round(float(quotes[-1]["Adj Close"]), 2)
#         return {"price": price, "symbol": symbol}
#     except (KeyError, IndexError, requests.RequestException, ValueError):
#         return None



def lookup(symbol):
    """Look up the latest adjusted close price for a given stock symbol."""
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        
        stock_data = yf.Ticker(symbol)
        stock_info = stock_data.info
        history = stock_data.history(start=start_date, end=end_date)
        
        
        if history.empty:
            return None
        latest_price = round(history["Close"].iloc[-1], 2)
        company_name = stock_info["shortName"]
        return {"price": latest_price, "symbol": symbol.upper(), "company_name": company_name}
    except (KeyError, IndexError, ValueError):
        return None




def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

