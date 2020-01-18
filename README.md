# Algoritmic Trading Bot based on LSTM Neural Networks and Pool Strategy
1) Creates a pool of most volatile cryptocurrencies that are in the first 50 cryptocurrencies from [Coinmarketcap](coinmarketcap.com) and has 
   a pair with USDT in [Binance](binance.com).
 
2) Automatically spins up a LSTM NN for each symbol that is in the pool, creates a new process for each symbol and 
  start trading them simultaneously.
  
3) Refreshes the pool every 3 days along with the models and continues the cycle.


# Disclaimer

LSTM Neural Netwoks model that is being used in this bot is taken from the [this](https://github.com/yacoubb/stock-trading-ml) 
githup repository and licencing may differ.

LICENCE: [MIT](https://en.wikipedia.org/wiki/MIT_License)