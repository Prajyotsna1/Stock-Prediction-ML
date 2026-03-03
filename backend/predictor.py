import yfinance as yf
import pandas as pd
import joblib
import os
import plotly.graph_objects as go
import plotly.io as pio
from datetime import timedelta

# Define absolute paths so Flask never gets confused about where the models are
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')

def fetch_and_prepare_data(ticker_symbol):
    """
    Fetches the latest market data and engineers the exact features your model expects.
    """
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="3mo")
    
    if df.empty:
        raise ValueError(f"No data found for ticker {ticker_symbol}")

    # Smart Feature Engineering
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['Daily_Return'] = df['Close'].pct_change()
    
    df = df.dropna()
    latest_data = df.iloc[-1]
    
    # Structure the features exactly as trained
    features = pd.DataFrame([{
        'SMA_10': latest_data['SMA_10'],
        'SMA_50': latest_data['SMA_50'],
        'Daily_Return': latest_data['Daily_Return']
    }])
    
    return features, df

def predict_tomorrow(ticker_symbol):
    """
    Loads the trained Ridge models, predicts next day prices, and generates a Plotly chart.
    """
    try:
        features, raw_df = fetch_and_prepare_data(ticker_symbol)
        
        scaler = joblib.load(os.path.join(MODELS_DIR, 'feature_scaler.pkl'))
        scaled_features = scaler.transform(features)
        
        model_close = joblib.load(os.path.join(MODELS_DIR, 'ridge_close.pkl'))
        model_high = joblib.load(os.path.join(MODELS_DIR, 'ridge_high.pkl'))
        model_low = joblib.load(os.path.join(MODELS_DIR, 'ridge_low.pkl'))
        
        pred_close = model_close.predict(scaled_features)[0]
        pred_high = model_high.predict(scaled_features)[0]
        pred_low = model_low.predict(scaled_features)[0]
        
        latest_close = raw_df.iloc[-1]['Close']
        
        # ── PLOTLY CHART GENERATION ──
        chart_df = raw_df.tail(30).copy()
        fig = go.Figure()

        # Historical Line
        fig.add_trace(go.Scatter(
            x=chart_df.index, y=chart_df['Close'],
            mode='lines+markers', name='Historical Close',
            line=dict(color='#00C6FF', width=2), marker=dict(size=5, color='#00C6FF')
        ))

        # Prediction Line (Connecting today to tomorrow)
        next_day = chart_df.index[-1] + timedelta(days=1)
        fig.add_trace(go.Scatter(
            x=[chart_df.index[-1], next_day], y=[latest_close, pred_close],
            mode='lines+markers', name='Predicted Close',
            line=dict(color='#00FF88', width=2, dash='dash'), marker=dict(size=8, color='#00FF88', symbol='star')
        ))

        # UI Styling
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8A9BBE', family='Sora, sans-serif'),
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=True, gridcolor='#1E2D4A', zeroline=False)
        )

        chart_json = pio.to_json(fig)
        
        return {
            "status": "success",
            "ticker": ticker_symbol.upper(),
            "latest_close": round(latest_close, 2),
            "predicted_high": round(pred_high, 2),
            "predicted_low": round(pred_low, 2),
            "predicted_close": round(pred_close, 2),
            "sma_10": round(raw_df.iloc[-1]['SMA_10'], 2),
            "sma_50": round(raw_df.iloc[-1]['SMA_50'], 2),
            "daily_return": round(raw_df.iloc[-1]['Daily_Return'] * 100, 2),
            "volume": f"{int(raw_df.iloc[-1]['Volume']):,}",
            "chart_json": chart_json
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }