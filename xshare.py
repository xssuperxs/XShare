from collections import Counter
from ta.trend import MACD
import pandas as pd


class KlinesAnalyzer:
    """
     K线分析类
    主要分析是K线形态 是不是符合 破底翻
    分析K线 形态 是否为阴线
    分析K线 形态 是否为仙人指路
    """
    # 记录数
    __RECORD_COUNT = 90
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

        wave_highs_index = KlinesAnalyzer.__extractFrequentElements(window_highs_index, window_size)
        wave_lows_index = KlinesAnalyzer.__extractFrequentElements(window_lows_index, window_size)

        # 再把计算结果反转过来
        for i in range(len(wave_highs_index)):
            wave_highs_index[i] = KlinesAnalyzer.__RECORD_COUNT - wave_highs_index[i] - 1

        for i in range(len(wave_lows_index)):
            wave_lows_index[i] = KlinesAnalyzer.__RECORD_COUNT - wave_lows_index[i] - 1

        wave_highs_index = wave_highs_index[::-1]
        wave_lows_index = wave_lows_index[::-1]
        return wave_highs_index, wave_lows_index

    @staticmethod
    def strategy_newHigh(klines: pd.DataFrame, period='d') -> bool:
        """
        缩量突破
        :param klines:
        :param period:
        :return:
        """
        pass

    @staticmethod
    def check_high_to_low(kline: pd.DataFrame, min_shadow_ratio=0.4) -> bool:
        """
        判断K线是否是冲高回落
        :param kline:
        :param min_shadow_ratio: 上阴线的占比 最少
        :return:
        """
        low = kline['low']
        high = kline['high']
        close = kline['close']
        open = kline['open']

        # 计算实体和影线
        entity_high = max(open, close)
        # entity_low = min(open, close)

        upper_shadow = high - entity_high  # 获取上限线的长度
        # lower_shadow = entity_low - low  # 获取下阴线的长度
        total_range = high - low  # K线最高 到 最低的范围

        # 避免除零错误
        if total_range == 0:
            return False

        # 计算各种比例
        upper_shadow_ratio = upper_shadow / total_range  # 上阴线的比例
        close_position = (close - low) / total_range  # 收盘价在K线中的位置

        # 冲高回落判断条件
        conditions = [
            upper_shadow_ratio >= min_shadow_ratio,  # 上影线足够长
            close_position <= 0.5,  # 收盘价在下半部分
            # high > open * 1.01,  # 最高点明显高于开盘价(至少1%)
            # close < high * 0.98  # 收盘价明显低于最高点(至少回落2%)
        ]
        return all(conditions)

    @staticmethod
    def kline_solid_bearish_candle(kline: pd.DataFrame, min_decline=0.02, entity_ratio=0.8) -> bool:
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
    def strategy_highToLow(klines: pd.DataFrame) -> bool:
        """
        低部冲高回落
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
    def check_pass_peak(klines: pd.DataFrame, period='d') -> bool:
        """
        破低翻  过波段高点  头肩底
        "date","open","high","low","close","volume" DataFrame需要用的列名  date 可以不包括
        :param klines:  最近 N天的交易记录 要保证传进来的K线数据大于100条  不大也没事
        :param period:  周期  d 日线  w 周线
        :return:  bool
        """
        # 早期返回条件
        if klines.empty or len(klines) < KlinesAnalyzer.__RECORD_COUNT:
            return False
        df_klines = klines.tail(KlinesAnalyzer.__RECORD_COUNT)
        try:
            # ============ 1. 基础条件检查 ============
            today, yesterday = df_klines.iloc[-1], df_klines.iloc[-2]
            # 昨日高点不能高于今日高点（今日需突破）
            if yesterday['high'] > today['high']:
                return False
            today_high = today['high']
            today_low = today['low']
            today_close = today['close']
            pre_low = yesterday['low']

            for n in [2, 3]:
                # 获取波段的 高低点
                highs_index, lows_index = KlinesAnalyzer.__getWavePoints(df_klines, n, 'high', 'low')

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
                # lowPoints = list(reversed(lows_index))
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
                # 周线直接返回TRUE
                if period == 'w':
                    return True
                # MACD
                close_prices = pd.Series(list(df_klines['close']))
                # new_series = pd.Series(list(df_klines['close']) + [today_close] + [today_close])
                macd_info = MACD(close=close_prices, window_fast=12, window_slow=26, window_sign=9)
                # last_DIF = macd_info.macd().iloc[-1]  # 快线
                # last_DEA = macd_info.macd_signal().iloc[-1]  # 慢线
                last_MACD = macd_info.macd_diff().iloc[-1]  # MACD 值 红绿柱
                if last_MACD < 0:
                    continue
                # 获取创新低的天数
                sub_check_low = df_klines.iloc[curLowIndex - KlinesAnalyzer.__NEW_LOW_DAYS: curLowIndex]
                n_day_low_price = sub_check_low['low'].min()
                lowPrice = df_klines.iloc[curLowIndex]['low']
                if lowPrice <= n_day_low_price:
                    return True
        except Exception as e:
            # 处理其他异常
            print(f"发生未知错误: {e}")
            return False
        return False
