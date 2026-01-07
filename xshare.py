import time

import akshare as ak
import baostock as bs
from collections import Counter

import requests
from ta.trend import MACD
import pandas as pd
import subprocess
import sys
from tqdm import tqdm
from datetime import datetime
from dateutil.relativedelta import relativedelta


class XShare:
    # 记录数
    __RECORD_COUNT = 100
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
    def strategy_newHigh(klines: pd.DataFrame, period='d') -> bool:
        """
        缩量突破
        :param klines:
        :param period:
        :return:
        """
        pass

    @staticmethod
    def kline_rally_fade(kline: pd.DataFrame, min_shadow_ratio=0.4) -> bool:
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
        # K线小于100条记录 返回FALSE
        if len(klines) < XShare.__RECORD_COUNT or klines.empty:
            return False
        df_klines = klines.tail(XShare.__RECORD_COUNT)
        try:
            today_kline = df_klines.iloc[-1]
            pre_kline = df_klines.iloc[-2]

            today_high = today_kline['high']
            today_low = today_kline['low']
            # today_open = today_kline['open']
            today_close = today_kline['close']
            today_vol = today_kline['volume']

            # pre_high = pre_kline['high']
            # pre_low = pre_kline['low']
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
    def strategy_bottomUpFlip(klines: pd.DataFrame, period='d') -> bool:
        """
        破低翻
        "date","open","high","low","close","volume" DataFrame需要用的列名  date 可以不包括
        :param klines:  最近 N天的交易记录 要保证传进来的K线数据大于100条  不大也没事
        :param period:  周期  d 日线  w 周线
        :return:  bool
        """
        # K线小于100条记录 返回FALSE
        if len(klines) < XShare.__RECORD_COUNT or klines.empty:
            return False
        df_klines = klines.tail(XShare.__RECORD_COUNT)
        try:
            today_kline = df_klines.iloc[-1]
            pre_kline = df_klines.iloc[-2]

            today_high = today_kline['high']
            today_low = today_kline['low']
            today_close = today_kline['close']
            pre_high = pre_kline['high']
            pre_low = pre_kline['low']

            if pre_high > today_high:
                return False
            # 滑动窗口大小
            window_size = [2, 3]

            for n in window_size:
                # 获取波段的 高低点
                highs_index, lows_index = XShare.__getWavePoints(df_klines, n, 'high', 'low')

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
                    lows_index.append(XShare.__RECORD_COUNT - 1)
                # 确定前低  和 最低
                lowPoints = list(reversed(lows_index))
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
                sub_check_high = df_klines.iloc[highIndex: XShare.__RECORD_COUNT - 1]
                sub_high_price = sub_check_high['high'].max()
                if sub_high_price != highPrice:
                    continue
                if period == 'w':
                    return True

                # MACD
                # new_series = pd.Series(list(df_klines['close']))
                new_series = pd.Series(list(df_klines['close']) + [today_close] + [today_close])
                macd_info = MACD(close=new_series, window_fast=12, window_slow=26, window_sign=9)
                # last_DIF = macd_info.macd().iloc[-1]  # 快线
                # last_DEA = macd_info.macd_signal().iloc[-1]  # 慢线
                last_MACD = macd_info.macd_diff().iloc[-1]  # MACD 值 红绿柱
                if last_MACD < 0:
                    continue
                # 判断是否出现过涨停板
                # close_prices = tuple(klines['close'].tolist())
                # is_limit_up = False
                # for i in range(1, len(close_prices)):
                #     prev_price = close_prices[i - 1]
                #     current_price = close_prices[i]
                #
                #     # 计算涨停价（10%限制）
                #     limit_up_price = round(prev_price * 1.10, 2)
                #
                #     # 判断是否为涨停
                #     if current_price >= limit_up_price:
                #         is_limit_up = True
                #         break
                # if not is_limit_up:
                #     continue
                # 获取创新低的天数
                sub_check_low = df_klines.iloc[curLowIndex - XShare.__NEW_LOW_DAYS: curLowIndex]
                n_day_low_price = sub_check_low['low'].min()
                lowPrice = df_klines.iloc[curLowIndex]['low']
                if lowPrice <= n_day_low_price:
                    return True
        except Exception as e:
            # 处理其他异常
            print(f"发生未知错误: {e}")
            return False
        return False


# ================================================ 以上是 XShare的类 ===================================================


def back_test(code, end_date, period='d'):
    """
    测试用
    :param period: 周期  d 日线  w 周线
    :param code: 代码
    :param end_date: 结束时间
    :return: 失败False  成功 类型码
    """
    start_date, _ = _get_last_trade_date("%Y%m%d", end_date)

    df = _get_klines_akshare(code, period, start_date=start_date, end_date=end_date)

    return XShare.strategy_bottomUpFlip(df, period)


def _get_klines_baostock(code, period='d'):
    start_date, end_date = _get_last_trade_date("%Y-%m-%d")

    if period == 'w':
        start_date = "2020-01-01"
    # 获取所有历史K线数据（从上市日期至今）
    rs = bs.query_history_k_data_plus(
        code=code,
        fields="date,open,close,high,low,volume",  # 字段可调整
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

    float_cols = ['open', 'close', 'high', 'low', 'volume']
    # 转换并保留两位小数
    df[float_cols] = df[float_cols].apply(pd.to_numeric, errors='coerce').round(2)
    return df


def _get_klines_akshare(code, period='d', start_date: str = "19700101", end_date: str = "20500101"):
    if period == 'w':
        start_date = "19700101"

    _COL_MAPPING_AK = {
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
    }
    v_period = 'daily' if period == 'd' else 'weekly'
    df = ak.stock_zh_a_hist(symbol=code, period=v_period, adjust="qfq", start_date=start_date, end_date=end_date)
    if df.empty:
        return pd.DataFrame()
    # 数据清洗
    return df[list(_COL_MAPPING_AK.keys())].rename(columns=_COL_MAPPING_AK)


def _get_last_trade_date(date_format='%Y%m%d', end_date=''):
    if end_date != '':
        last_trade_date = datetime.strptime(end_date, "%Y%m%d").date()
    else:
        df = ak.stock_zh_index_daily('sh000001')
        last_trade_date = df['date'].iloc[-1]

    # 取一年的K线足够用了
    previous_year_date = last_trade_date - relativedelta(years=1)
    start_date = previous_year_date.strftime(date_format)
    end_date = last_trade_date.strftime(date_format)  # 输出 '20301230'
    return start_date, end_date


def _query_A_stock_codes_baostock():
    # 获取最后一个交易日
    _, end_date = _get_last_trade_date("%Y-%m-%d")

    # 查询A股的 股票 和指数 代码
    rs = bs.query_all_stock(day=end_date)

    data_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        data_list.append(rs.get_row_data())
    df_all_codes = pd.DataFrame(data_list, columns=rs.fields)
    if df_all_codes.empty:
        return []

    # 过滤掉ST 和 没交易的
    df_filtered = df_all_codes[
        (~df_all_codes['code_name'].str.contains(r'ST|\*ST', case=False, na=False)) &
        (df_all_codes['tradeStatus'] == '1')
        ]
    return df_filtered['code'].to_list()


def analyze_A(period='d'):
    """
    分析 A股的 个股  和 指数
    :param period:  d = 日K   w = 周K   m = 月K
    :return:  返回A股股票 分析的结果
    """
    codes = _query_A_stock_codes_baostock()
    if not codes:
        print("baostock 可能没有更新完成 稍后再试！")
        return []

    # 过滤掉暂时不需要的代码
    patterns = [".7", ".9", ".688", ".4"]
    filtered_codes = [item for item in codes if not any(pattern in item for pattern in patterns)]

    # 使用 tqdm 包装循环，并设置中文描述
    print("[INFO] Analyzing  A stocks and Index...")
    nError = 0
    ret_results = []
    for code in tqdm(filtered_codes, desc="Progress"):
        try:
            # 提取历史K线信息
            df = _get_klines_baostock(code, period)
            # 开始分析K线数据  破底翻
            if XShare.strategy_bottomUpFlip(df, period):
                code = code.split(".")[-1]
                ret_results.append(code)
            # 前一根阴 首阳
            # if XShare.strategy_highToLow(df):
            #     code = code.split(".")[-1]
            #     ret_results.append(code)
        except Exception as e:
            nError += 1
            if nError == 1:
                print(f"A Error: {e}")
            continue
    if nError > 1:
        print("analyze_A error count:" + str(nError))

    return ret_results


def get_etf_klines(symbol: str, period: str):
    """
    :type symbol: 股票代码
    :param period: 周期 日 daily 周 weekly
    """
    if period == 'd':
        etf_hist_kline = ak.fund_etf_hist_sina(symbol=symbol)
    else:
        period = 'weekly'
        etf_hist_kline = ak.fund_etf_hist_em(symbol=symbol, period=period)
        column_mapping = {
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            # '成交额': 'amount',
            # '振幅': 'amplitude',
            # '涨跌幅': 'change_pct',
            # '涨跌额': 'change_amt',
            # '换手率': 'turnover'
        }
        etf_hist_kline = etf_hist_kline.rename(columns=column_mapping)

    if etf_hist_kline.empty or etf_hist_kline['high'].iloc[-1] > 50:
        return pd.DataFrame()
    return etf_hist_kline


def analyze_A_ETF(period: str = 'd'):
    ret_results = []
    etf_spot = pd.DataFrame()
    if period == 'd':
        etf_spot = ak.fund_etf_category_sina(symbol="ETF基金")
    if period == 'w':
        etf_spot = ak.fund_etf_spot_em()

    # 获取 ETF 代码
    codes = etf_spot['代码'].to_list()
    print("[INFO] Analyzing  A ETF...")
    nError = 0
    for code in tqdm(codes, desc="Progress"):
        try:
            hist_df = get_etf_klines(code, period)
            if hist_df.empty:
                continue
            if XShare.strategy_bottomUpFlip(hist_df, period=period):
                # 判断下ETF 成交量
                if period == 'd':
                    last_volume = hist_df['volume'].iloc[-1]
                    if last_volume < 100000000:
                        continue
                    code = code[2:]
                ret_results.append(code)
        except Exception as e:
            nError += 1
            if nError == 1:
                print(f"ETF  Error = : {e}")
            continue
    if nError > 1:
        print("ETF error count:" + str(nError))
    return ret_results


def analyze_BTC():
    _URL_PAIRS = "https://min-api.cryptocompare.com/data/pair/mapping/exchange?e={}"
    _URL_HIST_PRICE_DAY = "https://min-api.cryptocompare.com/data/v2/histoday?fsym={}&tsym={}&limit={}&e={}&toTs={}"

    response = requests.get(_URL_PAIRS.format('Binance')).json()
    if response:
        all_pairs = response["Data"]
    else:
        return None

    coins = [
        pair['fsym']  # 只保留基础货币，如 'BTC', 'ETH'
        for pair in all_pairs
        if pair['tsym'] == 'USDT'  # 只选择 USDT 交易对
    ]
    ret_results = []
    print("[INFO] 分析 加密货币（BTC 相关） ...")
    for coin in tqdm(coins, desc="Progress"):
        # 100 是要获取的条数
        request_url_historical_day = _URL_HIST_PRICE_DAY.format(coin, 'USDT', 100, 'Binance', int(time.time()))

        try:
            response = requests.get(request_url_historical_day).json()
            if not response:
                continue
            json_data = response["Data"]["Data"]
            df = pd.DataFrame(json_data)
            if XShare.strategy_bottomUpFlip(df):
                ret_results.append(coin + '/USDT')
        except KeyError:
            pass

    return ret_results


def update_packets():
    """
    更新需要的库（pip、akshare、baostock），并显示进度条
    :return: None
    """
    # 需要更新的包列表
    packages = [
        {"name": "pip", "command": [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]},
        {"name": "akshare", "command": [sys.executable, "-m", "pip", "install", "--upgrade", "akshare"]},
        {"name": "baostock", "command": [sys.executable, "-m", "pip", "install", "--upgrade", "baostock"]}
    ]
    print("[INFO] Updating required packages...")
    # 使用 tqdm 显示进度
    with tqdm(packages, desc="Updating", unit="package") as pbar:
        for package in pbar:
            pbar.set_postfix_str(f"Current: {package['name']}")
            try:
                # 静默安装，避免输出干扰进度条
                subprocess.check_call(
                    package["command"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError as e:
                tqdm.write(f"[ERROR] Failed to update {package['name']}: {e}")
            except Exception as e:
                tqdm.write(f"[ERROR] Unexpected error with {package['name']}: {e}")

    print("[INFO] All packages updated successfully!")


def handle_results(results):
    # 输出的文件路径
    file_path = "D:\\Users\\Administrator\\Desktop\\stock.txt"

    print("Analysis completed.： total: ", len(results))

    with open(file_path, 'w') as file:
        # 将数组的每个元素写入文件，每个元素占一行
        for item in results:
            file.write(f'{item}\n')


if __name__ == '__main__':
    test = False
    if test:
        print(back_test('002603', '20260105', period='d'))
        sys.exit(0)

    p_period = 'd' if len(sys.argv) > 1 and sys.argv[1] == 'd' else 'w'
    print(p_period)
    # 更新包
    update_packets()
    # 开始分析
    lg = bs.login()
    handle_results(analyze_A(p_period) + analyze_A_ETF(p_period))
    bs.logout()
