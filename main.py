import multiprocessing
import threading
from pool import Pool
from train import Train
from trade import Trade
from binance.client import Client
from util import writeToFile

#init
api_key = "crdv8sGzNgQiaMXa91Ybbfvj9qaUba8OnIZN65ZrtjFDrYHP5UtrMYraiAAisWJW"
api_secret = "xRn9iGwfkjNq2Zpn6OKlkWg8TPi0lp65ysJpHqwEK8SVOaIfCGssrMlsvxAxNXUq"
binancecClient = Client(api_key, api_secret)
balance = 500
models = {}
processes = {}
tradeIntances = {}
pool = []


def logPool(pool):
    log = "POOL: ["
    for symbol in pool:
        log += "'" + symbol + "', "
    log += "]"
    return log

def refreshTradeSession(balance):
    log = "   ------  NEW TRADE SESSION   ------"
    writeToFile(log, "main")

    #construct a new pool
    pool = Pool.construct(binancecClient)
    log = logPool(pool)
    writeToFile(log, "main")

    #train the missing models in the new pool
    newModels = Train.start(pool, models)
    log = "Added New Models for Symbols: "
    log += logPool(newModels.keys())
    writeToFile(log, "main")

    #stop trading the models that is not in the new pool
    writeToFile("Terminating OUT-DATED symbols...", "main")
    for symbol in models.keys():
        if not (symbol in pool):
            writeToFile("terminating {0}...".format(symbol), "main")
            #terminate the process for this symbol
            processes[symbol].terminate()
            #liquadate any assest for this symbol if we have some
            balance += tradeIntances[symbol].liquidateAssets()
            #remove the symbol from session
            del processes[symbol]
            del tradeIntances[symbol]
            del models[symbol]
            writeToFile("SUCCESS", "main")

    #refresh the instances for newModels
    writeToFile("Creating New Trade Instances...", "main")
    for symbol in newModels.keys():
        writeToFile( "creating a Trade instance for {0}...".format(symbol), "main")
        #add symbol to the models
        models[symbol] = newModels[symbol]
        #create a new trade instance
        newTradeInstance = Trade(models[symbol], binancecClient, symbol, int(balance/len(pool)))
        tradeIntances[symbol] = newTradeInstance
        #create and new process for trade
        processes[symbol] = multiprocessing.Process(target=newTradeInstance.start)
        processes[symbol].start()
        writeToFile("SUCCESS for {0}...".format(symbol) , "main")

    writeToFile( " -------  NEW SESSION STARTED!! -------", "main")

    return balance



if __name__ == "__main__":

    main = threading.Event()
    balance = refreshTradeSession(balance)
   
    while not main.wait(60*60*50): # run every 50 hours
        balance = refreshTradeSession(balance)
