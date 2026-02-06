# import akshare as ak
# import pandas as pd
# import baostock as bs
# from datetime import datetime, timedelta
#
#
# def daily_to_weekly(etf_hist_daily):
#     # 设置日期索引
#     etf_hist_daily['date'] = pd.to_datetime(etf_hist_daily['date'])
#     etf_hist_daily.set_index('date', inplace=True)
#
#     # 确保索引是datetime类型
#     if not pd.api.types.is_datetime64_any_dtype(etf_hist_daily.index):
#         etf_hist_daily.index = pd.to_datetime(etf_hist_daily.index)
#
#     # 按周重采样
#     etf_hist_weekly = etf_hist_daily.resample('W').agg({
#         'open': 'first',
#         'close': 'last',
#         'high': 'max',
#         'low': 'min',
#         'volume': 'sum',
#     })
#     # 删除NaN行
#     return etf_hist_weekly.dropna()
#
#
# df = ak.stock_zh_index_daily('sh000001')
# w_df = daily_to_weekly(df)
# print(daily_to_weekly(df))
#
#
# weekly_df = df.resample('W-FRI').agg({
#     'open': 'first',  # 周开盘价：周一的开盘价
#     'high': 'max',  # 周最高价：一周内的最高价
#     'low': 'min',  # 周最低价：一周内的最低价
#     'close': 'last',  # 周收盘价：周五的收盘价
# })
#
# start_date = df['date'].iloc[-105]
# end_date = df['date'].iloc[-1]
#
# if end_date != '':
#     last_trade_date = datetime.strptime(end_date, "%Y%m%d").date()
# else:
#
#     last_trade_date = df['date'].iloc[-1]
