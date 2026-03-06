from ta.trend import MACD
import pandas as pd
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numba import jit


class KlinesAnalyzer:
    """
    主要分析是K线形态 是不是符合 过前高     check_pass_peak
    分析K线 形态 是否为阴线               check_real_bearish
    分析K线 形态 是否为仙人指路            check_highToLow
    """
    # 记录数
    __RECORD_COUNT = 100
    # 创新低天数
    __NEW_LOW_DAYS = 18

    @staticmethod
    def __getWavePoints(records, window_size, high_flag, low_flag):
        """
           完全向量化的卷积思想实现
           使用滑动窗口视图和广播机制
        """

        highs = records[high_flag].values
        lows = records[low_flag].values
        n_records = len(highs)

        # 创建滑动窗口视图（不复制数据，只是视图）
        high_windows = sliding_window_view(highs, window_size)
        low_windows = sliding_window_view(lows, window_size)

        # 找到每个窗口的极值位置（相对索引）
        high_max_indices = np.argmax(high_windows, axis=1)
        low_min_indices = np.argmin(low_windows, axis=1)

        # 创建窗口起始位置
        starts = np.arange(n_records - window_size + 1)

        # 转换为绝对索引
        high_abs_indices = starts + high_max_indices
        low_abs_indices = starts + low_min_indices

        # 使用bincount统计每个位置出现的次数
        high_counts = np.bincount(high_abs_indices, minlength=n_records)
        low_counts = np.bincount(low_abs_indices, minlength=n_records)

        # 筛选
        wave_highs = np.where(high_counts >= window_size)[0].tolist()
        wave_lows = np.where(low_counts >= window_size)[0].tolist()

        return wave_highs, wave_lows

    @staticmethod
    def check_real_bearish(kline: pd.DataFrame, body_threshold=0.70, shadow_tolerance=0.2,
                           min_drop_percent=1.2) -> bool:
        """
        :param kline:   K线
        :param body_threshold:   实体部分 百分比 0.70  = 70%
        :param shadow_tolerance: 下阴线容忍度 占总K线的百分比 0.15 = 15%
        :param min_drop_percent:  阴线 开盘到收盘的最小跌幅 1.5 = 1.5%
        :return:  bool
        """
        # 基础检查
        open_price = kline['open']
        close_price = kline['close']
        high_price = kline['high']
        low_price = kline['low']

        # 必须是阴线
        if close_price >= open_price:
            return False
        #  计算总范围 无波动
        total_range = high_price - low_price
        if total_range == 0:
            return False
        # 计算跌幅
        drop_percent = ((open_price - close_price) / open_price) * 100
        if drop_percent < min_drop_percent:
            return False
        if close_price == low_price:
            return True

        # 计算实体比例
        body_size = open_price - close_price  # 阴线实体大小
        body_ratio = body_size / total_range

        # 计算下影线比例
        lower_shadow = close_price - low_price  # 阴线的下影线
        lower_shadow_ratio = lower_shadow / total_range

        # 判断条件
        meets_body_condition = body_ratio >= body_threshold
        meets_shadow_condition = lower_shadow_ratio <= shadow_tolerance
        # 实体百分比要匹配  下阴线容忍度要匹配
        return meets_body_condition and meets_shadow_condition

    @staticmethod
    def check_highToLow(kline: pd.DataFrame, upper_shadow_pct_threshold: float = 0.6,
                        min_amplitude_pct: float = 0.01) -> bool:
        open_price = kline['open']
        close_price = kline['close']
        high_price = kline['high']
        low_price = kline['low']

        # 计算总振幅
        total_range = high_price - low_price
        if total_range == 0:
            return False

        # 计算上影线长度（从最高点到收盘价或开盘价的较高者） 获取上阴线的长度
        upper_shadow = high_price - max(open_price, close_price)

        # 计算上影线占总振幅的比例
        upper_shadow_pct = upper_shadow / total_range

        # 计算上影线相对于开盘价的百分比
        upper_shadow_price_pct = upper_shadow / open_price

        # 计算实体长度
        # body = abs(close_price - open_price)
        # body_pct = body / total_range if total_range > 0 else 0

        # 判断条件
        condition1 = upper_shadow_pct >= upper_shadow_pct_threshold
        condition2 = upper_shadow_price_pct >= min_amplitude_pct

        is_high_low = all([condition1, condition2])

        return is_high_low

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
                # 链式赋值
                curLowIndex = preLowIndex = highIndex = -1
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
                # 前波段高点
                highPrice = df_klines.iloc[highIndex]['high']
                # 判断过前波段高点
                if today_high < highPrice:
                    continue

                # 判断前面波段的高点到昨天是最高点
                sub_check_high = df_klines.iloc[highIndex + 1: KlinesAnalyzer.__RECORD_COUNT - 1]
                sub_high_price = sub_check_high['high'].max()
                if highPrice <= sub_high_price:
                    continue

                # 获取最后一天的 close 值
                last_close = df_klines['close'].iloc[-1]
                close_prices = pd.Series(list(df_klines['close'])) + [last_close]

                macd_info = MACD(close=close_prices, window_fast=12, window_slow=26, window_sign=9)
                # 计算从highIndex到昨天的MACD大于0的个数
                MACD_values = macd_info.macd_diff()  # MACD柱 = DIF - DEA
                # DIF_line = macd_info.macd()  # DIF (快线/白线) = 12日EMA - 26日EMA
                DEA_line = macd_info.macd_signal()  # DEA (慢线/黄线) = DIF的9日EMA

                latest_MACD = MACD_values.iloc[-1]  # 最新一天的MACD值
                if period == 'd':
                    if latest_MACD < 0:
                        return []
                else:
                    latest_DEA = DEA_line.iloc[-1]  # 最新DEA值
                    if latest_DEA < 0 and latest_MACD < 0:
                        return []

                macd_slice = MACD_values.iloc[curLowIndex:-1]  # 包括最后一天 最后一天是加的
                rMacdCnt = (macd_slice >= 0).sum()
                if rMacdCnt == KlinesAnalyzer.__RECORD_COUNT - curLowIndex:
                    if rMacdCnt > 3:
                        rMacdCnt = 999  # 全红
                # 构造返回list
                ret_list = [float(curLowPrice), float(highPrice), int(rMacdCnt)]
                # 说明低点到高点全是红柱
                if rMacdCnt == 999:
                    return ret_list
                # 周线
                if period == 'w':
                    return ret_list
                # 获取创新低的天数
                sub_check_low = df_klines.iloc[curLowIndex - KlinesAnalyzer.__NEW_LOW_DAYS: curLowIndex]
                n_day_low_price = sub_check_low['low'].min()
                if curLowPrice <= n_day_low_price:
                    return ret_list
        except Exception as e:
            # 处理其他异常
            print(f"check_pass_peak err: {e}")
            return []
