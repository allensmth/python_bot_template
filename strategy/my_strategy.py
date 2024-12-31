import pandas as pd
from datetime import datetime
from typing import Optional
import talib
from bot.risk_management import calculate_lot_size
from models.individual_strategy import IndividualStrategy
from models.signal_decision import SignalDecision

# Function to articulate run_strategy
def run_strategy(
    candle_data: pd.DataFrame,
    symbol: str,
    strategy: IndividualStrategy,
    log_message: callable,
    log_to_error: callable,
) -> Optional[SignalDecision]:
    try:
        log_message(f"run_strategy: running strategy analysis", symbol)

        # Initialize variables
        signal = 0
        sl = 0  # Stop Loss
        tp = 0  # Take Profit
        

        # Calculate short and long SMAs based on the trade settings
        short_sma = candle_data['Close'].rolling(window=5).mean()
        long_sma = candle_data['Close'].rolling(window=20).mean()

        # 先决定趋势方向，如果1H的短期均线大于长期均线，说明是上涨趋势，如果1H的短期均线小于长期均线，说明是下跌趋势
        trend = 0
        if short_sma.iloc[-1] > long_sma.iloc[-1]:
            trend = 1  # Uptrend
        elif short_sma.iloc[-1] < long_sma.iloc[-1]:
            trend = -1  # Downtrend
        else:
            trend = 0  # No clear trend

        # 计算价格区间，取过去24*4根K线的最高价和最低价
        max_price = candle_data['High'].iloc[-24*4:].max()
        min_price = candle_data['Low'].iloc[-24*4:].min()

        # 计算target_price，如果是上涨趋势，target_price是最高价，如果是下跌趋势，target_price是最低价
        target_price = 0
        if trend == 1:
            target_price = max_price
        elif trend == -1:
            target_price = min_price
        
        # 计算当前的candle
        talib.CDLENGULFING(candle_data['Open'], candle_data['High'], candle_data['Low'], candle_data['Close'])


        # Check for buy or sell signals
        if short_sma.iloc[-1] > long_sma.iloc[-1]:
            signal = 1  # Buy signal
            order_type = "BUY_STOP"
            sl = candle_data['Low'].min()  # Example stop loss: Lowest price in the dataset
            tp = candle_data['Close'].iloc[-1] + (candle_data['Close'].iloc[-1] - sl) * strategy.profit_ratio  # Take profit calculation
        elif short_sma.iloc[-1] < long_sma.iloc[-1]:
            signal = -1  # Sell signal
            order_type = "SELL_STOP"
            sl = candle_data['High'].max()  # Example stop loss: Highest price in the dataset
            tp = candle_data['Close'].iloc[-1] - (sl - candle_data['Close'].iloc[-1]) * strategy.profit_ratio  # Take profit calculation

        # If a signal is generated, return a SignalDecision object
        if signal != 0:
            signal_decision = SignalDecision(
                signal=signal,
                symbol=symbol,
                order_type=order_type,
                current_price=candle_data['Close'].iloc[-1],
                volume=None,
                risk=strategy.risk,
                take_profit=tp,
                stop_loss=sl,
                signal_timestamp=datetime.now()
            )
            
            log_message(f"run_strategy: Signal generated for {symbol}: {signal_decision}", symbol)
            return signal_decision

        log_message(f"run_strategy: completed strategy analysis, no signal generated", symbol)
        return None  # No trade signal generated

    except Exception as error:
        log_to_error(f"run_strategy: Failed running strategy for {symbol}")
        log_to_error(error)
        raise error