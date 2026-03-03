import requests
import pandas as pd
import ssl
import yfinance as yf
# from google import genai

# Configure your API Key (Get a free one from Google AI Studio)
# client = genai.Client(api_key="AIzaSyCg0s8Pmz302No5D78m2D9jQyr74n-WW1M")

from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import pandas as pd

from config import Config
from backend.predictor import predict_tomorrow
from backend.database import db, User, Watchlist

app = Flask(__name__)

# Explicitly set the configuration so Flask never loses it
app.config['SECRET_KEY'] = 'predictx-sem6-super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///predictx.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── DATABASE & LOGIN SETUP ──
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # If someone tries to access Dashboard without logging in, redirect them here
login_manager.login_message = "Please log in to access your dashboard."
login_manager.login_message_category = "error"

@login_manager.user_loader
def load_user(user_id):
    # Modern SQLAlchemy 2.0 way:
    return db.session.get(User, int(user_id))

# Create database tables automatically if they don't exist
with app.app_context():
    db.create_all()

# ── GLOBAL CACHE FOR STOCKS ──
import requests
import pandas as pd
import ssl

# ── GLOBAL CACHE FOR STOCKS ──
STOCK_CACHE = []

def get_dynamic_stocks():
    global STOCK_CACHE
    if STOCK_CACHE:
        return STOCK_CACHE
        
    fallback_stocks = [
        {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
        {"symbol": "MSFT", "name": "Microsoft Corp.", "sector": "Technology"},
        {"symbol": "TSLA", "name": "Tesla, Inc.", "sector": "Automotive"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Cyclical"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Communication"},
        {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy"},
        {"symbol": "TCS.NS", "name": "Tata Consultancy Services", "sector": "Technology"},
        {"symbol": "INFY.NS", "name": "Infosys Limited", "sector": "Technology"},
        {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Financials"}
    ]
    
    try:
        print("Fetching live S&P 500 stock directory from Wikipedia...")
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        
        # Fake a Google Chrome browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Make sure the website actually loaded
        
        # Let pandas read the raw HTML text from our successful request
        table = pd.read_html(response.text)[0]
        
        dynamic_stocks = [{"symbol": row['Symbol'], "name": row['Security'], "sector": row['GICS Sector']} for _, row in table.iterrows()]
        indian_stocks = [s for s in fallback_stocks if ".NS" in s["symbol"]]
        
        STOCK_CACHE = indian_stocks + dynamic_stocks
        print(f"Successfully loaded {len(STOCK_CACHE)} stocks into the directory!")
        return STOCK_CACHE
        
    except Exception as e:
        print(f"Scrape failed: {e}")
        print("Using the reliable local fallback list instead.")
        STOCK_CACHE = fallback_stocks
        return STOCK_CACHE

# ── ROUTES ──
@app.route('/ask_ai', methods=['POST'])
def ask_ai():
    query = request.json.get('message', '').lower()
    
    # ── NAVIGATION ──
    if 'how to use' in query:
        reply = "Search for a ticker (like RELIANCE.NS) in the Predictor and click 'Forecast' to see tomorrow's estimated prices."
    elif 'save' in query:
        reply = "After a prediction, click 'Save to Watchlist'. You can then track live prices and returns on your Dashboard."
    
    # ── FINANCIAL TERMS ──
    elif 'close' in query:
        reply = "The 'Close' is the final trading price of the day. It's the primary value our Ridge model aims to predict."
    elif 'high' in query or 'low' in query:
        reply = "The 'High' is the peak price and the 'Low' is the bottom price of the day. Our model estimates this range for you."
    elif 'volume' in query:
        reply = "Trading Volume is the total number of shares traded. High volume indicates strong market interest in a price move."
    
    # ── TECHNICAL INDICATORS ──
    elif '10-day' in query:
        reply = "The 10-day SMA is the average price over 10 days. It helps the model detect short-term trends and momentum."
    elif '50-day' in query:
        reply = "The 50-day SMA is the average price over 50 days, used by the model to identify the long-term trend direction."
    elif 'daily return' in query:
        reply = "Daily Return is the % change from the previous day. It measures daily volatility to help the model adjust forecasts."
    
    # ── MACHINE LEARNING ──
    elif 'ridge' in query:
        reply = "Ridge Regression uses L2 Regularization to penalize large coefficients, preventing overfitting and handling market noise."
    elif 'mae' in query:
        reply = "MAE (Mean Absolute Error) is the average dollar amount the prediction is off by. In this project, lower MAE means higher accuracy."
    elif 'mse' in query:
        reply = "MSE (Mean Squared Error) squares the errors to penalize major 'misses' more heavily, ensuring the model stays reliable."
    
    else:
        reply = "I'm the PredictX guide! Select an option to learn more about my features."
        
    return jsonify({"reply": reply})
          
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        fullname = request.form.get('fullname')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        user_exists = User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first()
        if user_exists:
            # For now, we'll just redirect back. Later we can add pop-up flash messages!
            return redirect(url_for('register'))
            
        # Secure the password using hashing before saving it
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        new_user = User(fullname=fullname, username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        # Automatically log them in after creating the account
        login_user(new_user)
        return redirect(url_for('dashboard'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # Verify user exists and the password matches the hashed version in the DB
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            # Login failed
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    # We already have access to 'current_user' thanks to Flask-Login
    return render_template('profile.html', user=current_user)

@app.route('/stocks')
def stocks():
    popular_stocks = get_dynamic_stocks()
    return render_template('stocks.html', stocks=popular_stocks)

@app.route('/predictor', methods=['GET', 'POST'])
def predictor():
    prediction_data = None
    if request.method == 'POST':
        ticker = request.form.get('ticker', '').strip().upper()
        if ticker:
            prediction_data = predict_tomorrow(ticker)
    return render_template('predictor.html', prediction_data=prediction_data)

# ── WATCHLIST ROUTES ──

@app.route('/save_stock', methods=['POST'])
@login_required
def save_stock():
    ticker = request.form.get('ticker')
    if ticker:
        existing_stock = Watchlist.query.filter_by(user_id=current_user.id, ticker=ticker).first()
        if not existing_stock:
            # 1. Quickly fetch the price AT THIS EXACT MOMENT
            try:
                stock_data = yf.Ticker(ticker).history(period="1d")
                current_price = round(stock_data['Close'].iloc[-1], 2) if not stock_data.empty else 0.0
            except:
                current_price = 0.0

            # 2. Save it to the database with the price attached
            new_item = Watchlist(ticker=ticker, user_id=current_user.id, saved_price=current_price)
            db.session.add(new_item)
            db.session.commit()
            flash(f"Successfully saved {ticker} at ${current_price}!", "success")
        else:
            flash(f"{ticker} is already in your watchlist.", "info")
            
    return redirect(url_for('dashboard'))

@app.route('/delete_stock/<int:item_id>', methods=['POST'])
@login_required
def delete_stock(item_id):
    # Find the specific stock in the database
    item = Watchlist.query.filter_by(id=item_id, user_id=current_user.id).first()
    
    if item:
        ticker = item.ticker
        db.session.delete(item)
        db.session.commit()
        flash(f"Removed {ticker} from your watchlist.", "error")
        
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
    enriched_watchlist = []
    
    for item in user_watchlist:
        # 1. Get the LIVE price right now
        try:
            stock_data = yf.Ticker(item.ticker).history(period="1d")
            live_price = round(stock_data['Close'].iloc[-1], 2) if not stock_data.empty else 0.0
        except:
            live_price = 0.0
            
        # 2. Calculate the Total Return (%) since the day it was saved
        if item.saved_price and item.saved_price > 0:
            total_return = round(((live_price - item.saved_price) / item.saved_price) * 100, 2)
        else:
            total_return = 0.0
            
        # 3. Format the date beautifully (e.g., "Mar 03, 2026")
        formatted_date = item.date_saved.strftime("%b %d, %Y") if item.date_saved else "N/A"
            
        enriched_watchlist.append({
            'id': item.id,
            'ticker': item.ticker,
            'saved_price': item.saved_price,
            'live_price': live_price,
            'date_saved': formatted_date,
            'total_return': total_return
        })
        
    return render_template('dashboard.html', watchlist=enriched_watchlist)

if __name__ == '__main__':
    app.run(debug=True, port=5000)