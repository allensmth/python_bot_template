import pandas as pd
from datetime import datetime
from typing import Optional
import talib
from bot.risk_management import calculate_lot_size
from models.individual_strategy import IndividualStrategy
from models.signal_decision import SignalDecision
from db import DataDB


# Function to articulate run_strategy
def run_strategy(
    candle_data: pd.DataFrame,
    symbol: str,
    strategy: IndividualStrategy,
    log_message: callable,
    log_to_error: callable,
) -> Optional[SignalDecision]:
    try:
        log_message(f"run_strategy: running copy signal", symbol)

        # 从db读取信号
        db = DataDB()
        db.connect()

        # Fetch the unhandled signal
        signal = get_unhandled_signal(db, symbol)

        # 如果signal存在，返回SignalDecision对象
        if signal:
            # 如果查询得到signal的price和当前价格差距不大,小于atr的1/2那么操作，如果signal的创建时间差距在15分钟内，那么操作
            atr15 = talib.ATR(candle_data['High'], candle_data['Low'], candle_data['Close'], timeperiod=15).iloc[-1]
            #如果sinal的操作是market，那么直接操作
            if signal['order_type'] == 'BUY_MARKET' or signal['order_type'] == 'SELL_MARKET':
                if abs(signal['price'] - candle_data['Close'].iloc[-1]) < atr15 * 5 and (datetime.now() - signal['created_at']).seconds < 15 * 60:
                    #计算sl

                    # 如果是买单，sl是过去180根k线的最低价 再减去atr的1/2
                    
                    sl = 0
                    if signal['order_type'] == 'BUY_MARKET':
                        sl = candle_data['Low'].iloc[-180:].min() - atr15
                    elif signal['order_type'] == 'SELL_MARKET':
                        sl = candle_data['High'].iloc[-180:].max() + atr15 
                    else:
                        mark_signal_as_handled(db, signal)
                        db.close()
                        return None

                    signal_decision = SignalDecision(
                        signal=signal['signal'],
                        symbol=signal['symbol'],
                        order_type=signal['order_type'],
                        current_price=candle_data['Close'].iloc[-1],
                        volume=None,
                        risk=strategy.risk,
                        take_profit=None,
                        stop_loss=sl,
                        signal_timestamp=datetime.now()
                    )

                    log_message(f"run_strategy: Signal generated for {symbol}: {signal_decision}", symbol)
                    mark_signal_as_handled(db, signal)
                    db.close()
                    return signal_decision
        db.close()
        return None  # No trade signal generated

    except Exception as error:
        log_to_error(f"run_strategy: Failed running strategy for {symbol}")
        log_to_error(error)
        raise error

def mark_signal_as_handled(db, signal):
    if signal:
            # 标识为handled为true, 同时更新order_info
        update_query = """
            UPDATE t_signal
            SET handled = true, handled_time = NOW(), order_info = %s
            WHERE id = %s
            """
        db.query_single(update_query, (signal['order_info'], signal['id'],))
        print(f"Signal handled: {signal}")

def get_unhandled_signal(db: DataDB, symbol: str) -> Optional[dict]:
        # 查询当前symbol的handled为false的第一条数据
        signal_query = """
            SELECT * FROM t_signal
            WHERE symbol = %s AND handled = false
            ORDER BY created_at ASC
            LIMIT 1
        """
        return db.query_single(signal_query, (symbol,))
        