import string
import time

import akshare as ak
from collections import Counter

import numpy as np
from ta.trend import MACD
import threading
from queue import Queue
import pandas as pd

import pymongo
from datetime import datetime

import subprocess
import sys


class XShare:
    """ 道 """
    # 滑动窗口 窗口越大 分析的结果有可能越多 合理调整  4是比较合理的
    __WINDOW_SIZE = 4
    # 记录数
    __RECORD_COUNT = 150
    # 上市天数
    __ON_MARKET_DAYS = 400
    # 创新低天数
    __NEW_LOW_DAYS = 30

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
        filtered_elements = [element for element, count in count_dict.items() if count > nCount]
        return filtered_elements

    @staticmethod
    def __getWavePoints(records, subWindowSize, high_flag, low_flag):
        """
        计算波段的高低点
        :param records:  要计算的记录
        :param subWindowSize: 滑动窗口
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

        for i in range(len(highs) - XShare.__WINDOW_SIZE + 1):
            # 获取当前窗口的数据
            window_high = highs[i:i + XShare.__WINDOW_SIZE]
            window_low = lows[i:i + XShare.__WINDOW_SIZE]

            # 计算窗口内的最高点和最低点的索引
            high_index = window_high.index(max(window_high)) + i
            low_index = window_low.index(min(window_low)) + i

            # 保存结果
            window_highs_index.append(high_index)
            window_lows_index.append(low_index)

        wave_highs_index = XShare.__extractFrequentElements(window_highs_index, subWindowSize)
        wave_lows_index = XShare.__extractFrequentElements(window_lows_index, subWindowSize)

        # 再把计算结果反转过来
        for i in range(len(wave_highs_index)):
            wave_highs_index[i] = XShare.__RECORD_COUNT - wave_highs_index[i] - 1

        for i in range(len(wave_lows_index)):
            wave_lows_index[i] = XShare.__RECORD_COUNT - wave_lows_index[i] - 1

        wave_highs_index = wave_highs_index[::-1]
        wave_lows_index = wave_lows_index[::-1]
        return wave_highs_index, wave_lows_index

    @staticmethod
    def back_test(code, end_date, market=0):
        """
        回测用
        :param code: 代码
        :param end_date: 结束时间
        :param market: 市场代码  0 或  1   默认0 中国A股 1 港股
        :return:
        """
        return XShare.__analyze_single(code, market, end_date)

    @staticmethod
    def __strategy_bottomUpFlip(df_tail_150, stock_info):
        """
        :param df_tail_150:   最近 150天的交易记录
        :param stock_info:    需要用到的列  low high ...
        :return:  bool
        """
        if not stock_info:
            return False

        today_high = stock_info.get('today_high')
        today_low = stock_info.get('today_low')
        yesterday_high = stock_info.get('yesterday_high')
        yesterday_low = stock_info.get('yesterday_low')
        str_high = stock_info.get('str_high')
        str_low = stock_info.get('str_low')

        if yesterday_high > today_high:
            return False

        # 获取需要的时间窗口
        nSubWindow = [i for i in range(2, XShare.__WINDOW_SIZE)]

        for n in nSubWindow:

            wave_info = XShare.__get_wave_info(df_tail_150, n, str_high, str_low)

            if not wave_info:
                return False

            preHighIndex = wave_info.get('preHighIndex')
            preLowIndex = wave_info.get('preLowIndex')

            preHighPrice = wave_info.get('preHighPrice')
            preLowPrice = wave_info.get('preLowPrice')
            preLow2Price = wave_info.get('preLow2Price')

            # 当天过高点
            if today_high <= preHighPrice:
                continue
            # 昨天没过高点
            if yesterday_high >= preHighPrice:
                continue

            if today_low < preLowPrice:
                preLowPrice = today_low
                preLowIndex = XShare.__RECORD_COUNT - 1
            if yesterday_low < preLowPrice:
                preLowIndex = XShare.__RECORD_COUNT - 2
                preLowPrice = yesterday_low

            # 前低索引要大
            if preHighIndex > preLowIndex:
                continue

            # 判断是不是破底翻
            if preLowPrice > preLow2Price:
                continue

            macd = MACD(close=df_tail_150[stock_info.get('str_close')], window_fast=12, window_slow=26, window_sign=9)

            if len(macd.macd_diff()) < preHighIndex or len(macd.macd_diff()) < preLowIndex:
                continue
            pre_high_dea = macd.macd_signal().iloc[preHighIndex]

            if pre_high_dea > 0:
                continue

            # 获取最低点向前的N条记录
            subset = df_tail_150.iloc[preLowIndex - XShare.__NEW_LOW_DAYS: preLowIndex]
            min_last_N = subset[str_low].min()
            if preLowPrice <= min_last_N:
                return True
        return False

    @staticmethod
    def __strategy_double_bottom(df_tail_150, stock_info):
        """
         双底
        :param df_tail_150:
        :param stock_info:
        :return:bool
        """
        # 当天低点 和前低 差不多
        # 高点到今天要是MACD 红柱
        pass

    @staticmethod
    def __get_wave_info(df_tail_150, sub_window, str_high, str_low):
        # 获取波段信息
        highs_index, lows_index = XShare.__getWavePoints(df_tail_150, sub_window, str_high, str_low)

        if len(highs_index) < 2 or len(highs_index) < 2:
            return {}

        preHighIndex = highs_index[-1]
        preLowIndex = lows_index[-1]
        preLow2Index = lows_index[-2]

        wave_info = {
            'preHighIndex': highs_index[-1],
            'preLowIndex': lows_index[-1],
            'preLow2Index': lows_index[-2],
            'preHighPrice': df_tail_150.iloc[preHighIndex][str_high],
            'preLowPrice': df_tail_150.iloc[preLowIndex][str_low],
            'preLow2Price': df_tail_150.iloc[preLow2Index][str_low],
        }
        return wave_info

    @staticmethod
    def __analyze_single(code, socket_market, end_date=''):

        str_high = '最高' if socket_market == 0 else 'high'
        str_low = '最低' if socket_market == 0 else 'low'
        str_open = '开盘' if socket_market == 0 else 'open'
        str_close = '收盘' if socket_market == 0 else 'close'
        str_date = '日期' if socket_market == 0 else 'date'
        str_volume = '成交量' if socket_market == 0 else 'volume'

        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if socket_market == 1:
                df = ak.stock_hk_daily(symbol=code, adjust="qfq")

            if socket_market == 0:
                if not XShare.__filteringCode(code):
                    return False

            if len(df) < XShare.__RECORD_COUNT:
                return False

            # 判断是否需要回测
            if len(end_date) == 0:
                df_tail_150 = df.tail(XShare.__RECORD_COUNT)
            else:
                df['date'] = pd.to_datetime(df[str_date])  # 转换日期列
                target_date = pd.to_datetime(end_date)
                # target_date = pd.to_datetime('2024-05-06')
                target_index = df[df['date'] == target_date].index[0]  # 获取该日期的行索引
                start_index = max(0, target_index - (XShare.__RECORD_COUNT - 1))  # 确保不越界（150条含目标日）
                df_tail_150 = df.iloc[start_index: target_index + 1]  # 包含目标日

            today_doc = df_tail_150.iloc[-1]
            yesterday_doc = df_tail_150.iloc[-2]

            # 分析需要用到的信息
            stock_info = {
                'today_open': today_doc[str_open],
                'today_close': today_doc[str_close],
                'today_high': today_doc[str_high],
                'today_low': today_doc[str_low],
                'yesterday_high': yesterday_doc[str_high],
                'yesterday_low': yesterday_doc[str_high],
                'str_open': str_open,
                'str_close': str_close,
                'str_high': str_high,
                'str_low': str_low,
            }

            # today_tVolume = today_doc['成交额'] if socket_market == 0 else today_doc[str_volume] * today_doc["low"]
            #
            # # 成交额 小于 5千万的 不要
            # if today_tVolume < 50000000:
            #     return False

            # 破低翻
            if XShare.__strategy_bottomUpFlip(df_tail_150, stock_info):
                return 1

            return False
        except Exception as e:
            print(f"股票代码 {code} 处理失败，错误: {e}")
            return False

    @staticmethod
    def analysisA(market=0):

        stocks_df = ak.stock_zh_a_spot_em() if market == 0 else ak.stock_hk_spot_em()
        stocks_df = stocks_df.dropna(subset=['今开'])
        stocks_df = stocks_df.dropna(subset=['成交量'])

        # A股
        if market == 0:
            # 获取 ST 股票
            st_stocks_df = ak.stock_zh_a_st_em()
            stocks_df = stocks_df[~stocks_df['代码'].isin(st_stocks_df['代码'])]

        stock_codes = stocks_df['代码'].to_list()

        # 将股票代码分组
        groups = np.array_split(stock_codes, max(1, len(stock_codes) // 10))

        # 用于存储结果的队列
        result_queue = Queue()

        start_time = time.time()
        # 线程列表
        threads = []

        def worker(stock_group, socket_market):
            results = []
            for code in stock_group:
                ret = XShare.__analyze_single(code, socket_market)
                if ret in {1, 2, 3}:
                    results.append((ret, code))
            result_queue.put(results)

        # 创建并启动线程
        for group in groups:
            t = threading.Thread(target=worker, args=(group, market))
            t.start()
            threads.append(t)

        # 等待所有线程完成
        for t in threads:
            t.join()

        # # 收集所有结果
        analysis_results = []
        while not result_queue.empty():
            analysis_results.extend(result_queue.get())

        str_results = [(x, str(y)) for x, y in analysis_results]

        elapsed = time.time() - start_time
        print(f"\n分析完成! 总耗时: {elapsed:.2f}秒")
        return str_results


def analysisAndSave(market=0):
    # 输出的文件路径
    file_path = "D:\\Users\\Administrator\\Desktop\\stock.txt"

    print('update akshare...')
    subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
    # 安装或升级 akshare
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "akshare"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)

    print('begin analyzing....')
    resultA = XShare.analysisA(market)

    # 处理分析结果 使用字典来存储分组结果
    groups = {}
    for num, code in resultA:
        if num not in groups:
            groups[num] = []
        groups[num].append(code)

    # 提取分组
    group1 = groups.get(1, [])
    group2 = groups.get(2, [])

    mongoDBCli = pymongo.MongoClient("mongodb://dbroot:123456ttqqTTQQ@113.44.193.120:28018/")
    db = mongoDBCli['ashare']

    # 分析结果的集合
    coll_analysis_Results = db['analysis_results']

    data = {
        "type1": group1,
        "type2": group2,
        "analysis_date": datetime.now()
    }
    # 把数据写入到数据库
    coll_analysis_Results.insert_one(data)

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
    # 回测用
    # print(XShare.back_test('600529', '2024-12-10'))
    # print(XShare.back_test('605136', '2024-07-12'))
    # 开始分析  0 是分析A股  1 是分析港股
    analysisAndSave(0)
