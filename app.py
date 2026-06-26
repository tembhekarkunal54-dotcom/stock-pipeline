"""
Stock Dashboard with Streamlit - Real Data from Database.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from src.config import settings

# Page configuration
st.set_page_config(
    page_title="Stock Dashboard",
    page_icon="📈",
    layout="wide"
)

# Title
st.title("📈 Stock Pipeline Dashboard")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("📊 Status")
    st.success("✅ Pipeline is running!")
    st.write(f"⏰ Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# Load data from database
@st.cache_data(ttl=60)
def load_data_from_db():
    """Load real data from database."""
    try:
        engine = create_engine(settings.DB_URL)
        query = "SELECT * FROM stock_prices ORDER BY symbol, date"
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# Load data
df = load_data_from_db()

# Check if data exists
if df.empty:
    st.warning("⚠️ No data in database. Please run the pipeline first:")
    st.code("python src/main.py --once", language="bash")
    
    # Show sample data as fallback
    st.subheader("📊 Sample Data (Demo Mode)")
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    sample_df = pd.DataFrame({
        'Date': dates,
        'AAPL': np.random.randn(30).cumsum() + 150,
        'GOOGL': np.random.randn(30).cumsum() + 140,
        'MSFT': np.random.randn(30).cumsum() + 380,
    })
    st.line_chart(sample_df.set_index('Date'))
    st.dataframe(sample_df)
    
else:
    # Display real data
    st.success(f"✅ Loaded {len(df)} records from database")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Status", "🟢 Active", delta="Running")
    
    with col2:
        stocks = df["symbol"].nunique()
        st.metric("Stocks", stocks)
    
    with col3:
        records = len(df)
        st.metric("Records", f"{records:,}")
    
    with col4:
        # Check if anomalies column exists
        if "is_anomaly" in df.columns:
            anomalies = df["is_anomaly"].sum()
            st.metric("Anomalies", f"{anomalies}", delta="⚠️ Detected" if anomalies > 0 else "✅ Clean")
        else:
            st.metric("Anomalies", "N/A")
    
    st.markdown("---")
    
    # Price chart
    st.subheader("📈 Price Trends")
    
    # Get symbols
    symbols = df["symbol"].unique()
    
    # Create chart
    import plotly.express as px
    
    fig = px.line(
        df,
        x="date",
        y="close",
        color="symbol",
        title="Stock Prices",
        labels={"date": "Date", "close": "Price ($)", "symbol": "Stock"}
    )
    
    # Add anomaly markers
    if "is_anomaly" in df.columns:
        anomalies_df = df[df["is_anomaly"] == True]
        if not anomalies_df.empty:
            fig.add_scatter(
                x=anomalies_df["date"],
                y=anomalies_df["close"],
                mode="markers",
                name="Anomalies",
                marker=dict(color="red", size=10, symbol="x")
            )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Volume chart
    st.subheader("📊 Trading Volume")
    fig2 = px.bar(
        df,
        x="date",
        y="volume",
        color="symbol",
        title="Volume by Stock",
        labels={"date": "Date", "volume": "Volume", "symbol": "Stock"},
        barmode="group"
    )
    fig2.update_layout(height=300)
    st.plotly_chart(fig2, use_container_width=True)
    
    # Data table
    st.subheader("📋 Data Table")
    
    # Select columns to display
    display_cols = ["symbol", "date", "open", "high", "low", "close", "volume"]
    if "is_anomaly" in df.columns:
        display_cols.append("is_anomaly")
    
    display_df = df[display_cols].copy()
    display_df["date"] = pd.to_datetime(display_df["date"]).dt.date
    
    st.dataframe(
        display_df,
        column_config={
            "symbol": "Symbol",
            "date": "Date",
            "open": st.column_config.NumberColumn("Open", format="$%.2f"),
            "high": st.column_config.NumberColumn("High", format="$%.2f"),
            "low": st.column_config.NumberColumn("Low", format="$%.2f"),
            "close": st.column_config.NumberColumn("Close", format="$%.2f"),
            "volume": st.column_config.NumberColumn("Volume", format="%d"),
            "is_anomaly": st.column_config.CheckboxColumn("Anomaly"),
        },
        use_container_width=True
    )
    
    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name=f"stock_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # Summary statistics
    with st.expander("📊 Summary Statistics"):
        summary = df.groupby("symbol").agg({
            "close": ["mean", "min", "max", "std"],
            "volume": "sum"
        }).round(2)
        summary.columns = ["Avg Price", "Min Price", "Max Price", "Std Dev", "Total Volume"]
        st.dataframe(summary)

st.markdown("---")
st.success("✅ Dashboard is ready! Data is from database.")