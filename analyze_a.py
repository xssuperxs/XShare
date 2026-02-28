from xshare import KlinesAnalyzer as ka
import baostock as bs
import pandas as pd
import subprocess
import sys
from tqdm import tqdm
import datetime


def back_test(code, end_date, period='d'):
    df = _get_klines_baostock(code, period=period, start_date='1970-01-01', end_date=end_date)
    return ka.check_pass_peak(df, period)


def _get_klines_baostock(code, period, start_date, end_date):
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


def _get_trade_dates(period):
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(weeks=103)).strftime('%Y-%m-%d')
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
    start_date = df['date'].iloc[-101]
    end_date = df['date'].iloc[-1]
    return start_date, end_date


def _get_stock_codes():
    print("[INFO] Fetching stock codes...")
    stock_list = bs.query_stock_basic()
    stock_df = stock_list.get_data()
    filtered_stocks = stock_df[
        (stock_df['type'].isin(['1', '2'])) &  # 1 是股票  5 是ETF  2是指数
        (stock_df['status'] == '1') &  # 在交易
        (~stock_df['code_name'].str.contains('ST|\\*ST|退|警示|终止上市', na=False))  # 排除ST股和问题股
        ]
    # 获取股票代码列表
    code_list = filtered_stocks['code'].tolist()
    # 过滤掉暂时不需要的代码
    patterns = [".7", ".9", ".688", ".4"]
    ret_cods = [item for item in code_list if not any(pattern in item for pattern in patterns)]
    return ret_cods


def analyze_A(period):
    codes = _get_stock_codes()
    if not codes:
        print("baostock 可能没有更新完成 稍后再试！")
        return []
    # 使用 tqdm 包装循环，并设置中文描述
    print("[INFO] Analyzing  A stocks and ETF...")
    nError = 0
    ret_results = []
    start_date, end_date = _get_trade_dates(period)
    for code in tqdm(codes, desc="Progress"):
        try:
            # 提取历史K线信息
            df = _get_klines_baostock(code, period, start_date, end_date)
            # 开始分析K线数据  破底翻
            if ka.check_pass_peak(df, period):
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


def update_packets():
    """
    更新需要的库（pip、akshare、baostock），并显示进度条
    :return: None
    """
    # 需要更新的包列表
    packages = [
        {"name": "pip", "command": [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]},
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


def handle_results(results):
    # 输出的文件路径
    file_path = "D:\\Users\\Administrator\\Desktop\\stock.txt"

    print("Analysis completed.： total: ", len(results))

    with open(file_path, 'w') as file:
        # 将数组的每个元素写入文件，每个元素占一行
        for item in results:
            file.write(f'{item}\n')


if __name__ == '__main__':
    lg = bs.login()
    test = False
    if test:
        print(back_test('sh.605006', '2025-12-24', period='d'))
        bs.logout()
        sys.exit(0)
    p_period = 'd' if len(sys.argv) > 1 and sys.argv[1] == 'd' else 'w'
    print(p_period)
    # 更新包
    update_packets()
    # 开始分析
    handle_results(analyze_A(p_period))
    bs.logout()
