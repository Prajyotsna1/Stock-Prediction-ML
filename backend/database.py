from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Initialize the database object
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # We will store a hashed password, NEVER plain text!
    
    # Establish a relationship: One user can have many watchlist items
    watchlist_items = db.relationship('Watchlist', backref='user', lazy=True)

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # --- NEW COLUMNS ---
    saved_price = db.Column(db.Float, nullable=True) 
    date_saved = db.Column(db.DateTime, default=datetime.utcnow)