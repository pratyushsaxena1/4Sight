import sys
import yfinance as yf
import pandas as pd

def get_stock_data(stock_symbol):
    stock_data = yf.download(stock_symbol, '2020-01-01', None)
    stock_data.reset_index(inplace=True)
    stock_data['Date'] = stock_data['Date'].dt.strftime('%Y-%m-%d')
    stock_data.sort_values(by='Date', ascending=False, inplace=True)
    return stock_data.to_dict('records')

stock_symbol = sys.argv[1]
data = get_stock_data(stock_symbol)
print(data)