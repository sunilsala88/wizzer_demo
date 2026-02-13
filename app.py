# Supertrend and EMA Strategy
# Calculate the Supertrend on daily candles.
# Calculate the EMA (Exponential Moving Average) on hourly candles.
# Go Long:When the daily Supertrend gives a long signal and the closing price is greater than the daily EMA.
# Go Short:When the daily Supertrend gives a short signal.The closing price is less than the daily EMA.


import pandas as pd
import datetime as dt

import time
print('first line')
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

print(list_of_stocks)
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



import logging
strategy_name = "supertrend_ema_strategy"
logging.basicConfig(level=logging.INFO, filename=f"{strategy_name}.log",filemode='a',format="%(asctime)s - %(message)s")
logging.getLogger('ib_async').setLevel(logging.CRITICAL)
logging.info("Strategy execution started")
while True:
    # if dt.datetime.now() > end_time:
    #     break
    ct = dt.datetime.now()
    logging.info(f"Current time: {ct}")
    print(f"Current time: {ct}")
    time.sleep(60)
    
    # # Execute strategy at the start of each time frame
    # if ct.second in range(1, 3) and ct.minute % time_frame == 0:
    #     print(f"\n{'='*70}")
    #     print(f"Executing strategy at {ct}")
    #     print(f"{'='*70}")
    #     try:
    #         main_strategy()
    #     except Exception as e:
    #         print(f"Error in main_strategy execution: {e}")
    #         import traceback
    #         traceback.print_exc()
    # time.sleep(1)

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