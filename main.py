import math
import string
import time
import pymongo

from collections import Counter

import numpy as np
from ta.trend import MACD
import threading
from queue import Queue
import pandas as pd
import os
import subprocess
import sys
from datetime import datetime

import akshare as ak

print(ak.__version__)

# stock_zh_index_daily_df = ak.stock_zh_index_daily(symbol="sz399552")
# print(stock_zh_index_daily_df)

stock_zh_a_hist_df = ak.stock_zh_a_hist(
    symbol="600519",
    period="daily",
    adjust="qfq"
)
成交额_int = stock_zh_a_hist_df["成交量"].astype('int64')
print(成交额_int)

hk_df = ak.stock_hk_daily(symbol='00700', adjust="qfq")
#
print(hk_df)


# 成交额
# mongoDBCli = pymongo.MongoClient("mongodb://dbroot:123456ttqqTTQQ@113.44.193.120:28018/")
# db = mongoDBCli['ashare']
# # 分析结果的集合
# coll_analysis_Results = db['analysis_results']
#
# list1 = ['6000519', '123456', '778899']
#
# data = {
#     "type1": list1,
#     "type2": [],
#     # "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 例如：2023-11-20 14:30:45
#     "analysis_date": datetime.now()
# }
#
# coll_analysis_Results.insert_one(data)
