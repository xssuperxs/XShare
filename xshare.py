from collections import Counter
from ta.trend import MACD
import pandas as pd
import numpy as np
from collections import Counter


class KlinesAnalyzer:
    """
    主要分析是K线形态 是不是符合 过前高     check_pass_peak
    分析K线 形态 是否为阴线               check_real_bearish
    分析K线 形态 是否为仙人指路            check_highToLow
    """
    # 记录数
    __RECORD_COUNT = 90
    # 创新低天数
    __NEW_LOW_DAYS = 18

    @staticmethod
    def __getWavePoints(records, window_size, high_flag, low_flag):
        """
           计算波段的高低点
           :param records: 要计算的记录（DataFrame）
           :param window_size: 滑动窗口大小
           :param high_flag: 最高价字段名
           :param low_flag: 最低价字段名
           :return: (高点索引列表, 低点索引列表)
           """
        # 直接使用原始顺序，避免反转
        highs = records[high_flag].values
        lows = records[low_flag].values
        n_records = len(highs)

        # 预分配列表以提高性能
        window_highs_index = []
        window_lows_index = []

        # 使用numpy的argmax/argmin提高性能
        for i in range(n_records - window_size + 1):
            # 获取当前窗口的数据
            window_high = highs[i:i + window_size]
            window_low = lows[i:i + window_size]

            # 使用argmax和argmin获取相对索引，然后转换为全局索引
            high_rel_index = np.argmax(window_high)
            low_rel_index = np.argmin(window_low)

            window_highs_index.append(i + high_rel_index)
            window_lows_index.append(i + low_rel_index)

        # 筛选出现次数达到窗口大小的索引
        high_counter = Counter(window_highs_index)
        low_counter = Counter(window_lows_index)

        # 直接筛选，无需反转
        wave_highs = [idx for idx, count in high_counter.items() if count >= window_size]
        wave_lows = [idx for idx, count in low_counter.items() if count >= window_size]

        # 按索引排序（确保返回的索引是升序）
        wave_highs.sort()
        wave_lows.sort()

        return wave_highs, wave_lows

    @staticmethod
    def check_real_bearish(kline: pd.DataFrame, min_decline=0.02, entity_ratio=0.8) -> bool:
        """
        检测 K线是否为实体阴线
        :param kline:
        :param min_decline:  K线 跌幅   0.02 = 2%
        :param entity_ratio: K线 实体 占总K线的比例 0.8 = 80%
        :return:
        """
        # 计算跌幅+
        low = kline['low']
        high = kline['high']
        close = kline['close']
        open = kline['open']
        if close >= open:
            return False

        # 计算跌幅
        decline_ratio = (open - close) / open
        # 必须是阴线且跌幅超过阈值
        if decline_ratio < min_decline:
            return False

        # 计算是否为阴线实体较大
        total_range = high - low
        entity_size = open - close
        actual_entity_ratio = entity_size / total_range
        # 实体比例必须达到80%以上
        return actual_entity_ratio >= entity_ratio

    @staticmethod
    def check_highToLow(klines: pd.DataFrame) -> bool:
        """
        部冲高回落  仙人指路
        :param klines:
        :return:
        """
        RECORD_COUNT = KlinesAnalyzer.__RECORD_COUNT
        # K线小于100条记录 返回FALSE
        if len(klines) < RECORD_COUNT or klines.empty:
            return False
        df_klines = klines.tail(RECORD_COUNT)
        try:
            today_kline = df_klines.iloc[-1]
            pre_kline = df_klines.iloc[-2]

            today_high = today_kline['high']
            today_low = today_kline['low']
            today_close = today_kline['close']
            today_vol = today_kline['volume']
            pre_open = pre_kline['open']
            pre_close = pre_kline['close']
            pre_vol = pre_kline['volume']

            # 今天的高点比昨天要低
            # if today_high > pre_high:
            #     return False
            # 上一个交易日 要是阴线
            if pre_close > pre_open:
                return False
            # 判断上影线要长
            high_line = today_high - today_close
            low_line = today_close - today_low
            if high_line < low_line:
                return False
            macd_info = MACD(close=df_klines['close'], window_fast=12, window_slow=26, window_sign=9)
            last_DIF = macd_info.macd().iloc[-1]
            last_DEA = macd_info.macd_signal().iloc[-1]
            last_MACD = macd_info.macd_diff().iloc[-1]
            if last_MACD < 0 or last_DIF < 0 or last_DEA < 0:
                return False
            if today_vol > pre_vol:
                return False
        except Exception as e:
            # 处理其他异常
            print(f"发生未知错误: {e}")
            return False
        return True

    @staticmethod
    def check_pass_peak(klines: pd.DataFrame, period='d') -> list:
        """
        破低翻  过波段高点  头肩底
        "date","open","high","low","close","volume" DataFrame需要用的列名  date 可以不包括
        :param klines:  要分析的K线数据
        :param period:  周期  d 日线  w 周线
        :return:  不匹配返回空列表  匹配返回  list [low,high, rcnt]  low 前波段低点  high 前波段高点   rcnt 前波段高点 到 分析当天的红柱数量
        """
        # 早期返回条件
        if klines.empty or len(klines) < KlinesAnalyzer.__RECORD_COUNT:
            return []
        df_klines = klines.tail(KlinesAnalyzer.__RECORD_COUNT)
        try:
            # ============ 1. 基础条件检查 ============
            today, yesterday = df_klines.iloc[-1], df_klines.iloc[-2]
            # 昨日高点不能高于今日高点（今日需突破）
            if yesterday['high'] > today['high']:
                return []
            today_high = today['high']
            today_low = today['low']
            pre_low = yesterday['low']

            for n in [2, 3]:
                # 获取波段的 高低点
                highs_index, lows_index = KlinesAnalyzer.__getWavePoints(df_klines, n, 'high', 'low')

                # 波段数量小于3
                if len(lows_index) < 3 or len(highs_index) < 3:
                    continue

                # 先判断 今天的高点 是否大于第一个波段
                lastHighPrice = df_klines.iloc[highs_index[-1]]['high']
                if today_high < lastHighPrice:
                    continue

                # 先确定最低点
                lowPrice = df_klines.iloc[lows_index[-1]]['low']
                tmpLow = min(today_low, pre_low)
                if tmpLow < lowPrice:
                    lows_index.append(KlinesAnalyzer.__RECORD_COUNT - 1)

                # 确定前低  和 最低
                lowPoints = lows_index[::-1]  # 翻转list  ::-1  一般情况下更快
                curLowIndex = -1
                preLowIndex = -1
                highIndex = -1
                # 确定波段的最低点
                for current, next_item in zip(lowPoints, lowPoints[1:]):
                    curLow = df_klines.iloc[current]['low']
                    nextLow = df_klines.iloc[next_item]['low']
                    if curLow < nextLow:
                        curLowIndex = current
                        break
                if curLowIndex == -1:
                    continue

                # 确定波段的最高点
                for nIndex in reversed(highs_index):
                    if nIndex <= curLowIndex:
                        highIndex = nIndex
                        break
                if highIndex == -1:
                    continue

                # 再确定高点波段前面的低点
                for nIndex in reversed(lows_index):
                    if nIndex <= highIndex:
                        preLowIndex = nIndex
                        break

                curLowPrice = df_klines.iloc[curLowIndex]['low']
                preLowPrice = df_klines.iloc[preLowIndex]['low']
                # 判断破底翻
                if curLowPrice > preLowPrice:
                    continue

                highPrice = df_klines.iloc[highIndex]['high']
                # 判断过前波段高点
                if today_high < highPrice:
                    continue

                # 判断前面波段的高点到昨天是最高点
                sub_check_high = df_klines.iloc[highIndex: KlinesAnalyzer.__RECORD_COUNT - 1]
                sub_high_price = sub_check_high['high'].max()
                if sub_high_price != highPrice:
                    continue

                # 统计MACD 红柱的数量
                close_prices = pd.Series(list(df_klines['close']))
                macd_info = MACD(close=close_prices, window_fast=12, window_slow=26, window_sign=9)
                # 计算从highIndex到昨天的MACD大于0的个数
                macd_values = macd_info.macd_diff()
                macd_slice = macd_values.iloc[highIndex:]  # 从highIndex到昨天（不包括今天）

                # 统计MACD大于0的天数
                macd_positive_count = (macd_slice > 0).sum()

                # 周线直接返回
                if period == 'w':
                    return [curLowPrice, highPrice, macd_positive_count]
                if macd_positive_count < 0:
                    continue
                # 获取创新低的天数
                sub_check_low = df_klines.iloc[curLowIndex - KlinesAnalyzer.__NEW_LOW_DAYS: curLowIndex]
                n_day_low_price = sub_check_low['low'].min()
                lowPrice = df_klines.iloc[curLowIndex]['low']
                if lowPrice <= n_day_low_price:
                    return [lowPrice, highPrice, macd_positive_count]
        except Exception as e:
            # 处理其他异常
            print(f"check_pass_peak err: {e}")
            return []
        return []
