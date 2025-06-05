import time

import akshare as ak
import pandas as pd
import baostock as bs
import csv
from tqdm import tqdm

if __name__ == '__main__':
    etf_list = ak.fund_etf_category_sina(symbol="ETF基金")
    # print(etf_list.head())
    etf_codes = etf_list['代码'].to_list()

    hist_etf = ak.fund_etf_hist_sina(symbol="sz159998")
    print(hist_etf)