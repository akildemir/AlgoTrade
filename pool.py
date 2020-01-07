from requests import Session
from binance.client import Client
import json
import numpy as np
import math


class Pool:
   
    @staticmethod
    def getCmcData():
        # get coinmarketCap first 50
        cmc = []
        parameters = {
            'start':'1',
            'limit':'50',
            'convert':'USD'
        }
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': 'd63574e8-e7f4-48c5-8878-56640a67d267',
        }
        session = Session()
        session.headers.update(headers)
        response = session.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest", params=parameters)
        data = json.loads(response.text)
        
        for quote in data['data']:
            cmc.append(quote['symbol'])

        return cmc

    @staticmethod
    def getBinanceData(client):
        # get binance USDT tradeable assets
        binance = []
        data = client.get_exchange_info()
        for quote in data['symbols']:
            if quote['quoteAsset'] == "USDT":
                binance.append(quote['baseAsset'])
        
        return binance
    
    @staticmethod
    def matchTheSymbols(binance, cmc):
        common = []
        for symbol in binance:
            for cmc_symbol in cmc:
                if symbol == cmc_symbol:
                    common.append(symbol)

        return common

    @staticmethod
    def getVolatiliy(client, symbol):
        data_points = []
        data = client.get_klines(symbol=symbol + "USDT", interval='1h', limit=1000)
        for val in data:
            data_points.append(float(val[4]))
        data_points = np.array(data_points)
        mean = np.mean(data_points)
        variance = np.mean(np.square(data_points - mean))
        stdDev = math.sqrt(variance)
        percent = (stdDev * 100) / mean
        return percent
    
    @staticmethod
    def construct(binanceClient):
        #init the variables
        pool = [] 
        volatiliyTreshold = 5 # 2% deviaties from the its average price

        #get the data
        cmc     = Pool.getCmcData()
        binance = Pool.getBinanceData(binanceClient)
        common  = Pool.matchTheSymbols(binance, cmc)

        #make the pool
        for symbol in common:
            vol = Pool.getVolatiliy(binanceClient, symbol)
            if vol >= volatiliyTreshold:
                pool.append(symbol)

        return pool