# import mt5_interface
# from models.trade_management import TradeSettings

from datetime import datetime as dt

import numpy as np

from bot.risk_management import calculate_lot_size
from utils.utils import get_trade_multipler, get_decimals_places

import time
import datetime as dt
from typing import List

import time
import datetime as dt
from typing import List

class TradeManager:
    def __init__(self, mt5, risk_management, log_to_main, log_message, log_to_error):
        """Initializes the TradeManager with MT5 instance, risk management rules, and logging functions."""
        self.mt5 = mt5  # MT5 instance for trading operations
        self.risk_management = risk_management  # Risk management settings
        self.log_to_main = log_to_main
        self.log_message = log_message  # Function for logging general messages
        self.log_to_error = log_to_error  # Function for logging error messages
        self.is_running = True  # Flag to control the trade monitoring loop
        self.daily_loss = 0  # Track daily loss to stop trading if threshold is met
        
        # Break even points for different symbols
        self.BREAK_EVEN_POINTS = {
            "BTCUSD": 100,
            "NAS100": 50
        }
        
    def close_open_trades(self):
        """Closes all open trades before stopping the bot."""
        self.log_to_main("close_open_trades: Closing all open trades before stopping...", "trade_manager")

        open_trades = self.mt5.get_open_trades()
        for trade in open_trades:
            try:
                # Attempt to close the trade
                self.mt5.close_order(trade.order_id)
                self.log_message(f"close_open_trades: Successfully closed trade for {trade.symbol}", "trade_manager")

            except Exception as error:
                self.log_to_error(f"close_open_trades: Failed to close trade for {trade.symbol}: {error}")
                raise error

    def monitor_open_trades(self):
        """Monitors open trades and adjusts stop-loss or take-profit if necessary."""
        self.log_message("monitor_open_trades: Monitoring open trades...", "trade_manager")

        try:
            open_trades = self.mt5.get_open_trades()  # Fetch open trades
            for trade in open_trades:
                # Get the current market price for the traded symbol
                current_price = self.mt5.get_current_price(trade.symbol)
                # Adjust stop-loss or take-profit based on your strategy
                self.manage_trade(trade, current_price)

        except Exception as error:
            self.log_to_error(f"monitor_open_trades: Critical error while monitoring trades: {error}")
            raise error

    def calculate_stop_loss(self, symbol, order_type):
        """Calculate stop loss based on 180 minutes of historical data"""
        # Get 180 minutes of historical data (30 candles for M5 timeframe)
        candles = self.mt5.get_historical_data(symbol, timeframe="M5", count=30)
        
        if not candles:
            return None
            
        # Calculate candle heights
        heights = [candle.high - candle.low for candle in candles]
        avg_height = sum(heights) / len(heights)
        
        if order_type == "BUY_ORDER":
            # For buy orders: lowest low - average height
            lowest_low = min([candle.low for candle in candles])
            return lowest_low - avg_height
        else:
            # For sell orders: highest high + average height
            highest_high = max([candle.high for candle in candles])
            return highest_high + avg_height

    def manage_trade(self, trade, current_price):
        """Manages an open trade by adjusting stop-loss or take-profit if conditions are met."""
        # Check if stop loss is not set
        if trade.stop_loss is None:
            stop_loss = self.calculate_stop_loss(trade.symbol, trade.order_type)
            if stop_loss:
                self.mt5.modify_order(trade.order_id, stop_loss=stop_loss)
                self.log_message(f"manage_trade: Set initial stop loss for {trade.symbol} at {stop_loss}")

        # Get break even points for the symbol
        break_even_points = self.BREAK_EVEN_POINTS.get(trade.symbol, 100)
        
        if trade.order_type == "BUY_ORDER":
            # Calculate profit in points
            profit_points = (current_price - trade.price_open) * get_trade_multipler(trade.symbol)
            
            # Check if profit reaches break even points
            if profit_points >= break_even_points and trade.stop_loss < trade.price_open:
                # Move stop loss to break even
                self.mt5.modify_order(trade.order_id, stop_loss=trade.price_open)
                self.log_message(f"manage_trade: Moved stop loss to break even for {trade.symbol}")
                if self.risk_management["partial_close"]:
                    partial_close_volume = round(trade.volume / 3, 2)
                    self.partial_close_trade(trade.order_id, partial_close_volume)
            
            # Original trailing stop logic
            if current_price > trade.price_open + self.risk_management["max_stop_loss_percentage"] * trade.price_open:
                new_stop_loss = current_price - self.risk_management["max_stop_loss_percentage"] * trade.price_open
                if new_stop_loss > trade.stop_loss:
                    self.mt5.modify_order(trade.order_id, stop_loss=new_stop_loss)
                    self.log_message(f"manage_trade: Adjusted stop-loss for {trade.symbol} to {new_stop_loss}")

        elif trade.order_type == "SELL_ORDER":
            # Calculate profit in points
            profit_points = (trade.price_open - current_price) * get_trade_multipler(trade.symbol)
            
            # Check if profit reaches break even points
            if profit_points >= break_even_points and trade.stop_loss > trade.price_open:
                # Move stop loss to break even
                self.mt5.modify_order(trade.order_id, stop_loss=trade.price_open)
                self.log_message(f"manage_trade: Moved stop loss to break even for {trade.symbol}")
                if self.risk_management["partial_close"]:
                    partial_close_volume = round(trade.volume / 3, 2)
                    self.partial_close_trade(trade.order_id, partial_close_volume)
            
            # Original trailing stop logic
            if current_price < trade.price_open - self.risk_management["max_stop_loss_percentage"] * trade.price_open:
                new_stop_loss = current_price + self.risk_management["max_stop_loss_percentage"] * trade.price_open
                if new_stop_loss < trade.stop_loss:
                    self.mt5.modify_order(trade.order_id, stop_loss=new_stop_loss)
                    self.log_message(f"manage_trade: Adjusted stop-loss for {trade.symbol} to {new_stop_loss}")

    def close_trade_early(self, trade, current_price):
        """Closes a trade early if it meets specific conditions (e.g., profit threshold)."""
        current_profit = self.mt5.calculate_profit(trade)

        # Example: Close the trade early if it reaches the take-profit ratio
        take_profit_target = self.risk_management["take_profit_ratio"] * (trade.price_open - trade.stop_loss)
        if current_profit >= take_profit_target:
            self.mt5.close_order(trade.order_id)
            self.log_message(f"close_trade_early: Closed trade {trade.symbol} early with profit {current_profit}")

    def check_risk_limits(self, signal_decision):
        """Ensures that the trade meets risk management limits."""
        account_balance = self.mt5.get_account_balance()
        open_trades = self.mt5.get_open_trades()

        # Check the number of concurrent trades
        if len(open_trades) >= self.risk_management["max_concurrent_trades"]:
            self.log_to_error(f"check_risk_limits: Maximum concurrent trades reached. Ignoring new trade for {signal_decision.symbol}.")
            return False

        # Calculate potential risk for this trade
        stop_loss_distance = signal_decision.current_price - signal_decision.stop_loss
        risk_per_trade = stop_loss_distance * signal_decision.volume
        max_risk_per_trade = self.risk_management["max_trade_percentage"] * account_balance

        if risk_per_trade > max_risk_per_trade:
            self.log_to_error(f"check_risk_limits: Risk for {signal_decision.symbol} exceeds allowed maximum. Ignoring trade.")
            return False

        return True

    def track_daily_loss(self):
        """Tracks the bot's daily losses and stops trading if the max daily loss limit is reached."""
        total_loss = sum([trade.loss for trade in self.mt5.get_closed_trades_today()])
        account_balance = self.mt5.get_account_balance()
        max_daily_loss = self.risk_management["max_daily_loss_percentage"] * account_balance

        if total_loss >= max_daily_loss:
            self.log_to_error(f"track_daily_loss: Max daily loss reached. No further trades today.")
            return False  # Stop trading for the day

        return True

    def run_trade_manager(self):
        """Main loop to monitor and manage open trades."""
        self.log_message("run_trade_manager: Running trade manager...", "trade_manager")

        while self.is_running:
            try:
                if self.track_daily_loss():  # Stop trading if daily loss limit is hit
                    self.monitor_open_trades()  # Continuously monitor and manage open trades
            except Exception as e:
                self.log_to_error(f"run_trade_manager: Critical error in trade management: {e}")
            finally:
                time.sleep(5)  # Adjust sleep time as needed to control trade management frequency

    def stop_trade_manager(self):
        """Stops the trade manager process."""
        self.is_running = False
        self.log_message("stop_trade_manager: Trade manager stopped.", "trade_manager")

    def partial_close_trade(self, ticket, volume):
        """Partially closes an open trade."""
        symbol_info = self.mt5.mt5.symbol_info_ticket(ticket)
        if symbol_info is None:
            self.log_error(f"Could not get symbol info for ticket {ticket}")
            return

        volume_step = symbol_info.volume_step
        partial_close_volume = volume / 3

        # Determine the number of decimal places from volume_step
        import decimal
        d_v = decimal.Decimal(str(volume_step))
        decimals = abs(d_v.as_tuple().exponent)

        partial_close_volume = round(partial_close_volume, decimals)

        result = self.mt5.partial_close_position(ticket, partial_close_volume)
        if result:
            self.log_message(f"Partial close of ticket {ticket} with volume {partial_close_volume} successful.")
        else:
            self.log_error(f"Partial close of ticket {ticket} failed.")
