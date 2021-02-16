from datetime import timedelta, datetime, date
import pandas as pd
import numpy as np
import gzip
import shutil
import requests
from collections import defaultdict
from heapq import heappush, heappop
import time
from Trade import Trade
import os

class DataReader:
    '''Class that request, read and process the data to tick_data'''
    # based on data type, apply different reader to process data to the same format
    # the basic format is acccording to Bitmex, where following columns are included
    # 'timestamp', 'symbol', 'side', 'size', 'price'
    def __init__(self, data_type):
        # specify the data type
        self.data_type = data_type
        self.original_data = None
        
        
    def get_original_df(self):
        ''' returns unprocessed data get from the web'''
        return self.original_data
    
    def read_data(self, start, end, path = './', request = True):
        '''based on data type, apply different reader to process data to the same format
           the basic format is acccording to Bitmex, where following columns are included
           'timestamp', 'symbol', 'side', 'size', 'price'
        Inputs:
            start: start date in datetime.date(year,month,day) format
            end: end date in datetime.date(year,month,day) format
            path: path you want to save your data
            request: set to True if you want to request data from web, false if you already have data
        '''
        
        if isinstance(start, str) and isinstance(end, str):
            try:
                start = datetime.strptime(start,'%Y-%m-%d')
                end = datetime.strptime(end,'%Y-%m-%d')
            except:
                raise Exception('Start and end date, if entered in string format, should be %Y-%m-%d')
        elif not (isinstance(start, datetime) and isinstance(end, datetime)):
            raise Exception('Start and end date should be entered in string format or datetime object')
            
        if self.data_type == 'Bitmex':
            self.bitmex_data_reader(start, end, path = path, request = request)
        elif self.data_type == 'Bybit':
            self.bybit_data_reader(start, end, path = path, request = request)
        else:
            self.other_data_reader(start, end, path = path, request = request)
        
        
    def bitmex_data_reader(self, start, end, path = './', request = True):
        ''' function defined for bitmex data reading 
        Inputs:
            start: start date in datetime.date(year,month,day) format
            end: end date in datetime.date(year,month,day) format
            path: path you want to save your data
        '''
        def save_as_pickle(x, path):
            x.groupby('timestamp').agg(tuple).to_pickle(path + x.name + '.pkl')
            
        # read bitmex data
        print('Reading in data from',start.strftime("%Y-%m-%d"),
              'to', end.strftime("%Y-%m-%d"))
        if request:
            data = self.bitmex_data_request(start, end, path = path)
        else:
            try:
                data = pd.read_csv(path)
            except:
                raise Exception('If not requesting from web, please enter a valid path to data csv file')
                
        # check that those columns are in the data
        needed_columns = set(['timestamp', 'symbol', 'side', 'size', 'price'])
        if not needed_columns.issubset(set(data.columns)):
            raise Exception('Given data file need to contain columns {}'.format(needed_columns))
        # process data into ticks in rows, symbols in columns
        data.timestamp = pd.to_datetime(data.timestamp, format = '%Y-%m-%dD%H:%M:%S.%f')
        symbol_prices = data.groupby(['symbol']).apply(lambda x: x.set_index('timestamp')[['side','size','price']])
        tupled= symbol_prices.apply(tuple,axis = 1)
        trades = tupled.apply(lambda x:Trade(x))
        
        # display(data)
        self.original_data =data.copy()
        # data directory
        if not os.path.isdir(path+'data/'):    
            os.mkdir(path+'data/')
        # save pickle file for each symbol
        trades.groupby('symbol').apply(lambda x: save_as_pickle(x, './data/'))        
        
        
    def bitmex_data_request(self, start, end, path = './'):
        ''' function defined for bitmex data requesting from web
        Inputs:
            start: start date in datetime.date(year,month,day) format
            end: end date in datetime.date(year,month,day) format
            path: path you want to save your data
        Output:
            dataframe contans the tick level tuple trades for all coin types
        '''
        d1 = start
        d2 = end
        datas = []
        # this will give you a list containing all of the dates
        file_names = [(d1 + timedelta(days=x)).strftime("%Y%m%d")+'.csv.gz' for x in range((d2-d1).days + 1)]

        base_url = 'https://s3-eu-west-1.amazonaws.com/public.bitmex.com/data/trade/'
        # path = '/Users/yunxiaoxiang/Desktop/Ace quant/data/trade/'

        for f in file_names:
            r = requests.get(base_url+f)

            if 'The specified key does not exist' in r.text:
                raise Exception(f + 'has no corresponding file')

            print('Getting data from', base_url+f)   
            if not os.path.isdir(path+'data/'):    
                os.mkdir(path+'data/')
            with open(path + "data/" + f,"wb") as file: 
                file.write(r.content)
            with gzip.open(path + "data/" + f, 'rb') as f_in:
                with open(path + "data/"+  f[:-3] , 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            datas.append(pd.read_csv(path +"data/"+ f[:-3]))
        return pd.concat(datas)
    
    def bybit_data_reader(self, start, end, path = './', request = True):
        ''' function to be defined for reading bybit exchange data'''
        print('Please implement the bybit_data_reader in DataReader Class')
        pass
    
    def other_data_reader(self, start, end, path = './', request = True):
        ''' function to be defined for reading other exchange data'''
        print('Please implement the other_data_reader in DataReader Class')
        pass
    