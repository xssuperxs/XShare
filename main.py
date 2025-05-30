import time

import akshare as ak
import pandas as pd
import baostock as bs
import csv
from tqdm import tqdm

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


def get_klines_baostock(code, period='d'):
    stock_prefix = ''
    if code.startswith(('6', '9', '688')):  # 上海: 6/688/900
        stock_prefix = 'sh.'
    elif code.startswith(('0', '3', '2')):  # 深圳: 0/3/200
        stock_prefix = 'sz.'
    if stock_prefix == '':
        return pd.DataFrame()
    code = stock_prefix + code

    # 获取所有历史K线数据（从上市日期至今）
    rs = bs.query_history_k_data_plus(
        code=code,
        fields="date,open,close,high,low,volume",  # 字段可调整
        start_date="1990-01-01",  # 尽可能早的日期
        end_date="2030-12-31",  # 未来日期确保覆盖最新数据
        frequency=period,  # d=日线，w=周线，m=月线
        adjustflag="2"  # 复权类型：3=后复权  复权类型，默认不复权：3；1：后复权；2：前复权
    )
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())

    df = pd.DataFrame(data_list, columns=rs.fields)
    if df.empty:
        return df

    float_cols = ['open', 'close', 'high', 'low', 'volume']
    # 转换并保留两位小数
    df[float_cols] = df[float_cols].apply(pd.to_numeric, errors='coerce').round(2)
    return df


def update_stock_cache(stock_market):
    # 确保cache目录存在
    cache_dir = 'cache'
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    filename = __STOCK_CACHE_FILE_DICT.get(stock_market)
    # 构建完整的文件路径
    file_path = os.path.join(cache_dir, filename)

    # 判断文件是不是存在
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=['code', 'date', 'open', 'close', 'high', 'low', 'volume'])  # 定义列名
        df.to_csv(file_path, index=False)  # 保存为CSV（不保留索引）

    dtype_dict = {
        'code': str,  # 或者 'object'
        'open': float,
        'close': float,
        'high': float,
        'low': float,
        'volume': float
    }
    cache_df = pd.read_csv(file_path, dtype=dtype_dict)
    cache_df['date'] = pd.to_datetime(cache_df['date'])

    sh_index_daily = ak.stock_zh_index_daily(symbol="sh000001")

    print(type(sh_index_daily))
    # 取最新一条记录
    last_date = sh_index_daily['date'].iloc[-1]
    previous_trading_day = sh_index_daily['date'].iloc[-2]

    # 以上是获取日期
    stocks_df = ak.stock_zh_a_spot_em()
    stocks_df = stocks_df.dropna(subset=['今开'])
    stocks_df = stocks_df.dropna(subset=['成交量'])
    if stock_market == 0:
        # 0代表A股
        # 过滤掉ST
        st_stocks_df = ak.stock_zh_a_st_em()
        stocks_df = stocks_df[~stocks_df['代码'].isin(st_stocks_df['代码'])]
        # stocks_df = stocks_df[stocks_df['最高'] > stocks_df['昨收']]
        # column_mapping = {
        #     "代码": "code",
        #     "今开": "open",
        #     "最高": "high",
        #     "最低": "low",
        #     "最新价": "close",
        #     "成交量": "volume",
        # }
        # available_columns = [col for col in column_mapping.keys() if col in stocks_df.columns]
        # stocks_df = stocks_df[available_columns].rename(columns=column_mapping)

        stocks_codes = stocks_df['代码'].to_list()

        # print(type(stocks_codes))
        for code in tqdm(stocks_codes, desc="A股 分析进度 ", unit="只"):
            if code in cache_df["code"].values:
                pass
            else:
                print(code)
                df = get_klines_baostock(code, period='d')
                if df.empty:
                    continue
                # 判断是否需要回测
                df_tail_100 = df.tail(100)

                df_tail_100.insert(0, 'code', code)

                pd.concat([cache_df, df_tail_100], axis=0)
                # df_tail_150.to_csv(file_path, mode='a', header=False, index=False, encoding='utf-8-sig')
        # 打印
        print(cache_df)
        print(len(cache_df))
        cache_df.to_csv(file_path, index=False, encoding='utf-8-sig')

        print("===================end==========================")
        # print(stocks_codes)
        # print(len(stocks_codes))

    # 创建好文件后  把需要的数据写进去


if __name__ == '__main__':
    lg = bs.login()  # 登录系统
    aaaccc = 'sz.688124'
    pattern = r"\.9|\.8|\.4|\.688"

    print(aaaccc.contains(pattern, regex=True))
    # update_stock_cache(0)
    bs.logout()
