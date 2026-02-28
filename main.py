import akshare as ak
import pandas as pd
import baostock as bs
from datetime import datetime, timedelta

# 接口名称	核心特点与适用人群	主要数据范围	获取方式/费用
# AData 	专注A股的免费库，数据源融合多家公开渠道（如东方财富、同花顺），覆盖面不错。适合个人开发者、学生快速获取A股数据。	A股股票、ETF、可转债的行情、财务数据、板块概念、资金流、宏观数据等 。	开源免费。通过pip install adata安装，Python库直接调用 。
# QuantDataCollector 	旨在提供统一的数据接口，封装了baostock、tushare等底层库，并支持MySQL缓存，方便搭建本地数据库。	股票基本信息、日线行情、每日指标（PE/PB）、涨跌停板数据、同花顺板块等 。	开源免费。通过pip install QuantDataCollector安装，支持数据缓存 。
# iTick 	主打免费实时行情的API服务，提供WebSocket和RESTful接口，延迟低，适合需要实时监控或尝试高频策略的个人开发者。	提供A股、港美股实时行情，Level-2深度数据，以及15年历史K线 。	提供永久免费套餐。通过注册获取API Token，使用标准HTTP/WebSocket接口调用 。
#

# 接口名称	核心特点与适用人群	主要数据范围	获取方式/费用
# 上证所信息网络有限公司 (上证智能数据) 	官方背景，数据源最权威、最纯净。提供云端资源租用和数据服务，保障数据安全和系统独立。	上海证券交易所的Level-1、Level-2历史及实时行情、基础数据、公告数据等 。	商业付费，面向机构客户。提供云端服务和数据订阅服务 。
# 天软科技 (TinySoft) 	提供专业量化因子库，涵盖大量经过清洗和计算的因子数据（5000+个因子），可直接用于模型构建，省去自行计算因子的麻烦。	覆盖股票、债券、基金等多品类的量化因子数据、因子评价数据 。	商业付费。提供Web API、数据包等多种交付方式 。

# bs.login()
# rs = bs.query_history_k_data_plus(
#     code='sh.000001',
#     fields="date",  # 字段可调整
#     start_date='1988-01-01',  # 尽可能早的日期
#     end_date='2050-12-31',  # 未来日期确保覆盖最新数据
#     frequency='w',  # d=日线，w=周线，m=月线
#     adjustflag="2"  # 复权类型：3=后复权  复权类型，默认不复权：3；1：后复权；2：前复权
# )
# data_list = []
# while (rs.error_code == '0') & rs.next():
#     data_list.append(rs.get_row_data())
#
# df = pd.DataFrame(data_list, columns=rs.fields)
# start_date = df['date'].iloc[-102]
# end_date = df['date'].iloc[-1]
#
# bs.logout()

# 登录baostock
lg = bs.login()

stock_list = bs.query_stock_basic()
stock_df = stock_list.get_data()
filtered_stocks = stock_df[
    (stock_df['type'].isin(['1', '5'])) &  # type为1或5 1 是股票  5 是ETF
    (stock_df['status'] == '1') &  # 在交易
    (~stock_df['code_name'].str.contains('ST|\\*ST|退|警示|终止上市', na=False))  # 排除ST股和问题股
]

# # 获取股票代码列表
# codes_only = filtered_stocks['code'].tolist()

# print(len(codes_only))
# print(len(stock_df))
# 获取股票信息
# 获取全部A股股票，status：上市状态，'1'表示上市
