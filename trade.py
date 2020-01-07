import threading
from binance.client import Client
from binance.exceptions import BinanceAPIException
from util import writeToFile, getLatestData
import numpy as np
from util import writeToFile, csv_to_dataset
from keras.models import load_model

class Trade:
    model = ()
    symbol = ""
    buy = True
    balance = 0
    assets  = 0
    predictions = []
    correction = 0
    def __init__(self, model, client, symbol, balance):
        self.model = model
        self.symbol = symbol
        self.client = client
        self.balance = balance
        log = "NEW TRADE INSTANCE SYMBOL: {0}, BALANCE: {1}".format(symbol, balance)
        writeToFile(log, symbol)
        
    def getVariables(self): #last50 is already passed by reference
        #get the latest sma and candle data
        latest_sma_data, last50 = getLatestData(self.symbol) 
        latest_sma_data         = np.array([[latest_sma_data]])

        #normalize them
        last50_normalized          = self.model[1].transform(last50) #data normalizer of the model
        latest_sma_data_normalized = self.model[3].transform(latest_sma_data) #sma normalizer of the model
        #predict next hour close value by using the last 50 kandle data and sma of last 50 hour close value
        pediction = self.model[0].predict([[last50_normalized], [latest_sma_data_normalized[0]]]) #model
        next_hour_closing_price_prediction = np.squeeze(self.model[2].inverse_transform(pediction)) # y normalizer
        return next_hour_closing_price_prediction, last50[49][0], last50[47:,3] #TODO:: try with closing hour etc.

    def trade(self):
        #set up log
        noTradeMade = True
        log = "{0}USDT ".format(self.symbol)
        
        #get variables
        next_hour_closing_price_prediction, current_hour_open_val, last3_real_closing_price = self.getVariables()
        #calculate the correction
        self.calculateCorrection(next_hour_closing_price_prediction, last3_real_closing_price)
        
        #calculate delta
        delta = (next_hour_closing_price_prediction + self.correction) - current_hour_open_val

        #get current price
        trades = self.client.get_recent_trades(symbol= self.symbol + 'USDT', limit=1)
        curent_price = float(trades[0]['price'])

        #set the threshold to 0.1%
        threshold = curent_price * 0.001

        #make decision
        if (delta > threshold) and self.buy:
            #buy code goes here
            #set up logs
            noTradeMade = False
            log += "Signal: BUY: "
            
            #try to buy for all of balance
            quantity = int(self.balance / curent_price)
            buySuccess = False
            while not buySuccess:
                try:
                    self.client.create_test_order(symbol=self.symbol + 'USDT', side=Client.SIDE_BUY, type=Client.ORDER_TYPE_MARKET, quantity=quantity)
                    buySuccess = True
                    self.assets += quantity
                    self.balance = 0
                    #we start to look for sell opportinues
                    self.buy = False
                    log += "BALANCE: {0}, {1}: {2}".format(self.balance, self.symbol, self.assets)
                except BinanceAPIException as e:
                    #market can move realy quick between the time we got the last price and make our order
                    #if this move is uptrend we can get unsefficent balance exception
                    #we will have an exceptin in this case and if we do we decrease the amount we want to buy
                    buySuccess = True
                    log += "Exceptin Raised while tyrig to place a buy order: {0}".format(e.message)
                    if(e.message == "Account has insufficient balance for requested action."):
                        quantity = quantity - int(quantity*0.01) #dcrease the buying amount 1%
                        buySuccess = False
        elif (delta < -threshold) and not self.buy:
            #sell code goes here
            #set up log
            noTradeMade = False
            log += "Signal: SEl: "

            try:
                self.client.create_test_order(symbol=self.symbol + 'USDT', side=Client.SIDE_SELL, type=Client.ORDER_TYPE_MARKET, quantity=self.assets)
                self.balance += curent_price * self.assets
                self.assets = 0
                #we start to look for sell opportinues
                self.buy = True
                log += "BALANCE: {0}, {1}: {2}".format(self.balance, self.symbol, self.assets)
            except BinanceAPIException as e:
                log += "Sell order failed skippin this trade.. {0}".format(e.message)
        
        if noTradeMade:
            if  self.buy:
                log += "No BUY signal Found. Skpipping this cycle..."
            else:
                log += "No SEL signal Found. Skpipping this cycle..."
                
        #write log 
        writeToFile(log, self.symbol)

    def start(self):
        self.trade()
        e = threading.Event()
        while not e.wait(60*60):
           self.trade()

    def calculateCorrection(self, next_hour_closing_price_prediction, last3_real_closing_price):
        if len(self.predictions) < 3:
            self.predictions.append(next_hour_closing_price_prediction)
        else:
            sum = 0
            for i in range(3):
                sum +=  last3_real_closing_price[i] - self.predictions[i]
            self.correction  = sum / 3
            self.predictions = []


    def liquidateAssets(self):
        #if we hold any assets for this symbol, sell all
        log = "{0}USDT LIQITADE".format(self.symbol)

        #get current price
        trades = self.client.get_recent_trades(symbol=self.symbol + 'USDT', limit=1)
        curent_price = float(trades[0]['price'])

        try:
            self.client.create_test_order(symbol=self.symbol + 'USDT', side=Client.SIDE_SELL, type=Client.ORDER_TYPE_MARKET, quantity=self.assets)
            self.balance += curent_price * self.assets
            self.assets = 0
            #we start to look for sell opportinues
            log += "BALANCE: {0}, {1}: {2}".format(self.balance, self.symbol, self.assets)
        except BinanceAPIException as e:
            log += "Sell order failed skippin this trade.. {0}".format(e.message)

        return self.balance