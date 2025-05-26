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


class XShare:
    """ 道 """
    # 滑动窗口 窗口越大 分析的结果有可能越多 合理调整  4是比较合理的
    __WINDOW_SIZE = 7
    # 记录数
    __RECORD_COUNT = 150
    # 上市天数
    __ON_MARKET_DAYS = 400
    # 创新低天数
    __NEW_LOW_DAYS = 18

    # 缓存文件
    __A_DAILY_FILE = 0
    __A_WEEKLY_FILE = 1
    __AH_DAILY_FILE = 2

    __STOCK_CACHE_FILE_DICT = {
        0: 'A_daily.csv',
        1: 'A_weekly.csv',
        2: 'AH_daily.csv'
    }

    @staticmethod
    def __filteringCode(stock_code: string):
        """
        过滤A股股票
        :param stock_code: code
        :return: true
        """
        if stock_code.startswith('8'):
            return False
        if stock_code.startswith('4'):
            return False
        if stock_code.startswith('9'):
            return False
        if stock_code.startswith('688'):
            return False
        return True

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
    def back_test(code, end_date, period='daily'):
        """
        测试用
        :param period: 周期
        :param code: 代码
        :param end_date: 结束时间
        :return: 失败False  成功 类型码
        """
        return XShare.__analyze_single(code, 0, period, end_date)

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
    def __analyze_single(code, socket_market, period='daily', end_date=''):

        column_mapping = {
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
        }
        if period == 'weekly':
            XShare.__RECORD_COUNT = 100

        try:
            df = pd.DataFrame()
            if socket_market == 0:
                df = ak.stock_zh_a_hist(symbol=code, period=period, adjust="qfq")
                # 过滤掉不需要的 科创板 北证
                if not XShare.__filteringCode(code):
                    return False
                # A 股重新命名列  统一成英文的列名
                df = df.rename(columns=column_mapping)

            if socket_market == 1:
                df = ak.stock_hk_daily(symbol=code, adjust="qfq")

            if len(df) < XShare.__RECORD_COUNT:
                return False

            # 判断是否需要回测
            if len(end_date) == 0:
                df_tail_150 = df.tail(XShare.__RECORD_COUNT)
            else:
                df['date'] = pd.to_datetime(df['date'])  # 转换日期列
                target_date = pd.to_datetime(end_date)
                target_index = df[df['date'] == target_date].index[0]  # 获取该日期的行索引
                start_index = max(0, target_index - (XShare.__RECORD_COUNT - 1))  # 确保不越界（150条含目标日）
                df_tail_150 = df.iloc[start_index: target_index + 1]  # 包含目标日

            # 破低翻
            if XShare.__strategy_bottomUpFlip(df_tail_150, period):
                return 1

            return False
        except Exception as e:
            print(f"股票代码 {code} 处理失败，错误: {e}")
            return False

    @staticmethod
    def __thread_analysis(stock_codes, stock_market, period):
        # 将股票代码分组
        groups = np.array_split(stock_codes, len(stock_codes) // 2)

        # 用于存储结果的队列
        result_queue = Queue()

        # 开始分析的时间
        start_time = time.time()
        # 线程列表
        threads = []

        # 速率限制相关变量
        rate_limit = 10  # 每秒最多10次调用
        last_call_time = 0
        rate_lock = threading.Lock()

        def worker(stock_group, tp_stock_market, tp_period):
            nonlocal last_call_time
            ana_results = []
            for code in stock_group:
                # 速率控制
                with rate_lock:
                    # 计算需要等待的时间
                    isElapsed = time.time() - last_call_time
                    if isElapsed < 1.0 / rate_limit:
                        time.sleep((1.0 / rate_limit) - isElapsed)
                    last_call_time = time.time()

                ret = XShare.__analyze_single(code=code, socket_market=tp_stock_market, period=tp_period, end_date='')
                if ret in {1, 2, 3}:
                    ana_results.append((ret, code))
            result_queue.put(ana_results)

        # 创建并启动线程
        for group in groups:
            t = threading.Thread(target=worker, args=(group, stock_market, period))
            t.start()
            threads.append(t)

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 收集所有结果
        analysis_results = []
        while not result_queue.empty():
            analysis_results.extend(result_queue.get())

        str_results = [(x, str(y)) for x, y in analysis_results]

        elapsed = time.time() - start_time
        print(f"\n分析完成! 总耗时: {elapsed:.2f}秒")
        return str_results

    @staticmethod
    def __get_stock_codes(market=0):
        stocks_df = ak.stock_zh_a_spot_em() if market == 0 else ak.stock_hk_spot_em()
        stocks_df = stocks_df.dropna(subset=['今开'])
        stocks_df = stocks_df.dropna(subset=['成交量'])
        if market == 0:
            # 过滤掉ST
            st_stocks_df = ak.stock_zh_a_st_em()
            stocks_df = stocks_df[~stocks_df['代码'].isin(st_stocks_df['代码'])]
        return stocks_df['代码'].to_list()

    @staticmethod
    def analysisA(period='daily'):
        """
          分析A股 各股
        """
        return XShare.__thread_analysis(XShare.__get_stock_codes(0), 0, period)

    @staticmethod
    def analysisAIndex(period='daily'):
        """
        分析A股各个板块的指数
        """
        return XShare.__thread_analysis(XShare.__get_stock_codes(0), 0, period)

    @staticmethod
    def analysisAH():
        """
          分析港股
        """
        return XShare.__thread_analysis(XShare.__get_stock_codes(1), 1, period='daily')

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

    groups = {}
    for num, code in result:
        if num not in groups:
            groups[num] = []
        groups[num].append(code)

    # 提取分组
    group1 = groups.get(1, [])

    print("破底翻 ", len(group1), '只:', group1)

    # 只输出破底翻
    out_results = group1
    # 输出3全部的分析结果 3种全保留
    # out_results = group1 + group2

    with open(file_path, 'w') as file:
        # 将数组的每个元素写入文件，每个元素占一行
        for item in out_results:
            file.write(f'{item}\n')


if __name__ == '__main__':
    test = False
    if test:
        # 回测用
        print(XShare.back_test('002317', '2025-04-22', period='daily'))
    else:
        XShare.update_packet()
        # 分析A股
        results = XShare.analysisA()
        # 分析AH股 港股
        # aResult = XShare.analysisAH()
        # 处理分析结棍
        handle_results(results)
