import pandas as pd
from ta.trend import MACD
import baostock as bs
import datetime

from scipy.signal import find_peaks

# 登陆baostock
lg = bs.login()


def _bs_get_trade_date(period: str = 'd') -> tuple[str, str]:
    start_date = (datetime.date.today() - datetime.timedelta(weeks=120)).strftime('%Y-%m-%d')
    rs = bs.query_history_k_data_plus(
        code='sh.000001',
        fields="date",  # 字段可调整
        start_date=start_date,  # 尽可能早的日期
        end_date='',  # 未来日期确保覆盖最新数据
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


def bs_get_stock_hist(code: str, period: str = 'd',
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



def _check2_pass_peak(code, klines, period='d') -> int:
    all_red = False

    # 获取MACD信息，容忍度日线1天，周线2天
    # 扩展close序列用于MACD计算
    append_close = [klines['close'].iloc[-1]] * 2
    close_price = pd.concat([klines['close'], pd.Series(append_close)], ignore_index=True)

    # 获取MACD信息
    macd_info = MACD(close=pd.Series(close_price), window_fast=12, window_slow=26, window_sign=9)
    macd_histogram = macd_info.macd_diff()  # MACD柱状线
    latest_dif = macd_info.macd().iloc[-1]  # DIF线
    latest_dea = macd_info.macd_signal().iloc[-1]  # DEA线
    latest_macd = macd_histogram.iloc[-1]

    # 检查是否为水下
    if latest_macd < 0 and latest_dif < 0 and latest_dea < 0:
        return 0

    # 检查最近三条MACD柱线是否都是红柱(>=0)
    if all(x >= 0 for x in macd_histogram.iloc[-5:-2]):
        all_red = True

    # 周线处理
    if period == 'w':
        # 检查第三根柱线是否为红
        if macd_histogram.iloc[-3] > 0 or latest_dif > 0 or latest_dea > 0:
            return 999
        return 998

    # 日线处理
    if period == 'd':
        # 获取周线数据并计算MACD
        df_weekly = bs_get_stock_hist(code, 'w', _start_date_w, _end_date_w)
        w_macd_info = MACD(close=df_weekly['close'], window_fast=12, window_slow=26, window_sign=9)
        w_macd = w_macd_info.macd_diff().iloc[-1]
        w_dif = w_macd_info.macd().iloc[-1]
        w_dea = w_macd_info.macd_signal().iloc[-1]

        # 判断日线全红的情况
        if all_red:
            # 周线MACD在水下
            if w_dif < 0 and w_dea < 0:
                return 998
            return 999

        # 检查周线是否全部在水下
        if w_dif < 0 and w_macd < 0 and w_dea < 0:
            return 0

        # 容忍度2天还不是红的，直接返回0
        if latest_macd < 0:
            return 0
    return 997


def check_real_bearish(kline: pd.DataFrame, body_threshold=0.70, shadow_tolerance=0.2,
                       min_drop_percent=1.0) -> bool:
    """
    :param kline:   K线
    :param body_threshold:   实体部分 百分比 0.70  = 70%
    :param shadow_tolerance: 下阴线容忍度 占总K线的百分比 0.15 = 15%
    :param min_drop_percent:  阴线 开盘到收盘的最小跌幅 1.5 = 1.5%
    :return:  bool
    """
    # 基础检查
    open_price = kline['open'].iloc[0]
    close_price = kline['close'].iloc[0]
    high_price = kline['high'].iloc[0]
    low_price = kline['low'].iloc[0]
    # 必须是阴线
    if close_price >= open_price:
        return False
    #  计算总范围 无波动
    total_range = high_price - low_price
    if total_range == 0:
        return False
    # 计算跌幅
    drop_percent = ((open_price - close_price) / open_price) * 100
    if drop_percent > 4:
        return True
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
    open_price = kline['open'].iloc[0]
    close_price = kline['close'].iloc[0]
    high_price = kline['high'].iloc[0]
    low_price = kline['low'].iloc[0]

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


def check_pass_peak(klines: pd.DataFrame) -> tuple:
    """
    分析K线形态  过波段高点  头肩底   只是分析 形态是否相似  形似还要神似 需要二次过滤
    "date","open","high","low","close","volume" DataFrame需要用的列名  date 可以不包括
    :param klines:  要分析的K线数据
    :return:  返因TRUE
    """
    # 早期返回条件
    if klines.empty or len(klines) < 30:
        return ()
    try:
        # ============ 1. 基础条件检查 ============
        today, yesterday = klines.iloc[-1], klines.iloc[-2]
        # 昨日高点不能高于今日高点（今日需突破）
        if yesterday['high'] > today['high']:
            return ()
        today_high = today['high']
        today_low = today['low']
        pre_low = yesterday['low']
        highs = klines['high']
        lows = klines['low']
        for n in [1, 2]:
            # 获取波段的 高低点
            highs_index, _ = find_peaks(highs.values, distance=n)
            lows_index, _ = find_peaks(-lows.values, distance=n)
            highs_index = highs_index.tolist()
            lows_index = lows_index.tolist()
            # 波段数量小于3
            if len(lows_index) < 3 or len(highs_index) < 3:
                continue
            # 先判断 今天的高点 是否大于第一个波段
            lastHighPrice = klines['high'].iloc[highs_index[-1]]
            if today_high < lastHighPrice:
                continue

            # 先确定最低点
            lowPrice = klines.iloc[lows_index[-1]]['low']
            tmpLow = min(today_low, pre_low)
            if tmpLow < lowPrice:
                difference = 1 if tmpLow == today_low else 2
                lows_index.append(len(klines) - difference)

            # 确定前低  和 最低
            lowPoints = lows_index[::-1]  # 翻转list  ::-1  一般情况下更快
            # 链式赋值
            curLowIndex = preLowIndex = highIndex = -1
            # 确定波段的最低点
            for current, next_item in zip(lowPoints, lowPoints[1:]):
                curLow = klines.iloc[current]['low']
                nextLow = klines.iloc[next_item]['low']
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

            curLowPrice = klines.iloc[curLowIndex]['low']
            preLowPrice = klines.iloc[preLowIndex]['low']
            # 判断破底翻
            if curLowPrice > preLowPrice:
                continue
            # 前波段高点
            highPrice = klines.iloc[highIndex]['high']
            # 判断过前波段高点
            if today_high < highPrice:
                continue

            # 判断前面波段的高点到昨天是最高点
            sub_check_high = klines.iloc[highIndex + 1: kline_len - 1]
            sub_high_price = sub_check_high['high'].max()
            if highPrice <= sub_high_price:
                continue
            return float(curLowPrice), float(highPrice)
    except Exception as e:
        # 处理其他异常
        print(f"check_pass_peak err: {e}")
        return ()
    return ()


def analyze_an_stock(code, period='d') -> list:
    if period == 'w':
        df = bs_get_stock_hist(code, period, _start_date_w, _end_date_w)
    else:
        df = bs_get_stock_hist(code, period, _start_date_d, _end_date_d)

    analyze_date = _end_date_d if period == 'd' else _end_date_w
    # 判断 形似
    prices = check_pass_peak(df)
    if not prices:
        return []
    # 形似 判断神似  返回神似的分数
    rcnt = _check2_pass_peak(code, df, period)
    if rcnt == 0:
        return []
    low = prices[0]
    high = prices[1]
    ret_list = [code, low, high, analyze_date, period, rcnt]
    return ret_list
