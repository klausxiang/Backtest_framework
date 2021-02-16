class Trade:
    ''' Class that simulate a trade with price, size, direction '''
    def __init__(self, tup):
        self.side, self.qty, self.price = tup

    ''' Getter methods to get trades attributes '''
    def get_price(self):
        return self.price

    def get_size(self):
        return self.qty

    def get_type(self):
        return self.side

    def trade_info(self):
        ''' function that return the infomation of trade in dict '''
        return {'price': self.price,
                'size': self.qty,
                'side': self.side}