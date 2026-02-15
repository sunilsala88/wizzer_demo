
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

print('print first list')

logging.info("logging first Strategy execution started")
print('this line is written in wizzer')
strategy_name = "supertrend_ema_strategy"
print(strategy_name, 'started')

# Get current UTC time
dt_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
print("Current time in IST:", dt_ist.strftime("%Y-%m-%d %H:%M:%S"))

while True:
    time.sleep(30)
    dt_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    print("Current time in IST:", dt_ist.strftime("%Y-%m-%d %H:%M:%S"))