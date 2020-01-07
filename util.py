import pandas as pd
import threading
from sklearn import preprocessing
import numpy as np
import requests
import csv
import ast
import time
import os
from datetime import datetime
history_points = 50

def csv_to_dataset(csv_path, column):
    #obtain ohlcv data
    data = pd.read_csv(csv_path)
    data = data.drop('date', axis=1)
    data = data.drop("close_time", axis=1)
    data = data.drop("ast_vol", axis=1)
    data = data.drop("no_tr", axis=1)
    data = data.drop("ig1", axis=1)
    data = data.drop("ig2", axis=1)
    data = data.drop("ig3", axis=1)
    data = data.values

    data_normaliser = preprocessing.MinMaxScaler()
    data_normalised = data_normaliser.fit_transform(data)

    # using the last {history_points} open close high low volume data points, predict the next open value
    ohlcv_histories_normalised = np.array([data_normalised[i:i + history_points].copy() for i in range(len(data_normalised) - history_points)])
    next_day_open_values_normalised = np.array([data_normalised[:, column][i + history_points].copy() for i in range(len(data_normalised) - history_points)])
    next_day_open_values_normalised = np.expand_dims(next_day_open_values_normalised, -1)

    next_day_open_values = np.array([data[:, column][i + history_points].copy() for i in range(len(data) - history_points)])
    next_day_open_values = np.expand_dims(next_day_open_values, -1)
    y_normaliser = preprocessing.MinMaxScaler()
    y_normaliser.fit(next_day_open_values)

    technical_indicators = []
    for his in ohlcv_histories_normalised:
        # note since we are using his[3] we are taking the SMA of the closing price
        sma = np.mean(his[:, 3])
        technical_indicators.append(np.array([sma]))

    technical_indicators = np.array(technical_indicators)

    tech_ind_scaler = preprocessing.MinMaxScaler()
    technical_indicators_normalised = tech_ind_scaler.fit_transform(technical_indicators)

    assert len(ohlcv_histories_normalised) == len(next_day_open_values_normalised) == len(technical_indicators_normalised)
    return ohlcv_histories_normalised, technical_indicators_normalised, next_day_open_values_normalised, tech_ind_scaler, y_normaliser, data_normaliser



def getOhlcData(symbol):
    datas = []
    #get the newwest first 1000
    conn = requests.get("https://api.binance.com/api/v3/klines?symbol={0}USDT&interval=1h&limit=1000".format(symbol))
    res = conn.content
    data = res.decode()
    data = ast.literal_eval(data)
    limit = len(data)
    endTime = data[0][0] - 3600000
    datas.append(data)

    #get the rest
    e = threading.Event()
    e.wait(1)
    while limit == 1000:
        conn = requests.get("https://api.binance.com/api/v3/klines?symbol={0}USDT&interval=1h&endTime={1}&limit=1000".format(symbol, endTime))
        res = conn.content
        data = res.decode()
        data = ast.literal_eval(data)
        limit = len(data)
        endTime = data[0][0] - 3600000
        datas.append(data)
        e.wait(1)
    
    formatCSVFile(symbol)
    while bool(datas):
        data_to_csv(datas.pop(), symbol)  #write the oldest first 

    #return the filepath to the  data file
    return './data/{0}.csv'.format(symbol)

def data_to_csv(data, fileName):
    with open("./data/{0}.csv".format(fileName), "a+") as my_csv:
        csvWriter = csv.writer(my_csv, delimiter=',')
        csvWriter.writerows(data)


def getLatestData(symbol):
    conn = requests.get("https://api.binance.com/api/v3/klines?symbol={0}USDT&interval=1h&limit=51".format(symbol))
    res = conn.content
    data = res.decode()
    data = ast.literal_eval(data)
    #convert data to numeric
    data_num = []
    for val in data:
        data_num.append([float(val[1]), float(val[2]), float(val[3]), float(val[4]), float(val[5])])
    data_num = np.array(data_num)
    data_num = data_num[0:50]
    #calc sma
    sum = 0
    for val in data_num[:,3]:
        sum += val
    sma = sum / 50
    #get the last candle data
    return sma, data_num


def writeToFile(log, symbol):
    string = ""
    #get the current time
    now = datetime.now()
    date_time = now.strftime("%d:%m:%Y %H:%M:%S")
    date_time += ":: "
    #merge log and append to file
    string += date_time + log + "\r\n"
    f = open("./logs/{0}.txt".format(symbol), "a+")
    f.write(string)
    f.close()


def deleteThefile(filepath):
    os.remove(filepath)

def formatCSVFile(symbol):
    string = '"date","open","high","low","close","volume","close_time","ast_vol","no_tr","ig1","ig2","ig3"\r\n'
    f = open("./data/{0}.csv".format(symbol), "a+")
    f.write(string)
    f.close()
