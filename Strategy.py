from datetime import timedelta, datetime, date
import pandas as pd
import numpy as np
import gzip
import shutil
import requests
from collections import defaultdict
import time
from Exchange import Exchange
from Trade import Trade
from Order import Order
from heapq import heappush, heappop,heapify
import math
import os


class Strategy:
    ''' 
        Class which interact wit the exchange to do the backtest 
        and where you implement your own strategy 
    '''
    def __init__(self, exchange, maker_fee = 2.5/1000, capital = 100, pct = 5/100):
        # self.current_time = start_time
        self.exchange = exchange
        self.prices = []
        #self.prices, self.prices = self.exchange.update_to_time(start_time)
        self.order_num = 0
        self.positions = 0.0
        self.realized_PNL = 0
        self.unrealized_PNL = 0
        self.MAKER_FEE = maker_fee
        self.capital = capital
        self.pct = pct
        # this is list because we allow dulplicates when record what is finished
        self.completed_order = []
        # these are sets because when place order each round we want unique orders
        self.orders_active = set([])
        self.orders_desired = set([])
        
    def add_order(self, direction, price, size ):
        ''' function that create a order object and add it to desired order list
        Inputs:
            direction: direction of order
            price: price of order
            size: size of order
        '''
        # ID auto generated as its position in order list
        ID = self.order_num
        self.order_num += 1
        
        order = Order(direction, size, price, ID)
        self.orders_desired.add(order)
    
    def place_orders(self):
        ''' function that place a set of orders to exchange'''
        ''' Uncomment print statements below to print out every order placed '''
#         print(' --------------------------\n ')
#         print('Exchange time',self.exchange.current_time))
#         print('Current_order',[order.order_info() for order in self.orders_active],
#               '\nDesired_order',[order.order_info() for order in self.orders_desired])

        # use set difference to find order to place and to cancel
        orders_to_place = self.orders_desired.difference(self.orders_active)
        orders_to_cancel = self.orders_active.difference(self.orders_desired)
        orders_to_keep = self.orders_active.intersection(self.orders_desired)
        
#         print('orders_to_place',[order.order_info() for order in orders_to_place],
#               '\norders_to_cancel',[order.order_info() for order in orders_to_cancel],
#               '\norders_to_keep',[order.order_info() for order in orders_to_keep])

        # reset activ order and desired order
        self.orders_active = self.orders_desired.copy()
        self.orders_desired = set([])
        
        # place and cancel orders
        self.exchange.place_orders(orders_to_place)
        self.exchange.cancel_orders(orders_to_cancel)
        
#         print('Orders_in_exchange',self.exchange.orders, self.exchange.queue)
    
    def update_prices(self,trade):
        ''' function that update exchange reported prices to record list
        Inputs:
            trade: a trade reported by exchange
        '''
        # update price to a list
        self.prices.append(trade.get_price())
        self.generate_signal()
        
    ### mean-reverting last tick, last tick up the next might go down...
    def generate_signal(self):
        ''' function that generate signal everytime a trade from exchange is updated
            it generate signal and place orders
        '''
        
        ''' 
        IMPLEMENT YOUR STRATEGY HERE
            - Can add more recordings in fields, just need to add the code for update in 
              update_prices(self,trade,coin)
            - Except MM strategy, also can use trained model to predict price

        SUBJECT TO CHANGE: 
            place a sell order as last price * 1.01 and buy order as last price * 0.99,
            each time assume captial is constant and use pct*capital amount of money to place order
        '''
        # a simple MM strategy: look at MA 30 ticks vol and relative positions, 
        # place orders when market shows no infomation about direction
        historical_prices = np.array(self.prices[-30:])
        
        if len(historical_prices) < 14:
            return

        # can make this a queue, can record in fields and update each update_prices
        MA_30ticks = np.mean(historical_prices)
        std_30ticks = np.std(historical_prices)
        
        max_div = (np.max(historical_prices) - np.min(historical_prices))/MA_30ticks
        
        lastest_price = historical_prices[-1]
        if std_30ticks != 0:
            z = abs(lastest_price - MA_30ticks)/std_30ticks # std of log return
        else:
            z = 0
        vol_30ticks = np.std(np.diff(np.log(historical_prices))) # very naive measure of current vol
        

        if all([z < 2,
               max_div < 0.02,
               vol_30ticks < 0.01]):
            min_tick_size = self.exchange.get_min_tick_size()
            
            for i in range(1,3):
                buy_price = lastest_price - min_tick_size*i
                sell_price = lastest_price + min_tick_size*i
                # place multiple order for market making
                self.add_order('Buy', buy_price, self.pct*self.capital/buy_price)
                self.add_order('Sell', sell_price, self.pct*self.capital/sell_price)
                
        # if there is no signal, it will still call place orders to cancel all orders        
        self.place_orders()


    
    def mark_done(self,order,time):
        ''' function that mark a order as done, and record its time 
        Inputs:
            order: order that is completed
            time: time when it is completed
        '''
        try:
            self.orders_active.remove(order)
        except:
            print(order.order_info())
            print([order.order_info() for order in self.orders_active])
            print([order.order_info() for order in self.orders_desired])
            raise Exception('order not exist in order order_list')
        # record completed order and update PNL
        dic = {'Buy':-1, 'Sell':1}
        sign = dic[order.get_type()]
        # add sign to maker fee, it should always be positive
        self.realized_PNL += sign*order.get_value()*(1+sign*self.MAKER_FEE)
        self.positions -= dic[order.get_type()]*order.get_size()
        self.completed_order.append((time,order))
     
    def calculate_unrealized_PNL(self):
        ''' 
            function that compute all uncleared position with last trdae price in record
            we do not include maker fee here because it would be liquidated by the end of the backtest
        '''
        self.unrealized_PNL = self.positions*self.prices[-1]
        return self.unrealized_PNL
    
    def calculate_total_PNL(self):
        ''' function that compute all realized and unrealized PNL '''
        return self.calculate_unrealized_PNL() + self.get_realized_PNL()
    
    def get_realized_PNL(self):
        ''' function that compute the PNL realized through completed trades '''
        return self.realized_PNL
    
    def start_backtest(self):
        ''' function taht start backtest in self.exchange '''
        if self.exchange:
            self.exchange.add_subscriber(self)
            self.exchange.start_backtest()
            result_df = pd.DataFrame({'Realized_PNL':self.get_realized_PNL(),
                                      'Total_PNL':self.calculate_total_PNL()},index = ['metrics'])
            try:
                display(result_df)
            except:
                print(result_df)
        else:
            raise Exception('Need to subscribe to exchange first')
            
    def get_positions(self):
        ''' functio that get the position in that strategy '''
        return self.positions
    