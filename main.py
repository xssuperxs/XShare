import time

import akshare as ak
import pandas as pd
import baostock as bs
import csv
from tqdm import tqdm

import xshare

__WINDOW_SIZE = 6
nSubWindow = [i for i in range(2, __WINDOW_SIZE)]

print(nSubWindow)
import os

__STOCK_CACHE_FILE_DICT = {
    0: 'A_daily.csv',
    1: 'A_weekly.csv',
    2: 'AH_daily.csv',
    3: 'A_Index_daily.csv',
    4: 'A_Index_weekly.csv'
}

if __name__ == '__main__':
    highs_index = [3, 5, 6, 7, 8, 9, 10, 20]
    preLowIndex = 2
    highs_index_reversed = highs_index[::-1]  # 生成反转副本，不修改原列表
    for idx, item in enumerate(highs_index_reversed):
        original_idx = len(highs_index) - 1 - idx
        preHighIndex = item  # 原始正序索引

