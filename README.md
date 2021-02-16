# Yunxiao-Backtester

# TO RUN: 
- modify the strategy in generate_signal in Strategy.py 
- modify the exchange info, baktest period in main.py, will need to implement other data querying for market other than Bitmex
  - for specific data formatting, please refer to DataReader.py by running it with python3 DataReader.py
- then in console enter python3 main.py to get the backtest started, reults (realized PNL, total PNL) will be printed to the console
- Note: invalid orders are printed to screen for validaition: most of those orders are not valid because he market moves in same direction in subsequent ticks, causing one side of the ask and bid being too poorly estimated (by very distant last price).

# Algorithm
1. Create a exchange, a strategy, then subsribe to the exchange
2. Call backtest in strategy, then it will start the backtesting in the corresponding exchange
3. Exchange update the time until the end time is reached
4. in each update, move forward one tick where there are any update in any coin
    - check whether any order on the list can be excecuted by comparing the last trade price with every order's quote
    - update the price into last_buy or last_sell, then update the price for strategy
    - after update the price, strategy will generate signal for that coin_type (Might be changed later to cross-sectional), 
    - according to the signal, strategy place order submit to the exchange, the price will be automatically set to $0.99 \times last price$ if buy, and $1.01 \times last price$ if sell
    - once the order enter the exchange, it will be put in a waiting heapqueue, in each of the later update, it will be checked with current time and push into the order queue
    - once the order is excuted, strategy mark the order as done, record it in the completed list, update realized pnl
5. update until te end time is reached, then compute the unrealized pnl to calculate the total pnl, in the calculation of unrealzied pnl, since it is assumed to be liquidated at last price, it will not receive maker fee


# Updated 02/08
- Should be able to place multiple orders at a time
- Compare desired order with local order book, if exist, no need to place again, if not, place it, cancel all undesired order
- Objective: markett making and placee as much as possible
- Single coin type        
- def cancel_order to cancel all past unwanted order every tick
- In reality, your limited order (if price higher than other side limited order price) will become a taker and pay taker fee, so defined check order
    - according to last sell buy price to ask ank bid, your order price should not be between the bid ask
        **eg compare sell order price with market bid, must be > or it will get o market order
    - Q: Check before put in waiting queue or check before transfer from waiting to orderlist?
- smallest change tick: let the user set, eg: 0.0025, when strategy send order, get the price rounded to the closest tick
- defined hash and compare for order object, now can make set of orders

# Future possiblities
- Can combine ticks to 5 s bar, then separate (and aggregate to) 1 sell and 1 buy order, in this case just modify data
- Can record PNL for each tick and plot the PNL time series for backtestting period
