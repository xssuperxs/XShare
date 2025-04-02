import math
import string
import time

import akshare as ak
from collections import Counter

import numpy as np
from ta.trend import MACD
import threading
from queue import Queue
import pandas as pd


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
        # 计算每个元素出现的次数
        count_dict = Counter(input_list)
        # 筛选出出现次数大于3的元素
        filtered_elements = [element for element, count in count_dict.items() if count > nCount]
        return filtered_elements

    @staticmethod
    def __getWavePoints(records, subWindowSize, high_flag, low_flag):
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
        return XShare.__analyze_single(code, market, end_date)

    @staticmethod
    def __analyze_single(code, socket_market, end_date=''):
        try:
            df = pd.DataFrame()
            str_high = ''
            str_low = ''
            str_close = ''
            date_loc = ''
            if socket_market == 0:
                if not XShare.__filteringCode(code):
                    return False
                df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
                str_high = '最高'
                str_low = '最低'
                str_close = '收盘'
                date_loc = '日期'
            if socket_market == 1:
                df = ak.stock_hk_daily(symbol=code, adjust="qfq")
                str_high = 'high'
                str_low = 'low'
                str_close = 'close'
                date_loc = 'date'

            if len(df) < XShare.__RECORD_COUNT:
                return False

            # 判断是否需要回测
            if len(end_date) == 0:
                df_tail_150 = df.tail(XShare.__RECORD_COUNT)
            else:
                df['date'] = pd.to_datetime(df[date_loc])  # 转换日期列
                target_date = pd.to_datetime(end_date)
                # target_date = pd.to_datetime('2024-05-06')
                target_index = df[df['date'] == target_date].index[0]  # 获取该日期的行索引
                start_index = max(0, target_index - (XShare.__RECORD_COUNT - 1))  # 确保不越界（150条含目标日）
                df_tail_150 = df.iloc[start_index: target_index + 1]  # 包含目标日

            # 转成字典
            df_dict = df_tail_150.to_dict(orient='records')

            today_doc = df_dict[-1]
            pre_doc = df_dict[-2]
            if pre_doc[str_high] > today_doc[str_high]:
                return False

            stock_info = {}
            nSubWindow = [2, 3]
            for n in nSubWindow:
                stock_info.clear()
                highs_index, lows_index = XShare.__getWavePoints(df_tail_150, n, str_high, str_low)

                if len(highs_index) < 2 or len(highs_index) < 2:
                    return False

                preHighIndex = highs_index[-1]
                preLowIndex = lows_index[-1]
                preLow2Index = lows_index[-2]

                preHighPrice = df_dict[preHighIndex][str_high]
                preLowPrice = df_dict[preLowIndex][str_low]
                preLow2Price = df_dict[preLow2Index][str_low]

                if today_doc[str_high] <= preHighPrice:
                    continue

                if pre_doc[str_high] >= preHighPrice:
                    continue

                if preHighIndex > preLowIndex:
                    today_low = today_doc[str_low]
                    pre_low = pre_doc[str_low]
                    if today_low > preLowPrice or pre_low > preLowPrice:
                        continue
                    if today_low < pre_low:
                        preLowPrice = today_low
                        preLowIndex = XShare.__RECORD_COUNT - 1
                    else:
                        preLowIndex = XShare.__RECORD_COUNT - 2
                        preLowPrice = pre_low
                else:
                    if preLowPrice > preLow2Price:
                        continue

                macd = MACD(close=df_tail_150[str_close], window_fast=12, window_slow=26, window_sign=9)

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
        except Exception as e:
            # 捕获所有异常并打印错误信息
            print(f"股票代码 {code} 处理失败，错误: {e}")
            return False
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
        # 用于存储结果的队列
        result_queue = Queue()

        start_time = time.time()
        # 线程列表
        threads = []

        def worker(stock_group, socket_market):
            results = []
            for code in stock_group:
                if XShare.__analyze_single(code, socket_market):
                    results.append(code)
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


file_path = "D:\\Users\\Administrator\\Desktop\\stock.txt"

if __name__ == '__main__':
    ret = XShare.back_test('600529', '2024-12-11')
    print(ret)

    # resultA = XShare.analysisA()
    # with open(file_path, 'w') as file:
    #     # 将数组的每个元素写入文件，每个元素占一行
    #     for item in resultA:
    #         file.write(f'{item}\n')
    #
    # print("A股分析结果:", resultA)
