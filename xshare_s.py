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
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta


class XShare:
    # 时间窗口
    __MIN_WINDOW_SIZE = 3
    __MAX_WINDOW_SIZE = 4
    # 记录数
    __RECORD_COUNT = 100
    # 创新低天数
    __NEW_LOW_DAYS = 21

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
    def strategy_bottomUpFlip(klines: pd.DataFrame, period='d') -> bool:
        """
        策略 破低翻
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
            today_doc = df_klines.iloc[-1]
            yesterday_doc = df_klines.iloc[-2]

            today_high = today_doc['high']
            today_low = today_doc['low']
            yesterday_high = yesterday_doc['high']
            yesterday_low = yesterday_doc['low']
            if yesterday_high > today_high:
                return False

            # 获取需要的时间窗口
            nSubWindow = [i for i in range(XShare.__MIN_WINDOW_SIZE, XShare.__MAX_WINDOW_SIZE)]

            for n in nSubWindow:
                # 获取波段的 高低点
                highs_index, lows_index = XShare.__getWavePoints(df_klines, n, 'high', 'low')

                if len(lows_index) < 3 or len(highs_index) < 3:
                    continue
                # 先确定最低点
                lowPrice = df_klines.iloc[lows_index[-1]]['low']
                tmpLow = min(today_low, yesterday_low)
                if tmpLow < lowPrice:
                    lows_index.append(XShare.__RECORD_COUNT - 1)
                # 确定前低  和 最低
                lowPoints = list(reversed(lows_index))
                curLowIndex = lows_index[-1]
                nextLowIndex = -1
                for current, next_item in zip(lowPoints, lowPoints[1:]):
                    curLow = df_klines.iloc[current]['low']
                    nextLow = df_klines.iloc[next_item]['low']
                    if curLow < nextLow:
                        nextLowIndex = next_item
                        break
                    else:
                        curLowIndex = next_item

                # 判断是否获取到两个低点的索引
                if curLowIndex == -1 or nextLowIndex == -1:
                    continue

                # 取出波段的高点要在两个低点中间
                highIndex = -1
                for nIndex in reversed(highs_index):
                    if nextLowIndex < nIndex < curLowIndex:
                        highIndex = nIndex
                        break

                highPrice = df_klines.iloc[highIndex]['high']
                if today_high < highPrice:
                    continue
                if yesterday_high > highPrice:
                    continue
                if period == 'w':
                    return True

                # macd = MACD(close=df_klines['close'], window_fast=12, window_slow=26, window_sign=9)
                # pre_low_dea = macd.macd_signal().iloc[preLowIndex]
                # if pre_low_dea > 0:
                #     continue
                # 获取最低点向前的N条记录

                subset = df_klines.iloc[curLowIndex - XShare.__NEW_LOW_DAYS: curLowIndex]
                n_day_low_price = subset['low'].min()
                lowPrice = df_klines.iloc[curLowIndex]['low']
                if lowPrice <= n_day_low_price:
                    return True

            return False
        except Exception as e:
            # 处理其他异常
            print(f"发生未知错误: {e}")
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
    ret_results = []
    str1 = '日K'
    if period == 'w':
        str1 = '周K'

    # 过滤掉不需要的个股 北证 和 688 开的
    pattern = r"\.9|\.8|\.4|\.688"
    # 使用 tqdm 包装循环，并设置中文描述
    print("[INFO] 分析 A股股票和指数 ..." + str1)
    nError = 0
    for code in tqdm(codes, desc="Progress"):
        # 过滤掉暂时不需要的代码
        if re.search(pattern, code):
            continue
        try:
            # 提取历史K线信息
            df = _get_klines_baostock(code, period)
            # 开始分析K线数据
            if XShare.strategy_bottomUpFlip(df, period):
                code = code.split(".")[-1]
                ret_results.append(code)
        except Exception as e:
            nError += 1
            if nError == 1:
                print(f"发生未知错误: {e}")
            continue
    print("analyze_A error count:" + str(nError))
    return ret_results


def analyze_A_ETF():
    ret_results = []
    # etf_df = ak.fund_etf_category_sina(symbol="ETF基金")
    etf_df = ak.fund_etf_category_sina(symbol="ETF基金")
    codes = etf_df['代码'].to_list()
    print("[INFO] 分析 A股  ETF ...")
    for code in tqdm(codes, desc="Progress"):
        hist_df = ak.fund_etf_hist_sina(symbol=code)
        if hist_df.empty:
            continue
        latest_high = hist_df["high"].iloc[-1]
        if latest_high > 50:
            continue
        if XShare.strategy_bottomUpFlip(hist_df, period='d'):
            code = code[2:]
            ret_results.append(code)
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


def handle_results(result):
    # 输出的文件路径
    file_path = "D:\\Users\\Administrator\\Desktop\\stock.txt"

    print("分析完成！： 共 ", len(result), '只:', result)

    with open(file_path, 'w') as file:
        # 将数组的每个元素写入文件，每个元素占一行
        for item in result:
            file.write(f'{item}\n')


if __name__ == '__main__':
    lg = bs.login()  # 登录系统
    test = True
    if test:
        # 回测用
        print(back_test('601398', '20230310', period='w'))
        # print(back_test('300274', '20250711', period='w'))
    else:
        update_packets()
        is_daily = True  # 日线 周线切换  true为日线
        if is_daily:
            handle_results(analyze_A() + analyze_A_ETF())
        else:
            handle_results(analyze_A(period='w'))
        # 分析加密货币 币安 USDT 交易对
        # print(analyze_BTC())
    bs.logout()
