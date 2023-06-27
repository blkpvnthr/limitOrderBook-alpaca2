import alpaca_trade_api as tradeapi
import numpy as np
import yfinance as yf
import datetime as dt
import matplotlib.pyplot as plt

plt.style.use("dark_background")

# Alpaca API credentials
API_KEY = 'PK8TEY3LLKTZ37B952IP'
SECRET_KEY = 'vtT1nDJaAlKFGrsXozNAbmFFtur1vqOjQoxMn1VO'
BASE_URL = 'https://paper-api.alpaca.markets'

# Initialize the Alpaca API
api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL, api_version='v2')

while True:
    # Strategy parameters
    ma_1 = 5
    ma_2 = 20

    # Get the current date and time
    now = dt.datetime.now()

    # Set the start and end dates for data retrieval
    start = now - dt.timedelta(days=365 * 4)    
    end = now

    #  Download historical data from Yahoo Finance
    data = yf.download('SOXL', start=start, end=end)

    # Calculate moving averages
    data[f'SMA_{ma_1}'] = data['Adj Close'].rolling(window=ma_1).mean()
    data[f'SMA_{ma_2}'] = data['Adj Close'].rolling(window=ma_2).mean()

    # Generate buy and sell signals
    data = data.iloc[ma_2:]

    buy_signals = [np.nan]  # Add initial nan value
    sell_signals = [np.nan]  # Add initial nan value
    trigger = 0
    position = 0  # Current position (0: flat, 1: long, -1: short)
    order_ids = []  # List to track order IDs

    for x in range(1, len(data)):
        if (
            data[f'SMA_{ma_1}'].iloc[x] > data[f'SMA_{ma_2}'].iloc[x] and
            data[f'SMA_{ma_1}'].iloc[x - 1] < data[f'SMA_{ma_2}'].iloc[x - 1] and
            position != 1
        ):
            buy_signals.append(data['Adj Close'].iloc[x])
            sell_signals.append(np.nan)
            position = 1
            # Place a buy order using Alpaca API
            order = api.submit_order(
                symbol='SOXL',
                qty=1,  # Number of shares to buy
                side='buy',
                type='market',
                time_in_force='gtc'
            )
            order_ids.append(order.id)
            # Set position to 0 to prevent short positions
            position = 0
        else:
            buy_signals.append(np.nan)
            sell_signals.append(np.nan)

    # Calculate strategy returns
    data['Position'] = np.where(~np.isnan(buy_signals[x]), 1, np.where(data['Sell Signals'].notnull(), 0, np.nan))
    data['Position'] = data['Position'].ffill().fillna(0)
    data['Market Return'] = data['Adj Close'].pct_change()
    data['Strategy Return'] = data['Market Return'] * data['Position']
    data['Cumulative Returns'] = (data['Strategy Return'] + 1).cumprod() * 1000  # Starting portfolio value: $1000
    ending_portfolio_value = data['Cumulative Returns'].iloc[-1]

    # Calculate alpha, beta, and Sharpe ratio
    risk_free_rate = 0  # Assuming risk-free rate as 0%

    benchmark_returns = data['Market Return'].dropna()
    strategy_returns = data['Strategy Return'].dropna()

    benchmark_excess_returns = benchmark_returns - risk_free_rate
    strategy_excess_returns = strategy_returns - risk_free_rate

    beta, alpha = np.polyfit(benchmark_excess_returns, strategy_excess_returns, deg=1)
    cumulative_returns = data['Cumulative Returns'].iloc[-1]
    sharpe_ratio = np.sqrt(252) * np.mean(strategy_returns) / np.std(strategy_returns)

    print("Alpha:", alpha)
    print("Beta:", beta)
    print("Cumulative Returns:", cumulative_returns)
    print("Sharpe Ratio:", sharpe_ratio)
    print("Ending Portfolio Value:", ending_portfolio_value)

    plt.plot(data['Adj Close'], label="Share Price", alpha=0.5)
    plt.plot(data[f'SMA_{ma_1}'], label=f"SMA_{ma_1}", color="aqua", linestyle="--")
    plt.plot(data[f'SMA_{ma_2}'], label=f"SMA_{ma_2}", color="lime", linestyle="--")
    plt.scatter(data.index, buy_signals, label="Buy Signal", marker="^", color="#00ff00", linewidths=3)
    plt.scatter(data.index, data['SellSignals'], label="Sell Signal", marker="v", color="#ff0000", linewidths=3)
    plt.legend(loc="upper left")
    plt.show()

    current_price = data['Adj Close'].iloc[-1]  # Assuming current price is the last price in the data

    # Execute buy orders and print executed orders
    executed_buy_orders = []
    for order_id in order_ids:
        order = api.get_order_by_client_order_id(order_id)
        if order.side == 'buy' and order.status == 'filled':
            executed_buy_orders.append(order)
            print("Executed Buy Order:")
            print("Symbol:", order.symbol)
            print("Price:", order.filled_avg_price)
            print("Quantity:", order.filled_qty)
            print("Order ID:", order.id)
            print()

    # Clear order_ids list
    order_ids = []
