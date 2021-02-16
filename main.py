from datetime import timedelta, datetime, date
import pandas as pd
import numpy as np
import gzip
import shutil
import requests
from collections import defaultdict
from heapq import heappush, heappop
import time
from Strategy import Strategy
from Exchange import Exchange
from DataReader import DataReader
from Trade import Trade
from Order import Order

if __name__ == "__main__":
    # read data from bitmex markett
    dr_test = DataReader('Bitmex')
    dr_test.read_data('2020-08-08','2020-08-08')
    # start backtest
    start = time.time()
    start_time = datetime(2020,8,8,0)
    end_time = datetime(2020,8,8,23,59,59)
    exchange = Exchange('Bitmex', 'XBTUSD', 0.5,
                         start_time, end_time, delay = timedelta(milliseconds = 100),
                         path = './')
    s1 = Strategy(exchange)
    s1.start_backtest()
    
    print("--- %s seconds ---" % (time.time() - start))
    # backtest result and time will be reported
    # more attributes like PNL graphs is underdevelopment