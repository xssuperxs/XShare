import akshare as ak
import pandas as pd
import baostock as bs
from datetime import datetime, timedelta


# def calculate_limit_up_price(prev_close, limit_rate=0.10):
#     """
#     计算涨停价
#
#     参数:
#     prev_close: 前收盘价
#     limit_rate: 涨跌幅限制（默认10%）
#
#     返回:
#     float: 涨停价（四舍五入到0.01元）
#     """
#     limit_up = prev_close * (1 + limit_rate)
#     return round(limit_up, 2)
#
#     (20.12, 22.13, 30.15)
#
#
# print(calculate_limit_up_price(29.10))

# A股ETF

# 获取ETF
# etf_spot = ak.fund_etf_spot_em()
# etf_codes = etf_spot['代码'].tolist()
# print(etf_codes)

# def get_etf_klines(symbol: str, period: str):
#     """
#     :type symbol: 股票代码
#     :param period: 周期 日 daily 周 weekly
#     """
#     if period == 'd':
#         etf_hist_kline = ak.fund_etf_hist_sina(symbol=symbol)
#     else:
#         period = 'weekly'
#         etf_hist_kline = ak.fund_etf_hist_em(symbol=symbol, period=period)
#
#     if etf_hist_kline.empty or etf_hist_kline["high"].iloc[-1] > 50:
#         return pd.DataFrame()
#     return etf_hist_kline

#
# ak.fund_etf_hist_em()
# print(etf_spot)
# ak.fund_etf_hist_min_em()
# ak.fund_etf_hist_sina()
# # 港股ETF
