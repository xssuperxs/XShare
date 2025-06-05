import akshare as ak
import baostock as bs
from collections import Counter
from ta.trend import MACD
import pandas as pd
import subprocess
import sys
from tqdm import tqdm
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

__all__ = []
# 滑动窗口 窗口越大 分析的结果有可能越多 合理调整  4是比较合理的
_MIN_WINDOW_SIZE = 3
_MAX_WINDOW_SIZE = 7
# 记录数
_RECORD_COUNT = 100
# 创新低天数
_NEW_LOW_DAYS = 21

# akshare的映射列
_COL_MAPPING_AK = {
    "日期": "date",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
}

# 常量字符串
_STR_UPDATE_PACKAGES = "[INFO] Updating required packages..."
_STR_UPDATE_PACKAGES_SUCCESSFULLY = "[INFO] All packages updated successfully!"
_STR_A_STOCK_INDEX_ANALYSIS = "[INFO] A股 股票 指数 分析中..."
_STR_A_STOCK_INDUSTRY_ANALYSIS = "[INFO] A股 (东财)行业板块 分析中..."
_STR_A_STOCK_ETF_ANALYSIS = "[INFO] ETF 分析中..."
_STR_ANALYSIS_PROGRESS = "Progress"
_STR_BAOSTOCK_NOT_UPDATE = "baostock 数据可能没更新完成, 请稍后再试!"


def _extractFrequentElements(input_list: list, nCount: int) -> list:
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


def _getWavePoints(records, window_size, high_flag, low_flag):
    """
    计算波段的高低点
    :param records:  要计算的记录
    :param window_size: 滑动窗口
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

    wave_highs_index = _extractFrequentElements(window_highs_index, window_size)
    wave_lows_index = _extractFrequentElements(window_lows_index, window_size)

    # 再把计算结果反转过来
    for i in range(len(wave_highs_index)):
        wave_highs_index[i] = _RECORD_COUNT - wave_highs_index[i] - 1

    for i in range(len(wave_lows_index)):
        wave_lows_index[i] = _RECORD_COUNT - wave_lows_index[i] - 1

    wave_highs_index = wave_highs_index[::-1]
    wave_lows_index = wave_lows_index[::-1]
    return wave_highs_index, wave_lows_index


def back_test(code, end_date, period='d'):
    """
    测试用
    :param period: 周期  d 日线  w 周线
    :param code: 代码
    :param end_date: 结束时间
    :return: 失败False  成功 类型码
    """
    start_date, _ = _get_last_trade_date("%Y%m%d", end_date)
    if period == 'w':
        start_date = "19700101"

    df = _get_klines_akshare(code, period, start_date=start_date, end_date=end_date)

    if df.empty or len(df) < _RECORD_COUNT:
        return False
    return _strategy_bottomUpFlip(df.tail(_RECORD_COUNT), period)


def _get_klines_baostock(code, period='d'):
    start_date, end_date = _get_last_trade_date("%Y-%m-%d")
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
    v_period = 'daily' if period == 'd' else 'weekly'
    df = ak.stock_zh_a_hist(symbol=code, period=v_period, adjust="qfq", start_date=start_date, end_date=end_date)
    if df.empty:
        return pd.DataFrame()
    # 数据清洗
    return df[list(_COL_MAPPING_AK.keys())].rename(columns=_COL_MAPPING_AK)


def _strategy_bottomUpFlip(df_klines: pd.DataFrame, period='d') -> bool:
    """
    用一个字形容 这个策略

    :param df_klines:   最近 N天的交易记录 不能小于100条记录
    :param period:  周期  d 日线  w 周线
    :return:  bool
    """
    # K线小于100条记录 返回FALSE
    if len(df_klines) < _RECORD_COUNT or df_klines.empty:
        return False

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
        nSubWindow = [i for i in range(_MIN_WINDOW_SIZE, _MAX_WINDOW_SIZE)]

        for n in nSubWindow:

            # 获取波段的 高低点
            highs_index, lows_index = _getWavePoints(df_klines, n, 'high', 'low')

            if len(lows_index) < 3 or len(highs_index) < 3:
                continue

            preHighIndex = highs_index[-1]
            preLowIndex = lows_index[-1]
            preLow2Index = lows_index[-2]

            preHighPrice = df_klines.iloc[preHighIndex]['high']
            preLowPrice = df_klines.iloc[preLowIndex]['low']
            preLow2Price = df_klines.iloc[preLow2Index]['low']

            # 当天高点要过前高
            if today_high <= preHighPrice:
                continue
            # 昨天高点不能过前高
            if yesterday_high >= preHighPrice:
                continue

            if today_low < preLowPrice or yesterday_low < preLowPrice:
                preLow2Price = preLowPrice
                if today_low <= yesterday_low:  # 使用 <= 可以处理相等的情况
                    preLowPrice, preLowIndex = today_low, _RECORD_COUNT - 1
                else:
                    preLowPrice, preLowIndex = yesterday_low, _RECORD_COUNT - 2

            # 高点比低点索引大
            if preHighIndex > preLowIndex:
                if preLowPrice > preLow2Price:
                    continue
                pre_highs = []
                is_new_high = False
                is_OK = True
                for item in reversed(highs_index):
                    if item < preLowIndex:  # 找到前低前面的高点
                        preHighPrice = df_klines.iloc[item]['high']
                        if today_high > preHighPrice > yesterday_high:
                            is_new_high = True
                        break
                    else:
                        pre_highs.append(item)

                if not is_new_high:
                    continue
                for index in pre_highs:
                    if df_klines.iloc[index]['high'] > preHighPrice:
                        is_OK = False
                        break
                if not is_OK:
                    continue

            # 判断是不是破底翻
            if preLowPrice > preLow2Price:
                continue

            # 如果是分析周线 这里直接返回True
            if period == 'w':
                return True

            macd = MACD(close=df_klines['close'], window_fast=12, window_slow=26, window_sign=9)
            pre_low_dea = macd.macd_signal().iloc[preLowIndex]
            if pre_low_dea > 0:
                continue

            # 获取最低点向前的N条记录
            subset = df_klines.iloc[preLowIndex - _NEW_LOW_DAYS: preLowIndex]
            n_day_low_price = subset['low'].min()
            if preLowPrice <= n_day_low_price:
                return True
        return False
    except Exception as e:
        # 处理其他异常
        print(f"发生未知错误: {e}")
        return False


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
        print(_STR_BAOSTOCK_NOT_UPDATE)
        return []
    ret_results = []

    # 过滤掉不需要的个股 北证 和 688 开的
    pattern = r"\.9|\.8|\.4|\.688"
    # 使用 tqdm 包装循环，并设置中文描述
    for code in tqdm(codes, desc=_STR_A_STOCK_INDEX_ANALYSIS + _STR_ANALYSIS_PROGRESS):
        # 过滤掉暂时不需要的代码
        if re.search(pattern, code):
            continue
        # 提取历史K线信息
        df = _get_klines_baostock(code, period)
        if len(df) < _RECORD_COUNT or df.empty:
            continue
        # 提取需要的N条K线记录
        df_klines = df.tail(_RECORD_COUNT)
        # 开始分析K线数据
        if _strategy_bottomUpFlip(df_klines, period):
            code = code.split(".")[-1]
            ret_results.append(code)
    return ret_results


def analyze_A_industry(period='d'):
    """
    分析A股的 行业板块 东方财富
    :param period:
    :return:
    """
    v_period = '日k' if period == 'd' else '周k'

    # 获取需要提取记录的间隔
    start_date, end_date = _get_last_trade_date()

    # 获取行业板块的名称和代码
    df = ak.stock_board_industry_name_em()
    # 只保留名称和代码
    dict_data = {row['板块名称']: row['板块代码'] for _, row in df.iterrows()}
    name_list = list(dict_data.keys())
    ret_results = []

    for name in tqdm(name_list, desc=_STR_A_STOCK_INDUSTRY_ANALYSIS + _STR_ANALYSIS_PROGRESS):
        df = ak.stock_board_industry_hist_em(
            symbol=name,
            start_date=start_date,
            end_date=end_date,
            period=v_period
        )
        # 数据清洗
        df = df[list(_COL_MAPPING_AK.keys())].rename(columns=_COL_MAPPING_AK)

        if len(df) < _RECORD_COUNT:
            continue

        # 策略分析
        df_klines = df.tail(_RECORD_COUNT)
        if _strategy_bottomUpFlip(df_klines, period):
            ret_results.append(dict_data[name])
    return ret_results


def analyze_A_ETF():
    ret_results = []
    etf_df = ak.fund_etf_category_sina(symbol="ETF基金")
    codes = etf_df['代码'].to_list()
    for code in tqdm(codes, desc=_STR_A_STOCK_ETF_ANALYSIS):
        hist_df = ak.fund_etf_hist_sina(symbol=code)
        if len(hist_df) < _RECORD_COUNT or hist_df.empty:
            continue
        # 提取需要的N条K线记录
        df_klines = hist_df.tail(_RECORD_COUNT)

        if _strategy_bottomUpFlip(df_klines, period='d'):
            code = code[2:]
            ret_results.append(code)

    return ret_results


def _update_packets():
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
    print(_STR_UPDATE_PACKAGES)

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

    # print(_STR_UPDATE_PACKAGES_SUCCESSFULLY)


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
    test = False
    if test:
        # 回测用
        print(back_test('601398', '20230310', period='d'))
    else:
        _update_packets()
        # 同时分析 A股股票 A股指数 和 A股行业板块(东方财富的行业板块)
        # handle_results(analysisA(period='d'))
        handle_results(analyze_A() + analyze_A_ETF())
        # handle_results(analysis_ETF())
        # handle_results(analysisA() + analysisA_industry())
    bs.logout()
