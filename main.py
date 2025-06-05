import time

import akshare as ak
import pandas as pd
import baostock as bs
import csv
from tqdm import tqdm
import requests
import ccxt
if __name__ == '__main__':

    ak.amac_fund_abs()
    # import ccxt  获取币安
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {
        'symbol': 'BTCUSDT'
    }
    response = requests.get(url, params=params)
    print(response.json())