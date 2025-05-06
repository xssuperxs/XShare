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
    # 滑动窗口
    __WINDOW_SIZE = 4
    # 记录数
    __RECORD_COUNT = 150
    # 上市天数
    __ON_MARKET_DAYS = 400
    # 创新低天数
    __NEW_LOW_DAYS = 30

    # 过滤股票代码
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
    def __strategy_bottomUpFlip(df_tail_150, stock_info: dict):
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

        nSubWindow = [2, 3]
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
            min_last_N = subset[stock_info.get('str_low')].min()
            if preLowPrice <= min_last_N:
                return True
        return False

    @staticmethod
    def __get_wave_info(df_tail_150, sub_window, str_high, str_low):
        # 获取波段
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
    def __strategy_double_bottom(df_tail_150, stock_info: dict, socket_market):

        pass

    @staticmethod
    def __strategy_new_high(df_tail_150, stock_info: dict, socket_market):
        """
        创新高 试盘
        :param df_tail_150:
        :param stock_info:
        :param socket_market:
        :return:
        """
        if not stock_info:
            return False

        today_high = stock_info.get('today_high')
        today_close = stock_info.get('today_close')

        # 用3的子窗口
        wave_info = XShare.__get_wave_info(df_tail_150, 3, stock_info.get('str_high'), stock_info.get('str_low'))

        if today_high < wave_info.get('preHighPrice'):
            return False
        if stock_info.get('yesterday_high') >= wave_info.get('preHighPrice'):
            return False

        # 冲商回落
        is_pullback = (today_high - today_close) * 1.6 > abs(today_high - stock_info.get('today_low'))
        # 高开低走
        is_high_to_low = today_close < stock_info.get('today_open')
        if is_pullback or is_high_to_low:
            return True

        return False

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

            # 获取股票参数
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
            today_trading_volume = today_doc['成交额'] if socket_market == 0 else today_doc[str_volume] * today_doc[
                "low"]

            if today_trading_volume < 60000000:
                return False

            # 破低翻
            if XShare.__strategy_bottomUpFlip(df_tail_150, stock_info):
                return 1
            # # 双底
            # if XShare.__strategy_double_bottom(df_tail_150, stock_info_dict, socket_market):
            #     return 2
            # # 创新高试盘
            # if XShare.__strategy_new_high(df_tail_150, stock_info_dict, socket_market):
            #     return 3
            return False
        except Exception as e:
            print(f"股票代码 {code} 处理失败，错误: {e}")
            return False

    @staticmethod
    def analysisA(market=0):
        stock_codes = []
        # A股
        if market == 0:
            # 获取 ST 股票
            st_stocks_df = ak.stock_zh_a_st_em()
            st_stocks_list = st_stocks_df['代码'].to_list()

            # 获取当日所有股票代码A股
            df_em = ak.stock_zh_a_spot_em()
            df_em = df_em.dropna(subset=['今开'])
            em_stocks_list = df_em['代码'].to_list()

            stock_codes = list(set(em_stocks_list) - set(st_stocks_list))
        # 港股
        if market == 1:
            stock_hk_df = ak.stock_hk_spot_em()
            stock_hk_df = stock_hk_df.dropna(subset=['今开'])
            stock_hk_df = stock_hk_df.dropna(subset=['成交量'])
            stock_hk_df = stock_hk_df.dropna(subset=['成交额'])
            stock_codes = stock_hk_df['代码'].to_list()

        # 将股票代码分组
        groups = np.array_split(stock_codes, max(1, len(stock_codes) // 10))
        # groups = np.array_split(stock_codes, 1)
        # print(len(groups))
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

        # 收集所有结果
        final_results = []
        while not result_queue.empty():
            final_results.extend(result_queue.get())

        # 使用 item() 方法转换
        str_results = [x.item() for x in final_results]

        elapsed = time.time() - start_time
        print(f"\n分析完成! 总耗时: {elapsed:.2f}秒")
        return str_results


def analysisAndSave(market=0):
    file_path = "D:\\Users\\Administrator\\Desktop\\stock.txt"
    resultA = XShare.analysisA(market)
    mongoDBCli = pymongo.MongoClient("mongodb://dbroot:123456ttqqTTQQ@113.44.193.120:28018/")
    db = mongoDBCli['ashare']

    # 分析结果的集合
    coll_analysis_Results = db['analysis_results']

    data = {
        "type1": resultA,
        "type2": [],
        "analysis_date": datetime.now()
    }
    # 把数据写入到数据库
    coll_analysis_Results.insert_one(data)

    print("股票个数:", len(resultA))
    with open(file_path, 'w') as file:
        # 将数组的每个元素写入文件，每个元素占一行
        for item in resultA:
            file.write(f'{item}\n')

    print("股票列表:", resultA)


# pip install akshare --upgrade
def update_packet():
    """
    更新需要的包
    :return:
    """
    subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
    # 安装或升级 akshare
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "akshare"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    # 更新 akshare
    update_packet()
    # 回测用
    # print(XShare.back_test('000100', '2025-04-29'))
    print(XShare.back_test('605136', '2024-07-12'))
    # 开始分析
    # analysisAndSave(0)
