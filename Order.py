class Order:
    ''' Class that simulate an order with price, size, direction and ID '''
    def __init__(self,order_type, qty ,prc, ID = 0):
        self.price = prc
        self.qty = qty
        self.order_type = order_type
        self.id = ID
    
    def __ne__(self, other):
        """Overrides the default implementation of not equal """
        return not self.__eq__(other)

    def __eq__(self, other):
        """Overrides the default implementation of equal"""
        if isinstance(other, Order):
            return self.equals(other)
        return False
    
    def __lt__(self, other):
        """Overrides the default implementation of less than"""
        if isinstance(other, Order):
            return self.id < other.id
        else:
            raise Exception('Cannot compare order object with other object')
        
    
    def __hash__(self):
        """Overrides the default implementation of hash"""
        return hash((self.order_type, self.qty, self.price))
    
    """ Getter methods to get the attributes """
    def get_price(self):
        return self.price
    
    def get_size(self):
        return self.qty
    
    def get_type(self):
        return self.order_type
    
    def get_ID(self):
        return self.id
    
    def get_value(self):
        return self.price*self.qty
    
    def order_info(self):
        ''' function that return the order information in dictionary '''
        return {'price' : self.price,
                'size' : self.qty,
                'direction' : self.order_type,
                'ID': self.id}
    
    def set_price(self, prc):
        ''' function that set the price of order to be input price
        Inputs:
            prc: price to set
        '''
        self.price = prc
        
    def equals(self, other_order):
        ''' function that compare size, price, type to check if two orders equal
        Inputs:
            other_order: order to be compared with
        '''
        return all([self.price == other_order.get_price(),
                   self.qty == other_order.get_size(),
                   self.order_type == other_order.get_type()])   