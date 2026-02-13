# Supertrend and EMA Strategy
# Calculate the Supertrend on daily candles.
# Calculate the EMA (Exponential Moving Average) on hourly candles.
# Go Long:When the daily Supertrend gives a long signal and the closing price is greater than the daily EMA.
# Go Short:When the daily Supertrend gives a short signal.The closing price is less than the daily EMA.


import pandas as pd
import datetime as dt
import pandas_ta as ta
import time

api='z59mkhj6yg8b6c81'
secret='vd00dbutmiskmpelwfqf4o51s074d72h'
access_token='RmlX1MokZPOj0ZN7d7Ptl0J4VqbE23ye'

from kiteconnect import KiteConnect
kite = KiteConnect(api_key=api)
kite.set_access_token(access_token)




list_of_stocks=['RELIANCE','HDFCBANK','ONGC']
exchange='NSE'


def get_token(stock_name, exchange="NSE"):
    """Returns instrument token for a given stock name and exchange."""
    instruments = kite.instruments()
    for inst in instruments:
        if inst['tradingsymbol'] == stock_name and inst['exchange'] == exchange:
            return inst['instrument_token']
    return None


list_of_tickers={}
token_to_symbol = {}  # Reverse mapping: token -> symbol

for t in list_of_stocks:
    token = get_token(t, exchange=exchange)
    list_of_tickers.update({t: token})
    token_to_symbol[token] = t  # Add reverse mapping

print(list_of_tickers)
print(f"Token to Symbol mapping: {token_to_symbol}")

#timframe is 1 min
time_frame=1
days=20
start_hour,start_min=9,25
end_hour,end_min=18,15


def get_open_position():
    positions = kite.positions()
    net_positions = positions['net'] if 'net' in positions else []
    if net_positions:
        position_df = pd.DataFrame(net_positions)
    else:
        position_df = pd.DataFrame()
    return position_df

def get_open_orders():
    orders = kite.orders()
    if orders:
        order_df = pd.DataFrame(orders)
    else:
        order_df = pd.DataFrame()
    return order_df


def get_historical_data(ticker,interval,duration):
    """Extracts historical data and outputs in the form of dataframe with indicators."""
    try:
        instrument_token = ticker
        to_date = dt.date.today()
        from_date = to_date - dt.timedelta(days=duration)
        interval_map = {'1': 'minute', '60': '60minute', 'D': 'day'}
        kite_interval = interval_map.get(str(interval), str(interval))
        candles = kite.historical_data(instrument_token, from_date, to_date, kite_interval)
        
        if not candles:
            print(f"No historical data returned for token {ticker}")
            return pd.DataFrame()
            
        sdata = pd.DataFrame(candles)
        sdata['date'] = pd.to_datetime(sdata['date'])
        sdata = sdata.set_index('date')
        
        # Calculate indicators
        sdata['supertrend'] = ta.sma(sdata['close'], length=10)
        sdata['ema'] = ta.ema(sdata['close'], length=20)
        supertrend_df = ta.supertrend(sdata['high'], sdata['low'], sdata['close'], length=10)
        if supertrend_df is not None:
            sdata['super'] = supertrend_df['SUPERTd_10_3.0']
        else:
            sdata['super'] = 0
        sdata['atr'] = ta.atr(sdata['high'], sdata['low'], sdata['close'], length=14)
        
        return sdata
    except Exception as e:
        print(f"Error fetching historical data for token {ticker}: {e}")
        return pd.DataFrame()


def close_all_orders():
    order_df = get_open_orders()
    if not order_df.empty:
        open_orders = order_df[order_df['status'].isin(['OPEN', 'TRIGGER PENDING'])]
        if not open_orders.empty:
            for order_id in open_orders['order_id'].to_list():
                try:
                    response = kite.cancel_order(variety='regular', order_id=order_id)
                    print(response)
                except Exception as e:
                    print(f"Error cancelling order {order_id}: {e}")

def check_market_order_placed(ticker):
    """Check if a market order already exists for this ticker."""
    order_df = get_open_orders()
    if order_df.empty:
        return 1
    
    order_df = order_df[order_df['order_type'] == 'MARKET']
    order_df = order_df[order_df['status'].isin(['OPEN', 'TRIGGER PENDING', 'COMPLETE'])]
    
    if not order_df.empty and (ticker in order_df['instrument_token'].to_list()):
        print(f"Market order already exists for {token_to_symbol.get(ticker, ticker)}")
        return 0
    else:
        return 1

def close_ticker_open_orders(ticker):
    """Cancel all open orders for a specific ticker."""
    order_df = get_open_orders()
    if not order_df.empty:
        open_orders = order_df[order_df['status'].isin(['OPEN', 'TRIGGER PENDING'])]
        if (not open_orders.empty) and (ticker in open_orders['instrument_token'].to_list()):
            ticker_orders = open_orders[open_orders['instrument_token'] == ticker]
            for order_id in ticker_orders['order_id'].to_list():
                try:
                    response = kite.cancel_order(variety='regular', order_id=order_id)
                    print(f"Cancelled order {order_id} for {token_to_symbol.get(ticker, ticker)}: {response}")
                except Exception as e:
                    print(f"Error cancelling order {order_id}: {e}")
        else:
            print(f'No open orders to close for {token_to_symbol.get(ticker, ticker)}')


def close_ticker_position(ticker):
    """Close an open position for given instrument token."""
    position_df = get_open_position()
    if (not position_df.empty) and (ticker in position_df['instrument_token'].to_list()):
        try:
            pos_row = position_df[position_df['instrument_token'] == ticker].iloc[0]
            response = kite.exit_position(
                exchange=pos_row['exchange'],
                tradingsymbol=pos_row['tradingsymbol'],
                transaction_type='SELL' if pos_row['quantity'] > 0 else 'BUY',
                quantity=abs(pos_row['quantity']),
                order_type='MARKET',
                product=pos_row['product']
            )
            print(f"Position closed for {token_to_symbol.get(ticker, ticker)}: {response}")
        except Exception as e:
            print(f"Error closing position for {token_to_symbol.get(ticker, ticker)}: {e}")
    else:
        print(f'Position does not exist for {token_to_symbol.get(ticker, ticker)}')
 


def trade_sell_stocks(instrument_token,stock_price,stop_price,quantity=1):
    """Place sell order using instrument token. Converts token to trading symbol."""
    stock_name = token_to_symbol.get(instrument_token)
    if not stock_name:
        print(f"Error: Trading symbol not found for token {instrument_token}")
        return
    
    if check_market_order_placed(instrument_token):
        try:
            order_id = kite.place_order(
                variety='regular',
                exchange='NSE',
                tradingsymbol=stock_name,
                transaction_type='SELL',
                quantity=int(quantity),
                order_type='MARKET',
                product='MIS',
                validity='DAY'
            )
            print(f"Sell market order placed: {order_id} for {stock_name}")
            # Place stop-loss order
            sl_order_id = kite.place_order(
                variety='regular',
                exchange='NSE',
                tradingsymbol=stock_name,
                transaction_type='BUY',
                quantity=int(quantity),
                order_type='SL',
                price=stop_price,
                trigger_price=stop_price,
                product='MIS',
                validity='DAY'
            )
            print(f"Stop-loss order placed: {sl_order_id} for {stock_name}")
        except Exception as e:
            print(f"Error placing sell/SL order for {stock_name}: {e}")


def trade_buy_stocks(instrument_token,stock_price,stop_price,quantity=1):
    """Place buy order using instrument token. Converts token to trading symbol."""
    stock_name = token_to_symbol.get(instrument_token)
    if not stock_name:
        print(f"Error: Trading symbol not found for token {instrument_token}")
        return
    
    if check_market_order_placed(instrument_token):
        try:
            order_id = kite.place_order(
                variety='regular',
                exchange='NSE',
                tradingsymbol=stock_name,
                transaction_type='BUY',
                quantity=int(quantity),
                order_type='MARKET',
                product='MIS',
                validity='DAY'
            )
            print(f"Buy market order placed: {order_id} for {stock_name}")
            # Place stop-loss order
            sl_order_id = kite.place_order(
                variety='regular',
                exchange='NSE',
                tradingsymbol=stock_name,
                transaction_type='SELL',
                quantity=int(quantity),
                order_type='SL',
                price=stop_price,
                trigger_price=stop_price,
                product='MIS',
                validity='DAY'
            )
            print(f"Stop-loss order placed: {sl_order_id} for {stock_name}")
        except Exception as e:
            print(f"Error placing buy/SL order for {stock_name}: {e}")


def strategy_condition(hist_df_hourly,hist_df_daily,ticker):
    """Check strategy conditions and place trades. ticker is instrument_token."""
    symbol_name = token_to_symbol.get(ticker, 'Unknown')
    print(f'inside strategy conditional code for {symbol_name} (token: {ticker})')
    
    buy_condition = hist_df_hourly['super'].iloc[-1] > 0 and hist_df_daily['ema'].iloc[-1] < hist_df_hourly['close'].iloc[-1]
    sell_condition = hist_df_hourly['super'].iloc[-1] < 0 and hist_df_daily['ema'].iloc[-1] > hist_df_hourly['close'].iloc[-1]

    funds = kite.margins(segment='equity')
    money = funds['available']['cash'] / 3 if 'available' in funds and 'cash' in funds['available'] else 0
    print(f"Available money: {money}")
    hourly_closing_price = hist_df_hourly['close'].iloc[-1]
    atr_value = hist_df_daily['atr'].iloc[-1]
    
    # Calculate quantity based on available money
    quantity = int(money / hourly_closing_price) if hourly_closing_price > 0 else 0
    print(f"Calculated quantity: {quantity}")

    if quantity >= 1:
        if buy_condition:
            print(f'buy condition satisfied for {symbol_name}')
            trade_buy_stocks(ticker, hourly_closing_price, hourly_closing_price - atr_value, quantity)
        elif sell_condition:
            print(f'sell condition satisfied for {symbol_name}')
            trade_sell_stocks(ticker, hourly_closing_price, hourly_closing_price + atr_value, quantity)
        else:
            print('no condition satisfied')
    else:
        print(f'we dont have enough money to trade {symbol_name}')




def main_strategy():
    """Main strategy execution loop."""
    try:
        pos_df = get_open_position()
        ord_df = get_open_orders()
        print(f"\n{'='*50}")
        print(f"Current Positions: {len(pos_df)}")
        print(f"Current Orders: {len(ord_df)}")
        print(f"{'='*50}\n")

        for ticker in list_of_tickers.values():
            symbol_name = token_to_symbol.get(ticker, ticker)
            print(f"\n--- Processing {symbol_name} (Token: {ticker}) ---")
            
            # Fetch historical data
            hist_df = get_historical_data(ticker, f'{time_frame}', days)
            hist_df_hourly = get_historical_data(ticker, '60', 10)
            hist_df_daily = get_historical_data(ticker, 'D', 50)
            
            # Validate data
            if hist_df.empty or hist_df_hourly.empty or hist_df_daily.empty:
                print(f"Skipping {symbol_name}: insufficient historical data")
                continue
                
            if len(hist_df_hourly) < 2 or len(hist_df_daily) < 2:
                print(f"Skipping {symbol_name}: not enough data points")
                continue

            # Check available funds and calculate quantity
            funds = kite.margins(segment='equity')
            money = funds['available']['cash'] / 3 if 'available' in funds and 'cash' in funds['available'] else 0
            hourly_closing_price = hist_df_hourly['close'].iloc[-1]
            quantity = int(money / hourly_closing_price) if hourly_closing_price > 0 else 0
            print(f"Available funds: {money:.2f}, Price: {hourly_closing_price:.2f}, Qty: {quantity}")

            if quantity < 1:
                print(f"Skipping {symbol_name}: insufficient funds for trade")
                continue

            # Check positions and execute strategy
            if pos_df.empty:
                print(f'we dont have any position for {token_to_symbol.get(ticker, ticker)}')
                strategy_condition(hist_df_hourly, hist_df_daily, ticker)
            elif len(pos_df) != 0 and ticker not in pos_df['instrument_token'].to_list():
                print(f'we have some position but {token_to_symbol.get(ticker, ticker)} is not in pos')
                strategy_condition(hist_df_hourly, hist_df_daily, ticker)
            elif len(pos_df) != 0 and ticker in pos_df['instrument_token'].to_list():
                print(f'we have some pos and {token_to_symbol.get(ticker, ticker)} is in pos')
                curr_quant = float(pos_df[pos_df['instrument_token'] == ticker]['quantity'].iloc[-1])
                print(f'Current quantity: {curr_quant}')

                if curr_quant == 0:
                    print('my quantity is 0')
                    strategy_condition(hist_df_hourly, hist_df_daily, ticker)
                elif curr_quant > 0:
                    print(f'we have current ticker in position and is long: {token_to_symbol.get(ticker, ticker)}')
                    sell_condition = hist_df_hourly['super'].iloc[-1] < 0 and hist_df_daily['ema'].iloc[-1] > hist_df_hourly['close'].iloc[-1]
                    if sell_condition:
                        hourly_closing_price = hist_df_hourly['close'].iloc[-1]
                        atr_value = hist_df_daily['atr'].iloc[-1]
                        print('sell condition satisfied - reversing from long to short')
                        close_ticker_open_orders(ticker)
                        time.sleep(1)
                        close_ticker_position(ticker)
                        time.sleep(1)
                        # Calculate quantity for reverse position
                        funds = kite.margins(segment='equity')
                        money = funds['available']['cash'] / 3 if 'available' in funds and 'cash' in funds['available'] else 0
                        reverse_quantity = int(money / hourly_closing_price) if hourly_closing_price > 0 else 0
                        if reverse_quantity >= 1:
                            trade_sell_stocks(ticker, hourly_closing_price, hourly_closing_price + atr_value, reverse_quantity)
                elif curr_quant < 0:
                    print(f'we have current ticker in position and is short: {token_to_symbol.get(ticker, ticker)}')
                    hourly_closing_price = hist_df_hourly['close'].iloc[-1]
                    atr_value = hist_df_daily['atr'].iloc[-1]
                    buy_condition = hist_df_hourly['super'].iloc[-1] > 0 and hist_df_daily['ema'].iloc[-1] < hist_df_hourly['close'].iloc[-1]
                    if buy_condition:
                        print('buy condition satisfied - reversing from short to long')
                        close_ticker_open_orders(ticker)
                        time.sleep(1)
                        close_ticker_position(ticker)
                        time.sleep(1)
                        # Calculate quantity for reverse position
                        funds = kite.margins(segment='equity')
                        money = funds['available']['cash'] / 3 if 'available' in funds and 'cash' in funds['available'] else 0
                        reverse_quantity = int(money / hourly_closing_price) if hourly_closing_price > 0 else 0
                        if reverse_quantity >= 1:
                            trade_buy_stocks(ticker, hourly_closing_price, hourly_closing_price - atr_value, reverse_quantity)
    except Exception as e:
        print(f"Error in main_strategy: {e}")
        import traceback
        traceback.print_exc()
     



current_time = dt.datetime.now()
print(current_time)

start_time = dt.datetime(current_time.year, current_time.month, current_time.day, start_hour, start_min)
end_time = dt.datetime(current_time.year, current_time.month, current_time.day, end_hour, end_min)

print(start_time)
print(end_time)

# pre hour and post hour
while dt.datetime.now() < start_time:
    print(dt.datetime.now())
    time.sleep(1)

print('we have reached start time ')
print('we are running our strategy now')

while True:
    if dt.datetime.now() > end_time:
        break
    ct = dt.datetime.now()
    
    # Execute strategy at the start of each time frame
    if ct.second in range(1, 3) and ct.minute % time_frame == 0:
        print(f"\n{'='*70}")
        print(f"Executing strategy at {ct}")
        print(f"{'='*70}")
        try:
            main_strategy()
        except Exception as e:
            print(f"Error in main_strategy execution: {e}")
            import traceback
            traceback.print_exc()
    time.sleep(1)

print('we have reached end time')

# Close all open positions and orders at the end
print("\n" + "="*50)
print("Closing all positions and orders at end of trading session")
print("="*50)
try:
    positions = get_open_position()
    if not positions.empty:
        for idx, row in positions.iterrows():
            if row['quantity'] != 0:
                try:
                    response = kite.exit_position(
                        exchange=row['exchange'],
                        tradingsymbol=row['tradingsymbol'],
                        transaction_type='SELL' if row['quantity'] > 0 else 'BUY',
                        quantity=abs(row['quantity']),
                        order_type='MARKET',
                        product=row['product']
                    )
                    print(f"Closed position for {row['tradingsymbol']}: {response}")
                except Exception as pos_error:
                    print(f"Error closing position for {row['tradingsymbol']}: {pos_error}")
    else:
        print("No open positions to close")
except Exception as e:
    print(f"Error accessing positions: {e}")

try:
    close_all_orders()
    print("All orders closed successfully")
except Exception as e:
    print(f"Error closing orders: {e}")

print("\nTrading session ended successfully")