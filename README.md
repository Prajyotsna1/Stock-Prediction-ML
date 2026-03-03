📈 PredictX — AI Market Predictor

An intelligent, web-based financial forecasting system powered by Machine Learning. Predict tomorrow's market movements with confidence.

🚀 Overview
PredictX is a full-stack web application designed to forecast next-day stock prices using historical market data and technical indicators. Built with a Python/Flask backend and a custom, responsive frontend, it allows users to search for live stocks, view machine learning-powered price predictions, and manage a personalized portfolio watchlist.

✨ Key Features
* **ML-Powered Forecasting:** Utilizes **Ridge Regression** to predict the next day's High, Low, and Closing prices based on features like 10-day SMA, 50-day SMA, and daily returns.
* **Live Market Data:** Integrates with the `yfinance` API to fetch real-time stock prices, historical data, and trading volumes.
* **Secure User Authentication:** Full login and registration system using `Werkzeug` password hashing and `Flask-Login` for session management.
* **Personalized Dashboard:** A dynamic portfolio tracker that calculates live total returns (%) on saved watchlist stocks.
* **Interactive Visualizations:** Implements `Plotly.js` for interactive, responsive stock charts.
* **Custom UI/UX:** Features a bespoke "Emerald White Metallic" Light Mode and a deep Cyan Dark Mode with seamless CSS theme toggling, floating scrollbars, and dynamic loading states.

💻 Tech Stack
**Frontend:**
* HTML5, CSS3 (Custom Variables & Animations)
* JavaScript (DOM manipulation, asynchronous UI updates)
* Plotly.js (Data Visualization)
* FontAwesome (Icons)

**Backend:**
* Python 3.x
* Flask (Web Framework)
* Flask-SQLAlchemy (ORM)
* Flask-Login (Authentication)

**Machine Learning & Data:**
* Scikit-Learn (Ridge Regression, Model Evaluation via MSE/MAE)
* Pandas & NumPy (Data manipulation)
* yFinance (Market data extraction)

⚙️ Local Setup & Installation

Follow these steps to run PredictX on your local machine.

**1. Clone the repository and navigate to the project directory:**
```bash
git clone https://github.com/Prajyotsna1/PredictX.git
cd PredictX
```

**2. Create and activate a virtual environment:**
```bash
python -m venv venv
# For Windows:
venv\Scripts\activate
# For macOS/Linux:
source venv/bin/activate
```

**3. Install the required dependencies:**
```bash
pip install -r requirements.txt
```
**4. Run the application:**
```bash
python app.py
```
