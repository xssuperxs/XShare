from ta.trend import MACD
import pandas as pd
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import baostock as bs
import datetime

# 登陆baostock
lg = bs.login()


def _bs_get_trade_date(period: str = 'd') -> tuple[str, str]:
    start_date = (datetime.date.today() - datetime.timedelta(weeks=120)).strftime('%Y-%m-%d')
    rs = bs.query_history_k_data_plus(
        code='sh.000001',
        fields="date",  # 字段可调整
        start_date=start_date,  # 尽可能早的日期
        end_date='2050-12-30',  # 未来日期确保覆盖最新数据
        frequency=period,  # d=日线，w=周线，m=月线
        adjustflag="2"  # 复权类型：3=后复权  复权类型，默认不复权：3；1：后复权；2：前复权
    )
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    df = pd.DataFrame(data_list, columns=rs.fields)
    start_date = df['date'].iloc[-110]
    end_date = df['date'].iloc[-1]
    return start_date, end_date


def bs_get_stock_codes() -> list[str]:
    """
    :return: 返回提取的股票代码  带有sh.600519  sz.000353 这样格式的list
    """
    stock_list = bs.query_stock_basic()
    stock_df = stock_list.get_data()
    filtered_stocks = stock_df[
        (stock_df['type'].isin(['1'])) &  # 1 是股票  5 是ETF  2是指数
        (stock_df['status'] == '1') &  # 在交易
        (~stock_df['code_name'].str.contains('ST|\\*ST|退|警示|终止上市', na=False))  # 排除ST股和问题股
        ]
    # 获取股票代码列表
    code_list = filtered_stocks['code'].tolist()
    # 过滤掉暂时不需要的代码
    patterns = [".7", ".9", ".688", ".4"]
    ret_cods = [item for item in code_list if not any(pattern in item for pattern in patterns)]
    return ret_cods


def _bs_get_stock_hist(code: str, period: str = 'd',
                       start_date: str = None,
                       end_date: str = None) -> pd.DataFrame:
    """
    类方法：获取股票历史数据
    """
    # 1. 获取数据
    try:
        fields = "date,open,close,high,low,volume,amount"

        rs = bs.query_history_k_data_plus(
            code=code,
            fields=fields,  # 字段可调整
            start_date=start_date,  # 尽可能早的日期
            end_date=end_date,  # 未来日期确保覆盖最新数据
            frequency=period,  # d=日线，w=周线，m=月线
            adjustflag="2"  # 复权类型：3=后复权  复权类型，默认不复权：3；1：后复权；2：前复权
        )
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        df = pd.DataFrame(data_list, columns=rs.fields)
        if df.empty:
            return df

        float_cols = ['open', 'close', 'high', 'low', 'volume', 'amount']
        # 转换并保留两位小数
        df[float_cols] = df[float_cols].apply(pd.to_numeric, errors='coerce').round(2)
        return df

    except Exception as e:
        print(f"get_stock_hist 获取数据异常：{e}")
        return pd.DataFrame()


_start_date_d, _end_date_d = _bs_get_trade_date('d')
_start_date_w, _end_date_w = _bs_get_trade_date('w')

# 记录数
_RECORD_COUNT = 100

# 创新低天数
_NEW_LOW_DAYS = 18


def _getWavePoints(records, window_size, high_flag, low_flag):
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


def _check2_week_macd(klines: pd.DataFrame):
    """
    检测 周线的 DIF 线 要在 水上  非常重要！！！！！ 加速段都是从水上开始的
    :param klines:  K线数据
    :return:
    """

    klines = klines.tail(100)
    # 计算周线快线
    last_close = klines['close'].iloc[-1]

    # 使用 concat 追加
    # 原始 Series
    close_prices = pd.Series(list(klines['close']))
    macd_info = MACD(close=close_prices, window_fast=12, window_slow=26, window_sign=9)
    DIF_line = macd_info.macd()
    latest_DIF = DIF_line.iloc[-1]
    if latest_DIF > 0:
        return True
    # 计算MACD 红柱
    new_values = [last_close, last_close]
    close_prices = pd.concat([close_prices, pd.Series(new_values)], ignore_index=True)
    macd_info = MACD(close=close_prices, window_fast=12, window_slow=26, window_sign=9)
    MACD_values = macd_info.macd_diff()
    latest_MACD = MACD_values.iloc[-1]
    return latest_MACD > 0


def _check_MACD(klines: pd.DataFrame, lowIndex, period='d'):
    """
    :param klines:  K线数据
    :param lowIndex: 前波段低点的索引
    :param period:  周期
    :return: bool
    """

    # 获取最后一天的 close 值 容忍度
    last_close = klines['close'].iloc[-1]

    macd_ext = last_close if period == 'd' else [last_close, last_close]
    # 构造所需要的收盘价
    close_prices = pd.concat([pd.Series(list(klines['close'])), pd.Series(macd_ext)], ignore_index=True)
    # 计算MACD
    macd_info = MACD(close=close_prices, window_fast=12, window_slow=26, window_sign=9)
    # MACD 柱
    MACD_values = macd_info.macd_diff()
    # DIF  快线 白线
    # DIF_line = macd_info.macd()
    # DEA  黄线 慢线
    # DEA_line = macd_info.macd_signal()
    # 获取最后一天的值
    # latest_DEA = DEA_line.iloc[-1]
    # latest_DIF = DIF_line.iloc[-1]
    latest_MACD = MACD_values.iloc[-1]

    # 提取MACD 低点到今天的红柱数量
    macd_slice = MACD_values.iloc[lowIndex - 1:-1]  # 包括最后一天 最后一天是加的
    rMacdCnt = (macd_slice >= 0).sum()
    # 如果是全红 就直接返回
    if rMacdCnt == len(klines) - lowIndex:
        if rMacdCnt >= 3:
            rMacdCnt = 999  # 全红
            return True, rMacdCnt

    if latest_MACD < 0:
        return False, rMacdCnt
    return True, rMacdCnt


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


def check_pass_peak(klines: pd.DataFrame, period='d') -> list:
    """
    分析K线形态  过波段高点  头肩底
    "date","open","high","low","close","volume" DataFrame需要用的列名  date 可以不包括
    :param klines:  要分析的K线数据
    :param period:  周期  d 日线  w 周线
    :return:  不匹配返回空列表  匹配返回  list [low,high, rcnt]  low 前波段低点  high 前波段高点   rcnt 前波段高点 到 分析当天的红柱数量
    """
    # 早期返回条件
    if klines.empty or len(klines) < _RECORD_COUNT:
        return []
    df_klines = klines.tail(_RECORD_COUNT)
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
            highs_index, lows_index = _getWavePoints(df_klines, n, 'high', 'low')

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
                lows_index.append(_RECORD_COUNT - 1)

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
            sub_check_high = df_klines.iloc[highIndex + 1: _RECORD_COUNT - 1]
            sub_high_price = sub_check_high['high'].max()
            if highPrice <= sub_high_price:
                continue

            macd_ok, rcnt = _check_MACD(df_klines, curLowIndex, period)
            if not macd_ok:
                return []
            ret_list = [float(curLowPrice), float(highPrice), int(rcnt)]
            if period == 'w':
                return ret_list
            # 获取创新低的天数
            sub_check_low = df_klines.iloc[curLowIndex - _NEW_LOW_DAYS: curLowIndex]
            n_day_low_price = sub_check_low['low'].min()
            if curLowPrice <= n_day_low_price:
                return ret_list
    except Exception as e:
        # 处理其他异常
        print(f"check_pass_peak err: {e}")
        return []


def _append_result(ret_list, code, end_date, period):
    ret_list.insert(0, code)
    ret_list.insert(3, end_date)
    ret_list.insert(4, period)
    return ret_list


def analyze_an_stock(code, period='d') -> list:
    if period == 'w':
        df = _bs_get_stock_hist(code, period, _start_date_w, _end_date_w)
    else:
        df = _bs_get_stock_hist(code, period, _start_date_d, _end_date_d)

    end_data_list = _end_date_d if period == 'd' else _end_date_w

    ret_list = check_pass_peak(df, period)
    if not ret_list:  # 列表为空
        return []
    _append_result(ret_list, code, end_data_list, period)

    if period == 'w':
        return ret_list
    # 检查周线的快线在水上
    df_weekly = _bs_get_stock_hist(code, 'w', _start_date_w, _end_date_w)
    is_valid = _check2_week_macd(df_weekly)

    if not is_valid and ret_list[-1] < 999:
        return []
    ret_list[-1] = 998
    return ret_list
