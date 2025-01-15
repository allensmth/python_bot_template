import math
import pandas as pd
import MetaTrader5 as mt5
import pytz
import logging
import time

import datetime as dt

import constants.credentials as credentials
import constants.defs as defs

class MT5:
    MAX_LOGIN_ATTEMPTS = 3  # Define the max number of login attempts
    RETRY_DELAY = 5  # Delay in seconds before retrying the login

    ORDER_TYPE_BUY = mt5.ORDER_TYPE_BUY
    ORDER_TYPE_SELL = mt5.ORDER_TYPE_SELL

    def __init__(self) -> None:
        logging.basicConfig(level=logging.INFO) 
        self.mt5 = mt5
        
    def attempt_login(self) -> bool:
        """Attempts to log in to the MT5 account with retry logic."""
        for attempt in range(1, self.MAX_LOGIN_ATTEMPTS + 1):
            if self.login():
                logging.info(f"Connected to account #{credentials.ACCOUNT_ID}")
                return True
            else:
                error_code = self.mt5.last_error()
                logging.error(f"Login attempt {attempt} failed for account #{credentials.ACCOUNT_ID}, error code: {error_code}")
                
                if attempt < self.MAX_LOGIN_ATTEMPTS:
                    logging.info(f"Retrying login in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)
                else:
                    logging.error(f"Max login attempts reached. Unable to connect to account #{credentials.ACCOUNT_ID}.")
                    return False
        
        return False
    
    def login(self) -> bool:
        """Logs in to the MetaTrader 5 account."""
        if not self.mt5.initialize(path=defs.METATRADER_PATH):
            logging.error(f"Failed to initialize MetaTrader 5, error: {self.mt5.last_error()}")
            return False

        authorized = self.mt5.login(
            credentials.ACCOUNT_ID,
            password=credentials.ACCOUNT_PASSWORD,
            server=credentials.ACCOUNT_SERVER
        )
        
        if authorized:
            return True
        else:
            logging.error(f"Login failed for account #{credentials.ACCOUNT_ID}, error code: {self.mt5.last_error()}")
            return False

    def configure_df(self, hist_data):
        hist_data_df = pd.DataFrame(hist_data)
        hist_data_df.time = pd.to_datetime(hist_data_df.time, unit="s")
        hist_data_df.rename(
            columns={
                "time": "Time",
                "open": "Open",
                "high": "High",
                "close": "Close",
                "low": "Low",
                "tick_volume": "Volume",
                "real_volume": "_Volume",
                "spread": "Spread",
            },
            inplace=True,
        )

        return hist_data_df
    def get_account_info(self):
        """Fetch and display account information."""
        account_info = mt5.account_info()
        if account_info is None:
            logging.error("Failed to get account info")
            return None

        account_info_dict = account_info._asdict()

        return account_info_dict
    # Function to place a trade on MT5
    def place_order(
        self,
        order_type,
        symbol,
        volume,
        price,
        stop_loss,
        take_profit,
        comment,
        log_message,
        log_to_error,
    ):
        try:
            # If order type SELL_STOP
            if order_type == "SELL_STOP":
                order_type = self.mt5.ORDER_TYPE_SELL_STOP
            elif order_type == "BUY_STOP":
                order_type = self.mt5.ORDER_TYPE_BUY_STOP
            elif order_type == "BUY_MARKET":
                order_type = self.mt5.ORDER_TYPE_BUY
            elif order_type == "SELL_MARKET":
                order_type = self.mt5.ORDER_TYPE_SELL
            elif order_type == "BUY_LIMIT":
                order_type = self.mt5.ORDER_TYPE_BUY_LIMIT
            elif order_type == "SELL_LIMIT":
                order_type = self.mt5.ORDER_TYPE_SELL_LIMIT
    
            
            
           
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                raise ValueError(f"Could not get symbol info for {symbol}")
            
            # Get price precision and volume step
            price_precision = symbol_info.digits
            volume_step = symbol_info.volume_step
            
            # Round values to correct precision
            price = round(price, price_precision)
            stop_loss = round(stop_loss, price_precision) if stop_loss else None
            take_profit = round(take_profit, price_precision) if take_profit else None
            volume = round(volume, int(-math.log10(volume_step)))

            
            if order_type == self.mt5.ORDER_TYPE_BUY or order_type == self.mt5.ORDER_TYPE_SELL:
                # Get symbol's minimum stop level and point value
                min_stop_level = symbol_info.trade_stops_level
                point_value = symbol_info.point
                
                # Calculate minimum allowed distance
                min_distance = min_stop_level * point_value
                
                # Validate stop loss
                if stop_loss:
                    current_sl_distance = abs(price - stop_loss)
                    if current_sl_distance < min_distance:
                        # Adjust SL to minimum allowed distance
                        stop_loss = price - min_distance if order_type == self.mt5.ORDER_TYPE_BUY else price + min_distance
                        stop_loss= None
                  
                
                # Validate take profit
                if take_profit:
                    current_tp_distance = abs(price - take_profit)
                    if current_tp_distance < min_distance:
                        # Adjust TP to minimum allowed distance
                        take_profit = None
                
            deviation = 100
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": deviation,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            print(f"palce_order: {request}")

            # Send the order to MT5
            order_result = self.mt5.order_send(request)

            # Notify based on return outcomes
            if order_result[0] == 10009:
                log_message(
                    f"metatrader_api.place_order(): Order for {symbol} successful",
                    symbol,
                )
            else:
                log_message(
                    f"Error placing order. ErrorCode {order_result[0]}, Error Details: {order_result}",
                    symbol,
                )
                log_to_error(
                    f"Error placing order. {symbol} ErrorCode {order_result[0]}, Error Details: {order_result}"
                )

            return order_result
        except Exception as error:
            log_message(f"Error placing order {error}", symbol)
            log_to_error(
                f"metatrader_api.place_order(): Error placing order symbol: {error}"
            )

            raise error

    # Function to convert a timeframe string in MetaTrader 5 friendly format
    def set_query_timeframe(self, timeframe):
        # Implement a Pseudo Switch statement. Note that Python 3.10 implements match / case but have kept it this way for
        # backwards integration
        if timeframe == "S20" or timeframe == "M1":  # S20 maps to M1 since MT5 doesn't support seconds
            return mt5.TIMEFRAME_M1
        elif timeframe == "M2":
            return mt5.TIMEFRAME_M2
        elif timeframe == "M3":
            return mt5.TIMEFRAME_M3
        elif timeframe == "M4":
            return mt5.TIMEFRAME_M4
        elif timeframe == "M5":
            return mt5.TIMEFRAME_M5
        elif timeframe == "M6":
            return mt5.TIMEFRAME_M6
        elif timeframe == "M10":
            return mt5.TIMEFRAME_M10
        elif timeframe == "M12":
            return mt5.TIMEFRAME_M12
        elif timeframe == "M15":
            return mt5.TIMEFRAME_M15
        elif timeframe == "M20":
            return mt5.TIMEFRAME_M20
        elif timeframe == "M30":
            return mt5.TIMEFRAME_M30
        elif timeframe == "H1":
            return mt5.TIMEFRAME_H1
        elif timeframe == "H2":
            return mt5.TIMEFRAME_H2
        elif timeframe == "H3":
            return mt5.TIMEFRAME_H3
        elif timeframe == "H4":
            return mt5.TIMEFRAME_H4
        elif timeframe == "H6":
            return mt5.TIMEFRAME_H6
        elif timeframe == "H8":
            return mt5.TIMEFRAME_H8
        elif timeframe == "H12":
            return mt5.TIMEFRAME_H12
        elif timeframe == "D1":
            return mt5.TIMEFRAME_D1
        elif timeframe == "W1":
            return mt5.TIMEFRAME_W1
        elif timeframe == "MN1":
            return mt5.TIMEFRAME_MN1
    
    # Function to cancel an order
    def cancel_order(self, order_number):
        # Create the request
        request = {
            "action": self.mt5.TRADE_ACTION_REMOVE,
            "order": order_number,
            "comment": "Order Removed",
        }
        # Send order to MT5
        order_result = self.mt5.order_send(request)
        return order_result

    # Function to modify an open position
    def modify_position(self, order_number, stop_loss, take_profit=None):
        """Modifies an open position with new stop loss and take profit values."""
        request = {
            "action": self.mt5.TRADE_ACTION_SLTP,
            "position": order_number,
            "sl": stop_loss,
        }
        if take_profit is not None:
            request["tp"] = take_profit
 
        order_result = self.mt5.order_send(request)

        if order_result[0] == 10009:
            return True
        else:
            return False

    def fetch_candles(
        self,
        symbol: str,
        mt5_timeframe: str,
        log_to_error: callable,
        count: int = 200,
    ) -> pd.DataFrame:
        try:
            # Set the correct timeframe for MT5 query
            mt5_timeframe = self.set_query_timeframe(mt5_timeframe)
            hist_data = self.mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
            if hist_data is None or len(hist_data) == 0:
                raise ValueError(f"No data returned for {symbol} in {mt5_timeframe}")
            
            # Convert to DataFrame and configure it
            hist_data_df = self.configure_df(hist_data)
            return hist_data_df
        except Exception as error:
            # Log detailed error message
            log_to_error(f"Error: fetch_candles failed for {symbol} in {mt5_timeframe}. Error: {error}")
            return pd.DataFrame()  # Return an empty DataFrame on failure

    # Function to query previous candlestick data from MT5
    def query_historic_data(self, symbol, number_of_candles, granularity):
        # Convert the timeframe into an MT5 friendly format
        mt5_timeframe = self.set_query_timeframe(granularity)
             # Retrieve data from MT5
        rates = self.mt5.copy_rates_from_pos(
            symbol, mt5_timeframe, 0, number_of_candles
        )

        return rates

    # Function to retrieve all open orders from MT5
    def get_open_orders(self):
        orders = self.mt5.orders_get()
        order_array = []
        for order in orders:
            order_array.append(order[0])
        return order_array

    # Function to retrieve all open positions
    def get_open_positions(self):
        # Get position objects
        positions = self.mt5.positions_get()
        # Return position objects
        return positions

    # Function to partially close an open position
    def get_closed_trades_today(self):
        """Returns all trades closed today."""
        timezone = pytz.timezone("Etc/UTC")
        today = dt.datetime.now(timezone).replace(hour=0, minute=0, second=0, microsecond=0)
        deals = self.mt5.history_deals_get(today, dt.datetime.now(timezone))
        
        if deals is None:
            return []
            
        return [deal for deal in deals if deal.profit < 0]  # Only return losing trades

    def partial_close_position(self, ticket, volume):
        """Closes a part of an open position."""
        position = self.mt5.positions_get(ticket=ticket)
        if not position:
            logging.error(f"Position with ticket #{ticket} not found")
            return None

        symbol = position[0].symbol
        order_type = position[0].type  # 0 for buy, 1 for sell
        
        if order_type == self.mt5.ORDER_TYPE_BUY:
            trade_type = self.mt5.ORDER_TYPE_SELL
            price = self.mt5.symbol_info_tick(symbol).bid
        else:
            trade_type = self.mt5.ORDER_TYPE_BUY
            price = self.mt5.symbol_info_tick(symbol).ask
        
        deviation = 200
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": trade_type,
            "position": ticket,
            "price": price,
            "deviation": deviation,
            "magic": 234000,
            "comment": "partial close",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_FOK,
        }
        
        print(f"partial_close_position: {request}")
        order_result = self.mt5.order_send(request)

        if order_result[0] == 10009:
            logging.info(f"Partial close for ticket #{ticket} successful")
            return order_result
        else:
            logging.error(f"Error partially closing ticket #{ticket}. ErrorCode: {order_result[0]}, Error Details: {order_result}")
            return None

    def get_closed_deals(self):
        """Retrieves all trades closed today."""
        timezone = pytz.timezone("Etc/UTC")
        utc_from = dt.datetime.now(timezone).replace(hour=0, minute=0, second=0, microsecond=0)
        utc_to = dt.datetime.now(timezone).replace(hour=23, minute=59, second=59, microsecond=999)
        
        # Request orders in the specified time range
        closed_deals = self.mt5.history_deals_get(utc_from, utc_to)
        return closed_deals

    def symbol_info(self, symbol):
        """Fetch symbol information."""
        return self.mt5.symbol_info(symbol)
