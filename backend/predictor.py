import yfinance as yf
import pandas as pd
import joblib
import os
import plotly.graph_objects as go
import plotly.io as pio
from datetime import timedelta
from sklearn.metrics import mean_absolute_error

# Define absolute paths so Flask never gets confused about where the models are
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')

def fetch_and_prepare_data(ticker_symbol):
    """
    Fetches the latest market data and engineers the exact features your model expects.
    """
    ticker = yf.Ticker(ticker_symbol)
    
    # FIX: Increased to 1y so that after dropping 50 days for the SMA_50, 
    # we still have plenty of historical data left to make a beautiful chart!
    df = ticker.history(period="1y") 
    
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
    Loads the trained Ridge models, predicts next day prices, and generates an advanced Plotly chart.
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
        
        # ── ADVANCED PLOTLY CHART GENERATION ──
        chart_df = raw_df.tail(60).copy() # Show the last 2 months on the chart
        fig = go.Figure()

        # 1. Professional Candlestick Chart
        fig.add_trace(go.Candlestick(
            x=chart_df.index,
            open=chart_df['Open'],
            high=chart_df['High'],
            low=chart_df['Low'],
            close=chart_df['Close'],
            name='Daily Price',
            increasing_line_color='#10B981', # Emerald
            decreasing_line_color='#FF4455'  # Red
        ))

        # 2. Add 10-Day SMA Line
        fig.add_trace(go.Scatter(
            x=chart_df.index, y=chart_df['SMA_10'],
            mode='lines', name='10-Day SMA',
            line=dict(color='#00C6FF', width=1.5) # Cyan
        ))

        # 3. Add 50-Day SMA Line
        fig.add_trace(go.Scatter(
            x=chart_df.index, y=chart_df['SMA_50'],
            mode='lines', name='50-Day SMA',
            line=dict(color='#8A9BBE', width=1.5, dash='dot') # Muted text color
        ))

        # 4. Prediction Markers for Tomorrow
        next_day = chart_df.index[-1] + timedelta(days=1)
        
        # Predicted Close (Star)
        fig.add_trace(go.Scatter(
            x=[next_day], y=[pred_close],
            mode='markers', name='Predicted Close',
            marker=dict(size=14, color='#10B981', symbol='star', line=dict(color='white', width=1))
        ))
        
        # Prediction Range (High to Low Line)
        fig.add_trace(go.Scatter(
            x=[next_day, next_day], y=[pred_low, pred_high],
            mode='lines', name='Predicted Range',
            line=dict(color='rgba(16, 185, 129, 0.5)', width=4)
        ))

        # 5. UI Styling & Interactivity
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8A9BBE', family='Sora, sans-serif'),
            hovermode='x unified', # Creates the professional crosshair and popup box
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(
                showgrid=False, 
                zeroline=False,
                rangeslider=dict(visible=False), # Hides the bulky default scrollbar
                type='date'
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='rgba(138, 155, 190, 0.1)', 
                zeroline=False,
                tickprefix='$'
            ),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        chart_json = pio.to_json(fig)

        # Calculate historical accuracy (MAE) using all available data
        historical_features = scaler.transform(raw_df[['SMA_10', 'SMA_50', 'Daily_Return']])
        historical_preds = model_close.predict(historical_features)
        mae = mean_absolute_error(raw_df['Close'], historical_preds)
        accuracy_pct = round(100 - (mae / latest_close * 100), 2)
        
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
            "chart_json": chart_json,
            "mae_score": round(mae, 2),
            "accuracy_pct": accuracy_pct
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }