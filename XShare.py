import string
import time

import akshare as ak
from collections import Counter

import numpy as np
from ta.trend import MACD
import threading
from queue import Queue
import pandas as pd

import subprocess
import sys
import time
import baostock as bs
from tqdm import tqdm


class XShare:
    """   """
    # 滑动窗口 窗口越大 分析的结果有可能越多 合理调整  4是比较合理的
    __WINDOW_SIZE = 7
    # 记录数
    __RECORD_COUNT = 100
    # 上市天数
    __ON_MARKET_DAYS = 400
    # 创新低天数
    __NEW_LOW_DAYS = 18

    @staticmethod
    def __extractFrequentElements(input_list: list, nCount: int) -> list:
        """
        提取波段的高低点
        :param input_list: high or low  list
        :param nCount: 滑动窗口
        :return: 提取好的 list
        """
        # 计算每个元素出现的次数
        count_dict = Counter(input_list)
        # 筛选出出现次数大于3的元素
        filtered_elements = [element for element, count in count_dict.items() if count >= nCount]
        return filtered_elements

    @staticmethod
    def __getWavePoints(records, window_size, high_flag, low_flag):
        """
        计算波段的高低点
        :param records:  要计算的记录
        :param window_size: 滑动窗口
        :param high_flag:  最高价 字段的 名称
        :param low_flag:   最低价 字段的 名称
        :return:
        """

        # 开始提出150条数据 进行计算
        window_highs_index = []
        window_lows_index = []

        highs = records[high_flag].to_list()
        lows = records[low_flag].to_list()

        highs = highs[::-1]
        lows = lows[::-1]

        for i in range(len(highs) - window_size + 1):
            # 获取当前窗口的数据
            window_high = highs[i:i + window_size]
            window_low = lows[i:i + window_size]

            # 计算窗口内的最高点和最低点的索引
            high_index = window_high.index(max(window_high)) + i
            low_index = window_low.index(min(window_low)) + i

            # 保存结果
            window_highs_index.append(high_index)
            window_lows_index.append(low_index)

        wave_highs_index = XShare.__extractFrequentElements(window_highs_index, window_size)
        wave_lows_index = XShare.__extractFrequentElements(window_lows_index, window_size)

        # 再把计算结果反转过来
        for i in range(len(wave_highs_index)):
            wave_highs_index[i] = XShare.__RECORD_COUNT - wave_highs_index[i] - 1

        for i in range(len(wave_lows_index)):
            wave_lows_index[i] = XShare.__RECORD_COUNT - wave_lows_index[i] - 1

        wave_highs_index = wave_highs_index[::-1]
        wave_lows_index = wave_lows_index[::-1]
        return wave_highs_index, wave_lows_index

    @staticmethod
    def back_test(code, end_date, period='d'):
        """
        测试用
        :param period: 周期
        :param code: 代码
        :param end_date: 结束时间
        :return: 失败False  成功 类型码
        """
        df = XShare.__get_kline_info(code, period)
        df['date'] = pd.to_datetime(df['date'])  # 转换日期列
        target_date = pd.to_datetime(end_date)
        target_index = df[df['date'] == target_date].index[0]  # 获取该日期的行索引
        start_index = max(0, target_index - (XShare.__RECORD_COUNT - 1))  # 确保不越界（150条含目标日）
        df_tail_150 = df.iloc[start_index: target_index + 1]  # 包含目标日

        return XShare.__strategy_bottomUpFlip(df_tail_150, period)

    @staticmethod
    def __get_kline_info(code, period='d'):
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

        float_cols = ['open', 'close', 'high', 'low', 'volume']
        # 转换并保留两位小数
        df[float_cols] = df[float_cols].apply(pd.to_numeric, errors='coerce').round(2)
        return df

    @staticmethod
    def __strategy_bottomUpFlip(df_klines: pd.DataFrame, period='daily') -> bool:
        """
        :param df_klines:   最近 N天的交易记录
        :return:  bool
        """

        today_doc = df_klines.iloc[-1]
        yesterday_doc = df_klines.iloc[-2]

        today_high = today_doc['high']
        today_low = today_doc['low']
        yesterday_high = yesterday_doc['high']
        yesterday_low = yesterday_doc['low']

        if yesterday_high > today_high:
            return False

        # 获取需要的时间窗口
        nSubWindow = [i for i in range(3, XShare.__WINDOW_SIZE)]

        for n in nSubWindow:

            # 获取波段的 高低点
            highs_index, lows_index = XShare.__getWavePoints(df_klines, n, 'high', 'low')

            if len(highs_index) < 2 or len(highs_index) < 2:
                continue

            preHighIndex = highs_index[-1]
            preLowIndex = lows_index[-1]
            preLow2Index = lows_index[-2]

            preHighPrice = df_klines.iloc[preHighIndex]['high']
            preLowPrice = df_klines.iloc[preLowIndex]['low']
            preLow2Price = df_klines.iloc[preLow2Index]['low']

            # 当天高点要过前高
            if today_high <= preHighPrice:
                continue
            # 昨天高点不能过前高
            if yesterday_high >= preHighPrice:
                continue

            if today_low < preLowPrice or yesterday_low < preLowPrice:
                preLow2Price = preLowPrice
                minPrice = min([today_low, yesterday_low])
                if minPrice == today_low:
                    preLowPrice = today_low
                    preLowIndex = XShare.__RECORD_COUNT - 1
                if minPrice == yesterday_low:
                    preLowIndex = XShare.__RECORD_COUNT - 2
                    preLowPrice = yesterday_low

            # 前低索引要大
            if preHighIndex > preLowIndex:
                continue

            # 判断是不是破底翻
            if preLowPrice > preLow2Price:
                continue

            # 如果是分析周线 这里直接返回True
            if period == 'weekly':
                return True

            macd = MACD(close=df_klines['close'], window_fast=12, window_slow=26, window_sign=9)
            pre_low_dea = macd.macd_signal().iloc[preLowIndex]
            if pre_low_dea > 0:
                continue

            # 获取最低点向前的N条记录
            subset = df_klines.iloc[preLowIndex - XShare.__NEW_LOW_DAYS: preLowIndex]
            n_day_low_price = subset['low'].min()
            if preLowPrice <= n_day_low_price:
                return True

        return False

    @staticmethod
    def __get_stock_codes(market=0):
        stocks_df = ak.stock_zh_a_spot_em() if market == 0 else ak.stock_hk_spot_em()
        stocks_df = stocks_df.dropna(subset=['今开'])
        stocks_df = stocks_df.dropna(subset=['成交量'])
        if market == 0:
            # 过滤掉ST 0代表A股
            st_stocks_df = ak.stock_zh_a_st_em()
            stocks_df = stocks_df[~stocks_df['代码'].isin(st_stocks_df['代码'])]
            stocks_df = stocks_df[stocks_df['最高'] > stocks_df['昨收']]
        return stocks_df['代码'].to_list()

    @staticmethod
    def analysisA(period='d'):
        """
        :param period:  d = 日K   w = 周K   m = 月K
        :return:  返回A股股票 分析的结果
        """
        codes = XShare.__get_stock_codes(0)
        ret_results = []

        # 使用 tqdm 包装循环，并设置中文描述
        for code in tqdm(codes, desc="A股 分析进度 ", unit="只"):
            # 过滤掉暂时不需要的代码
            if any(code.startswith(prefix) for prefix in ('8', '4', '9', '688')):
                continue
            # 提取K线信息
            df = XShare.__get_kline_info(code, period)
            if len(df) < XShare.__RECORD_COUNT or df.empty:
                continue
            # 提取需要N条K线
            df_klines = df.tail(XShare.__RECORD_COUNT)
            # 开始分析K线数据
            if XShare.__strategy_bottomUpFlip(df_klines, period):
                ret_results.append(code)
        return ret_results

    @staticmethod
    def analysisAIndex(period='d'):
        pass
        """
        分析A股行业指数
        """
        # return XShare.__thread_analysis(XShare.__get_stock_codes(0), 0, period)

    @staticmethod
    def update_packet():
        """
        更新 akshare
        :return:
        """
        print('update akshare...')
        subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
        # 安装或升级 akshare
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "akshare"],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)


def handle_results(result):
    # 输出的文件路径
    file_path = "D:\\Users\\Administrator\\Desktop\\stock.txt"

    print("分析结果! ", len(result), '只:', result)

    with open(file_path, 'w') as file:
        # 将数组的每个元素写入文件，每个元素占一行
        for item in result:
            file.write(f'{item}\n')


if __name__ == '__main__':
    lg = bs.login()  # 登录系统
    test = True
    if test:
        # 回测用
        print(XShare.back_test('300785', '2024-07-31', period='d'))
    else:
        XShare.update_packet()
        # 分析A股
        results = XShare.analysisA()
        handle_results(results)
    bs.logout()
