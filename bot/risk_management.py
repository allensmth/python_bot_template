from api.metatrader_api import MT5
import constants.defs as defs
import decimal

from models.signal_decision import SignalDecision

def calculate_lot_size(mt5: MT5, signal_decision: SignalDecision, log_message: callable, log_to_error: callable):
    log_message('calculate_lot_size:', signal_decision.symbol)
    
    symbol_info = mt5.mt5.symbol_info(signal_decision.symbol)
    
    pip_value = symbol_info.trade_tick_value
    volume_step = symbol_info.volume_step
    
    if signal_decision.signal == 1:
        price = symbol_info.ask
    elif signal_decision.signal == -1:
        price = symbol_info.bid
    
    trade_multiper = symbol_info.trade_tick_size
    num_pips = (abs(signal_decision.current_price - signal_decision.stop_loss) / trade_multiper)

    balance = mt5.mt5.account_info().balance
    risk_amt = signal_decision.risk * balance
    
    # 获取所有已经开仓的交易

    open_positions = mt5.positions_get()
    total_risk = 0

    for position in open_positions:
        if position.symbol == signal_decision.symbol:
            position_pips = abs(position.price_open - position.sl) / trade_multiper
            position_risk = position.volume * position_pips * pip_value
            total_risk += position_risk

    # 将当前交易的风险加入总风险中
    total_risk += risk_amt

    # Volume 
    d_v = decimal.Decimal(str(volume_step))
    d_v = abs(d_v.as_tuple().exponent)
    
    # Multiplier
    d_p = decimal.Decimal(str(trade_multiper))
    d_p = abs(d_p.as_tuple().exponent)
    
    units = round(total_risk / (num_pips * pip_value), d_v)
    
    return units, trade_multiper, d_p