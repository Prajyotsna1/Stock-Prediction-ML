import requests
import pandas as pd
import ssl

from flask import Flask, render_template, request, redirect, url_for, flash
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
    return User.query.get(int(user_id))

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
            new_item = Watchlist(ticker=ticker, user_id=current_user.id)
            db.session.add(new_item)
            db.session.commit()
            flash(f"Successfully added {ticker} to your watchlist!", "success")
        else:
            flash(f"{ticker} is already in your watchlist.", "info")
            
    return redirect(url_for('dashboard'))

@app.route('/delete_stock/<int:item_id>', methods=['POST'])
@login_required
def delete_stock(item_id):
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
    # Pull all watchlist items belonging to the currently logged-in user
    user_watchlist = Watchlist.query.filter_by(user_id=current_user.id).all()
    # Pass that data to the template
    return render_template('dashboard.html', watchlist=user_watchlist)

if __name__ == '__main__':
    app.run(debug=True, port=5000)