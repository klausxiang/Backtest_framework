from datetime import timedelta, datetime, date
import pandas as pd
import numpy as np
import gzip
import shutil
import requests
from collections import defaultdict
from heapq import heappush, heappop,heapify
import time
import math
import os
import time
from DataReader import DataReader
from Trade import Trade
from Order import Order

class Exchange:
    
    def __init__(self, ex_type, coin, min_tick_size,
                 start_time, end_time, delay = timedelta(milliseconds = 100),
                 path = './'):
        ''' Initiate Exchange of specific ex_type
        Inputs:
            path, request, ex_type: used for getting data, see DataReader
            delay: set to 100ms for delay of trading operations
            start_time, end_time: datetime object specifying start and end of backtest
        '''
        
    
        start_date = start_time.date()
        end_date = end_time.date()
        
        # read data for specific coin type, firstly try read pickle
        # if pickle not exist, try request from web
        try:
            print('Reading data from {}'.format('{}data/{}.pkl'.format(path,coin)))
            self.data = pd.read_pickle('{}data/{}.pkl'.format(path,coin))[start_time:end_time]
        except:
            print('Pickle file does not exist, trying to request data using DataReader:')
            dr = DataReader(ex_type)
            dr.read_data(start_date, end_date, path = path, request = True)
            try:
                print('Request completed, now reading data from {}'.format('{}data/{}.pkl'.format(path,coin)))
                self.data = pd.read_pickle('{}data/{}.pkl'.format(path,coin))[start_time:end_time]
            except:
                raise Exception('Data for {} not avaliable from {}'.format(coin,ex_type))

        # orders: strategies submitted orders that are not yet excuted, currently 1d list: for 1 strategy
        self.orders = {'Buy': [] , 'Sell': []}
        self.order_prices = []
        
        # subscriber: now for convenience just kept 1 strategy, might change later to list of strategies,
        self.subscriber = None
        
        # current_time: current time point of the exchange
        self.current_time = start_time

        self.DELAY = delay
        self.end_time = end_time
        self.last_sell_price = np.inf
        self.last_buy_price = 0
        
        self.coin = coin
        self.timestamps = self.data.index.to_list()
        # heap of (time, order, coin)
        self.queue = [] 
        self.min_tick_size = min_tick_size
        
        
    def add_subscriber(self, subscriber):
        ''' function that add a stratgy to this exchange '''
        # link to strategy: for convenience just kept 1 strategy
        self.subscriber = subscriber
        
        
    def update_prices(self, trade):
        ''' function that update the current price by inputing latest trade
        Input:
            trade: trade object with the size, price, direction info
        '''

        if trade.get_type() == 'Sell':
            self.last_sell_price = trade.get_price()
            
            # check if any order can be excuted
            if self.orders['Buy']:
                while self.orders['Buy']:
                    # get the higheest price buy order
                    price, ID, order = heappop(self.orders['Buy'])
                    # if the higest buy order is not excecuted, break loop
                    if order.get_price() <=  trade.get_price():
                        heappush(self.orders['Buy'],(price, ID, order))
                        break
                    else:
                        self.subscriber.mark_done(order, self.current_time)
           
        else:
            self.last_buy_price = trade.get_price()
            # check if any order can be excuted
            if self.orders['Sell']:
                while self.orders['Sell']:
                    # get the higheest price buy order
                    price, ID, order = heappop(self.orders['Sell'])
                    # if the higest buy order is not excecuted, break loop
                    if order.get_price() >=  trade.get_price():
                        heappush(self.orders['Sell'],(price, ID, order))
                        break
                    else:
                        self.subscriber.mark_done(order, self.current_time)
        
        ''' 
            For one tick report to strategy multiple times (depends on num trade) 
            Comment below if for one tick only report once
        '''
        # update price to strategy for next generation of order placement
        # print('Current bid: {}, Current ask: {}'.format(self.last_sell_price, self.last_buy_price))
        self.subscriber.update_prices(trade)            

        
        
    def update_time(self):
        ''' function that update the current time and update all the trades in this tick'''
        # if there is no more timestamps avaliable, end of backtest
        if not self.timestamps:
            self.current_time = self.end_time
            return
        
        # update time
        ts = self.timestamps.pop(0)
        self.current_time = ts
        
        # check orders in queue and put them into system
        if self.queue:
            while self.queue:
                order_in_queue = heappop(self.queue)
                if order_in_queue[0] > self.current_time:
                    # if it is not excuted put it back to heap
                    heappush(self.queue, order_in_queue)
                    break
                else:
                    time, _, order = order_in_queue
                    # if after delay the order is no longer valid, just cancel it
                    if not self.check_order_price(order):
                        continue
                    # add the pending order to order list
                    # rank it with negative price as we are using a min heap: ie when heappop,
                    # we want to start from highest buy order to compare with sell trades
                    if order.get_type() == 'Buy':
                        heappush(self.orders['Buy'],(-order.get_price(), order.get_ID(),order))
                    elif order.get_type() == 'Sell':
                        # rank it with negative price as we are using a min heap
                        heappush(self.orders['Sell'],(order.get_price(), order.get_ID(),order))
                    else:
                        raise Exception('{} is an invalid order'.format(order.get_ID()))

        # update all trades to update prices
        updates = self.data.loc[ts]
        if isinstance(updates,tuple):
            for trade in updates:
                self.update_prices(trade)
            ''' Uncomment below if for one tick only report to strategy once (the last trade) '''
#             # update price to strategy for next generation of order placement
#             self.subscriber.update_prices(trade)
        else:
            raise Exception('Timestamp {} has invalid trades'.format(ts))
        
        
    
    def start_backtest(self):
        ''' function that starts the backtest from current time to end time'''
        while self.current_time < self.end_time:
            self.update_time()
        print('----------- Backtest finished -----------')
    
    def get_min_tick_size(self):
        ''' function that get min ticksize'''
        return self.min_tick_size
    
    def valid_order(self, order):
        ''' function that check if the input order is valid 
            (convert to closest tick, make sure limit order does not
            become market order when it enter the exchange) 
        Inputs:
            order: order object to be checked
        Outputs:
            checked_order if it is valid, None if not '''
        prc = order.get_price()
        multiplier = prc*(1/self.min_tick_size)
        if multiplier.is_integer():
            return self.check_order_price(order)
        else:
            if order.get_type() == 'Buy':
                # if it is a sell order, round it to closest lower tick
                order.set_price(math.floor(multiplier)*self.min_tick_size)
                return self.check_order_price(order)
            else:
                # if it is a sell order, round it to closest upper tick
                order.set_price(math.ceil(multiplier)*self.min_tick_size)
                return self.check_order_price(order)
            
    def check_order_price(self, order):
        ''' function that check if the input order price is valid 
            (make sure limit order does not become market order when it enter the exchange) 
        Inputs:
            order: order object to be checked
        Outputs:
            checked_order if it is valid, None if not '''
        if order.get_type() == 'Buy':
            # use last buy price to estimate current ask, 
            # because the buy go accross spread to reach the best ask
            if order.get_price() < self.last_buy_price:
                return order
            else:
                return None
        else:
            # use last sell price to estimate current bid, 
            # because the sell go accross spread to reach the best bid
            if order.get_price() > self.last_sell_price:
                return order
            else:
                return None
            
    def place_orders(self, orders):
        ''' function that place set of orders into the exchange
        Inputs:
            orders: set of orders object to be placed
        '''
        if orders:
            for order in orders:
                self.place_order(order)
        else:
            pass
            
    def place_order(self, order):
        ''' function that place one order into the exchange
        Inputs:
            order: order object to be placed
        '''
        valid_order = self.valid_order(order)
        if valid_order:
            heappush(self.queue,(self.current_time+self.DELAY, valid_order.get_ID(),valid_order))
        else:
            pass
            ''' Uncomment below to print all invalid orders '''
#             print('-'*30)
#             print('Order {} is not added to queue because it is invalid'.format(order.order_info()))
#             print('Current bid: {}, Current ask: {}'.format(self.last_sell_price, self.last_buy_price))
        
    def cancel_orders(self, orders):
        ''' function that cancel set of orders in the exchange
        Inputs:
            orders: set of orders object to be canceled
        '''
        ''' Check order (1) when place it, (2) when it enter the order list from waiting queue'''
        if orders:
            self.orders['Buy'] = [(t,ID,order) for (t,ID,order) in self.orders['Buy'] if order not in orders]
            heapify(self.orders['Buy'])
            
            self.orders['Sell'] = [(t,ID,order) for (t,ID,order) in self.orders['Sell'] if order not in orders]
            heapify(self.orders['Sell'])
            
            self.queue = [(t,ID,order) for (t,ID,order) in self.queue if order not in orders]
            heapify(self.queue)
        else:
            pass
        
