import keras
import tensorflow as tf
from keras.models import Model
from keras.layers import Dense, Dropout, LSTM, Input, Activation, concatenate
from keras import optimizers
import numpy as np
np.random.seed(4)
from tensorflow import random
random.set_seed(4)
from util import csv_to_dataset, history_points, getOhlcData, deleteThefile


class Train:
    @staticmethod
    def train(filePath, symbol):
        # dataset
        ohlcv_histories, technical_indicators, next_day_open_values, technical_normalizer, y_normaliser, data_normaliser = csv_to_dataset(filePath, 3)

        # model architecture
        # define two sets of inputs
        lstm_input = Input(shape=(history_points, 5), name='lstm_input')
        dense_input = Input(shape=(technical_indicators.shape[1],), name='tech_input')

        # the first branch operates on the first input
        x = LSTM(50, name='lstm_0')(lstm_input)
        x = Dropout(0.2, name='lstm_dropout_0')(x)
        lstm_branch = Model(inputs=lstm_input, outputs=x)

        # the second branch opreates on the second input
        y = Dense(20, name='tech_dense_0')(dense_input)
        y = Activation("relu", name='tech_relu_0')(y)
        y = Dropout(0.2, name='tech_dropout_0')(y)
        technical_indicators_branch = Model(inputs=dense_input, outputs=y)

        # combine the output of the two branches
        combined = concatenate([lstm_branch.output, technical_indicators_branch.output], name='concatenate')

        z = Dense(64, activation="sigmoid", name='dense_pooling')(combined)
        z = Dense(1, activation="linear", name='dense_out')(z)

        # our model will accept the inputs of the two branches and
        # then output a single value
        model = Model(inputs=[lstm_branch.input, technical_indicators_branch.input], outputs=z)
        adam = optimizers.Adam(lr=0.0005)
        model.compile(optimizer=adam, loss='mse')
        model.fit(x=[ohlcv_histories, technical_indicators], y=next_day_open_values, batch_size=32, epochs=50, shuffle=True, validation_split=0.1)
        return model, technical_normalizer, y_normaliser, data_normaliser

    @staticmethod
    def start(currentPool, models):
        #compare the pool againts the current avaible models and find the missing models
        missingSymbols = Train.findMissingSymbols(currentPool, models)

        #get the historical data for each missing symbol and train a model
        newModels = {}
        for symbol in missingSymbols:
            filepath = getOhlcData(symbol)
            model, sma_normalizer, y_normaliser, data_normalizer = Train.train(filepath, symbol)
            newModels[symbol] = (model, data_normalizer, y_normaliser, sma_normalizer)
            deleteThefile(filepath)

        #return the new models
        return newModels

    @staticmethod
    def findMissingSymbols(pool, models):
        missingSymbols = []
        for symbol in pool:
           if not (symbol in models.keys()):
               missingSymbols.append(symbol)
        return missingSymbols
   