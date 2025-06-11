import time

import akshare as ak
import pandas as pd
import baostock as bs
import csv
from tqdm import tqdm
import requests
import ccxt

from binance import Client

# 初始化客户端（公共API无需密钥）

import cryptocompare

import cryptocompare

data = cryptocompare.get_historical_price_day('BTC', 'USDT', limit=100)
df = pd.DataFrame(data)
df = df.drop(columns=['conversionType', 'conversionSymbol', 'volumeto', 'volumefrom'])
df['date'] = pd.to_datetime(df['time'], unit='s')
df = df.drop(columns=['time'])
print(df)

# df.set_index('date', inplace=True)
print(type(data))
print(data)
print(data)

#     return usdt_pairs
# exchange = 'Binance'  # 币安交易所名称
# pairs = cryptocompare.get_pairs(exchange=exchange)
#
# print(pairs)
# # 打印所有交易对
# for pair in pairs:
#     print(f"{pair['fsym']}/{pair['tsym']}")


# url = "https://min-api.cryptocompare.com/data/v4/all/exchanges?e=binance"
# response = requests.get(url)
# print(response)
# data = response.json()
# print(data)
#
# # 检查返回的数据结构
# print(data.keys())  # 查看顶层键
# print(data["Data"]['exchanges']['Binance']['pairs'].keys())  # 查看交易所列表
# print(data.keys())  # 查看顶层键
# 测试输出
# pairs = get_binance_usdt_pairs()
# print(f"获取到 {len(pairs)} 个币安USDT交易对")
# print(pairs[:10])  # 打印前10个

#
#
# # 获取并打印前20个币安USDT交易对
# binance_pairs = get_binance_pairs_formatted()
# print(binance_pairs)
# print("币安USDT交易对(示例):")
# for pair in binance_pairs[:20]:
#     print(pair)

# coins = cryptocompare.get_coin_list()
#
# usdt_coins = [coin for coin in coins.values() if 'USDT' in coin.get('Symbol', '')]
#
# # 2. 获取BTC/USDT日K线
# btc_data = cryptocompare.get_historical_price_day('BTC', 'USDT', limit=30)
#
# # 转换为DataFrame
# df = pd.DataFrame(btc_data)
# df = df.drop(columns=['conversionType', 'conversionSymbol', 'volumeto', 'volumefrom'])
# df['date'] = pd.to_datetime(df['time'], unit='s')
# df = df.drop(columns=['time'])
# # df.set_index('date', inplace=True)
# print(df)
# print(1)

# print(f"共找到 {len(usdt_coins)} 个USDT交易对")

# # client = Client()
#
#
# print(data)
# 获取USDT交易对
# usdt_pairs = get_usdt_trading_pairs()
# print(f"找到 {len(usdt_pairs)} 个USDT交易对")
# for pair in usdt_pairs:  # 打印前10个
#     print(f"{pair['symbol']} - {pair['name']}")

#
# bs.login()
#
# start_date = "1970-01-01"
# # 获取所有历史K线数据（从上市日期至今）
# rs = bs.query_history_k_data_plus(
#     code='sh.000004',
#     fields="date,open,close,high,low,volume",  # 字段可调整
#     start_date='2020-06-06',  # 尽可能早的日期
#     end_date='2025-06-06',  # 未来日期确保覆盖最新数据
#     frequency='w',  # d=日线，w=周线，m=月线
#     adjustflag="2"  # 复权类型：3=后复权  复权类型，默认不复权：3；1：后复权；2：前复权
# )
# data_list = []
# while (rs.error_code == '0') & rs.next():
#     data_list.append(rs.get_row_data())
#
# df = pd.DataFrame(data_list, columns=rs.fields)
# print(df)
#
# bs.logout()
