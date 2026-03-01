from xshare import KlinesAnalyzer as ka
from xbaostock import XBaoStock as xbs
import subprocess
import sys


def analyze_A_stocks(period):
    codes = xbs.get_stock_codes()
    if not codes:
        return []
    nError = 0
    ret_results = []
    start_date, end_date = xbs.get_trade_dates(period)
    for code in codes:
        try:
            # 提取历史K线信息
            df = xbs.get_stock_hist(code, period, start_date, end_date)
            # 开始分析K线数据  破底翻
            if ka.check_pass_peak(df, period):
                code = code.split(".")[-1]
                ret_results.append(code)
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
    # 使用 tqdm 显示进度
    for pkg in packages:
        try:
            # 执行命令
            subprocess.run(
                pkg['command'],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"update_packets 错误: {e.stderr}")
        except Exception as e:
            print(f"update_packets 执行出错: {e}")


if __name__ == '__main__':
    # 先更新需要的包
    xbs.login()
    update_packets()
    p_period = 'd' if len(sys.argv) > 1 and sys.argv[1] == 'd' else 'w'
    analyze_A_stocks(p_period)
    xbs.logout()

